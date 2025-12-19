# -*- coding: utf-8 -*-
"""
Cluster Service
Lógica de negocio para Cluster Lab
"""
from django.db.models import Count
from django.utils import timezone
from ..models import (
    UniqueProductCluster, 
    ProductClusterMembership, 
    ClusterDecisionLog,
    Product
)


class ClusterService:
    """
    Servicio para manejar la lógica de clustering y análisis
    """
    
    @staticmethod
    def get_cluster_stats():
        """
        Obtiene estadísticas del Cluster Lab
        
        Returns:
            dict: Métricas de clustering y progreso
        """
        from ..models import AIFeedback
        
        # Total de clusters
        total_clusters = UniqueProductCluster.objects.count()
        
        # Clusters solitarios (orphans)
        orphan_clusters = UniqueProductCluster.objects.filter(
            total_competitors=1
        ).count()
        
        # Feedback del usuario
        total_feedback = AIFeedback.objects.count()
        positive_feedback = AIFeedback.objects.filter(feedback='positive').count()
        
        # Calcular "XP" y progreso
        xp = total_feedback * 10
        level = xp // 100
        
        return {
            'total_clusters': total_clusters,
            'orphan_count': orphan_clusters,
            'total_feedback': total_feedback,
            'positive_feedback': positive_feedback,
            'xp': xp,
            'level': level,
            'progress': (xp % 100)
        }
    
    @staticmethod
    def get_audit_logs(limit=50):
        """
        Obtiene logs de decisiones del clusterizer
        
        Args:
            limit: Número máximo de logs
            
        Returns:
            QuerySet: Logs de decisiones ordenados por fecha
        """
        return ClusterDecisionLog.objects.order_by('-created_at')[:limit]
    
    @staticmethod
    def get_orphan_products(limit=50):
        """
        Obtiene productos solitarios (clusters de 1)
        
        Args:
            limit: Número máximo de orphans
            
        Returns:
            QuerySet: Clusters solitarios
        """
        return UniqueProductCluster.objects.filter(
            total_competitors=1
        ).select_related('representative_product', 'representative_product__supplier')\
        .order_by('-created_at')[:limit]
    
    @staticmethod
    def investigate_orphan(product_id):
        """
        Investiga candidatos para un producto solitario
        
        Args:
            product_id: ID del producto a investigar
            
        Returns:
            list: Lista de candidatos con scores
        """
        from django.db import connection
        from ..models import ProductEmbedding
        
        # Obtener embedding del producto
        try:
            embedding = ProductEmbedding.objects.get(product_id=product_id)
            if not embedding.embedding_visual:
                return []
        except ProductEmbedding.DoesNotExist:
            return []
        
        # Buscar candidatos similares visualmente
        sql = """
            SELECT 
                pe.product_id,
                (pe.embedding_visual <=> %s::vector) as visual_score,
                p.title
            FROM product_embeddings pe
            JOIN products p ON p.product_id = pe.product_id
            WHERE pe.product_id != %s
              AND pe.embedding_visual IS NOT NULL
            ORDER BY visual_score ASC
            LIMIT 15
        """
        
        candidates = []
        with connection.cursor() as cursor:
            cursor.execute(sql, (str(embedding.embedding_visual), product_id))
            rows = cursor.fetchall()
        
        # Obtener detalles completos
        if rows:
            product_ids = [r[0] for r in rows]
            products = Product.objects.filter(product_id__in=product_ids)\
                .select_related('supplier')
            
            product_map = {p.product_id: p for p in products}
            
            for pid, visual_score, title in rows:
                product = product_map.get(pid)
                if product:
                    candidates.append({
                        'product_id': pid,
                        'title': product.title,
                        'image': product.url_image_s3,
                        'price': product.sale_price,
                        'visual_score': round((1 - visual_score) * 100, 2),
                        'supplier': product.supplier.name if product.supplier else 'N/A'
                    })
        
        return candidates
    
    @staticmethod
    def save_cluster_feedback(product_id, candidate_id, decision, feedback, scores):
        """
        Guarda feedback del usuario sobre una decisión de clustering
        
        Args:
            product_id: ID del producto principal
            candidate_id: ID del candidato
            decision: Decisión tomada (MERGE, REJECT, etc.)
            feedback: Feedback del usuario
            scores: Dict con scores (visual, text, final)
            
        Returns:
            AIFeedback: Objeto guardado
        """
        from ..models import AIFeedback
        
        feedback_obj = AIFeedback.objects.create(
            product_id=product_id,
            candidate_id=candidate_id,
            decision=decision,
            feedback=feedback,
            visual_score=scores.get('visual_score'),
            text_score=scores.get('text_score'),
            final_score=scores.get('final_score'),
            method=scores.get('method', 'unknown'),
            active_weights=scores.get('active_weights', {})
        )
        
        return feedback_obj
