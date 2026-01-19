"""
[DSA-08b] Cluster Centroid & Medoids Calculator

Calcula el centroide visual (promedio) y los 3 medoids (representantes)
para cada cluster de productos únicos.

Estos vectores se usan en la verificación visual (SigLIP) para determinar
si un competidor vende el mismo producto.
"""
from typing import List, Dict, Any, Tuple
import numpy as np
from django.db import transaction
from core.models import UniqueProductCluster, ProductClusterMembership, ProductEmbedding, EMBED_DIM


class CentroidCalculator:
    """
    Calcula centroides y medoids para clusters de productos.
    """
    
    MIN_PRODUCTS_FOR_CALCULATION = 3  # Mínimo de productos para calcular centroide
    NUM_MEDOIDS = 3  # Número de medoids a extraer
    
    @classmethod
    def calculate_for_cluster(cls, cluster: UniqueProductCluster) -> Dict[str, Any]:
        """
        Calcula centroide y medoids para un cluster específico.
        
        Returns:
            Dict con 'status', 'centroid', 'medoids', y metadata
        """
        # 1. Obtener todos los productos del cluster con embeddings
        members = ProductClusterMembership.objects.filter(
            cluster=cluster
        ).select_related('product')
        
        if not members.exists():
            return {
                "status": "error",
                "error": "No members in cluster"
            }
        
        # 2. Extraer vectores visuales
        product_ids = [m.product_id for m in members]
        embeddings = ProductEmbedding.objects.filter(
            product_id__in=product_ids,
            embedding_visual__isnull=False
        )
        
        if embeddings.count() < cls.MIN_PRODUCTS_FOR_CALCULATION:
            return {
                "status": "error",
                "error": f"Not enough embeddings ({embeddings.count()} < {cls.MIN_PRODUCTS_FOR_CALCULATION})"
            }
        
        # 3. Convertir a numpy array
        vectors = []
        vector_metadata = []  # Para tracking
        
        for emb in embeddings:
            if emb.embedding_visual:
                vectors.append(emb.embedding_visual)
                vector_metadata.append({
                    "product_id": emb.product_id,
                    "title": emb.product.title[:50] if emb.product else ""
                })
        
        if len(vectors) < cls.MIN_PRODUCTS_FOR_CALCULATION:
            return {
                "status": "error",
                "error": "Not enough valid vectors"
            }
        
        vectors_array = np.array(vectors, dtype=np.float32)
        
        # 4. Calcular Centroide (promedio)
        centroid = np.mean(vectors_array, axis=0)
        
        # 5. Calcular Medoids (3 vectores más representativos)
        # Medoid = vector que minimiza la distancia promedio a todos los demás
        medoid_indices = cls._find_medoids(vectors_array, num_medoids=cls.NUM_MEDOIDS)
        
        medoids = [vectors_array[idx].tolist() for idx in medoid_indices]
        medoid_meta = [vector_metadata[idx] for idx in medoid_indices]
        
        # 6. Guardar en el cluster
        with transaction.atomic():
            cluster.visual_centroid = centroid.tolist()
            cluster.visual_medoid_1 = medoids[0] if len(medoids) > 0 else None
            cluster.visual_medoid_2 = medoids[1] if len(medoids) > 1 else None
            cluster.visual_medoid_3 = medoids[2] if len(medoids) > 2 else None
            
            # Sanitizar títulos para SQL_ASCII (remover ñ, tildes, etc.)
            sanitized_titles = [
                title.encode('ascii', 'ignore').decode('ascii')
                for title in [m["title"] for m in medoid_meta]
            ]
            
            cluster.medoid_meta = {
                "ids": [m["product_id"] for m in medoid_meta],
                "titles": sanitized_titles,
                "total_vectors": len(vectors),
                "calculation_method": "k-medoids"
            }
            cluster.save()
        
        return {
            "status": "success",
            "cluster_id": cluster.cluster_id,
            "total_vectors": len(vectors),
            "centroid_dim": len(centroid),
            "medoids_count": len(medoids),
            "medoid_products": [m["product_id"] for m in medoid_meta]
        }
    
    @staticmethod
    def _find_medoids(vectors: np.ndarray, num_medoids: int = 3) -> List[int]:
        """
        Encuentra los N medoids (vectores más representativos) usando distancia euclidiana.
        
        Medoid = vector que minimiza la suma de distancias a todos los demás vectores.
        
        Args:
            vectors: Array de vectores (N x D)
            num_medoids: Número de medoids a encontrar
            
        Returns:
            Lista de índices de los medoids
        """
        n_vectors = len(vectors)
        
        if n_vectors <= num_medoids:
            # Si hay menos vectores que medoids solicitados, devolver todos
            return list(range(n_vectors))
        
        # Calcular matriz de distancias (N x N)
        # Usamos distancia euclidiana
        distances = np.zeros((n_vectors, n_vectors))
        for i in range(n_vectors):
            for j in range(i + 1, n_vectors):
                dist = np.linalg.norm(vectors[i] - vectors[j])
                distances[i, j] = dist
                distances[j, i] = dist
        
        # Encontrar medoids de forma greedy
        medoid_indices = []
        
        # Primer medoid: el que tiene menor distancia promedio a todos
        avg_distances = distances.sum(axis=1)
        first_medoid = int(np.argmin(avg_distances))
        medoid_indices.append(first_medoid)
        
        # Medoids subsecuentes: maximizar diversidad
        # Elegir vectores que estén más lejos de los medoids ya seleccionados
        for _ in range(num_medoids - 1):
            if len(medoid_indices) >= n_vectors:
                break
                
            # Distancia mínima de cada punto a los medoids ya seleccionados
            min_distances = np.min(distances[:, medoid_indices], axis=1)
            
            # Evitar seleccionar medoids ya elegidos
            for idx in medoid_indices:
                min_distances[idx] = -1
            
            # Elegir el punto más lejano
            next_medoid = int(np.argmax(min_distances))
            medoid_indices.append(next_medoid)
        
        return medoid_indices
    
    @classmethod
    def calculate_batch(cls, clusters: List[UniqueProductCluster]) -> Dict[str, Any]:
        """
        Calcula centroides y medoids para un batch de clusters.
        
        Returns:
            Dict con estadísticas del batch
        """
        results = {
            "total": len(clusters),
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "details": []
        }
        
        for cluster in clusters:
            try:
                result = cls.calculate_for_cluster(cluster)
                
                if result["status"] == "success":
                    results["success"] += 1
                elif result["status"] == "error":
                    results["errors"] += 1
                    results["details"].append({
                        "cluster_id": cluster.cluster_id,
                        "error": result.get("error", "Unknown")
                    })
                else:
                    results["skipped"] += 1
                    
            except Exception as e:
                results["errors"] += 1
                results["details"].append({
                    "cluster_id": cluster.cluster_id,
                    "error": str(e)
                })
        
        return results
