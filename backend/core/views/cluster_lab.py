# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import connection, transaction
from difflib import SequenceMatcher
from ..models import (
    AIFeedback,
    ClusterDecisionLog,
    UniqueProductCluster,
    Product,
    ProductEmbedding,
    ProductClusterMembership,
)
from ..permissions import IsAdminRole


class ClusterLabStatsView(APIView):
    permission_classes = [IsAdminRole]
    """
    Métricas para el Sidebar del Cluster Lab (XP y Progreso).
    """
    
    def get(self, request):
        try:
            # 1. Total Auditorías Realizadas (XP del Usuario)
            total_feedback = AIFeedback.objects.count()
            
            # --- XP DIARIA ---
            now = timezone.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_xp = AIFeedback.objects.filter(created_at__gte=start_of_day).count()
            
            # 2. Total Decisiones IA Registradas
            total_logs = ClusterDecisionLog.objects.count()

            # 3. Precisión Humana (Correcciones vs Confirmaciones)
            correct_feedback = AIFeedback.objects.filter(feedback='CORRECT').count()
            incorrect_feedback = AIFeedback.objects.filter(feedback='INCORRECT').count()
            
            # --- SALUD DEL SISTEMA ---
            # Huérfanos: Clusters con singletons
            pending_orphans = UniqueProductCluster.objects.filter(total_competitors=1).count()
            total_products = Product.objects.count()

            return Response({
                "xp_audits": total_feedback,
                "xp_today": daily_xp,
                "ai_decisions": total_logs,
                "feedback_correct": correct_feedback,
                "feedback_incorrect": incorrect_feedback,
                "pending_orphans": pending_orphans,
                "total_products": total_products
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ClusterAuditView(APIView):
    permission_classes = [IsAdminRole]
    """
    API para el 'Cluster Lab'.
    1. GET: Retorna los últimos logs de decisión del Clusterizer (Persistent DB).
    2. POST: (Opcional) Simula un match entre dos productos (Dry Run).
    """
    
    def get(self, request):
        try:
            limit = int(request.query_params.get('limit', 100))
            # Ordering is defined in Meta class as ['-timestamp']
            logs = ClusterDecisionLog.objects.all()[:limit]
            
            # --- ACTION: Bulk Fetch Concepts ---
            p_ids = [log.product_id for log in logs]
            products = Product.objects.filter(product_id__in=p_ids).only('product_id', 'taxonomy_concept', 'taxonomy_level')
            concept_map = {p.product_id: {'concept': p.taxonomy_concept, 'level': p.taxonomy_level} for p in products}

            data = []
            for log in logs:
                c_info = concept_map.get(log.product_id, {})
                data.append({
                    "timestamp": log.timestamp.timestamp(),
                    "product_id": log.product_id,
                    "candidate_id": log.candidate_id,
                    "title_a": log.title_a,
                    "title_b": log.title_b,
                    "image_a": log.image_a,
                    "image_b": log.image_b,
                    "visual_score": log.visual_score,
                    "text_score": log.text_score,
                    "final_score": log.final_score,
                    "decision": log.decision,
                    "method": log.match_method,
                    "active_weights": log.active_weights,
                    # NEW FIELDS
                    "concept": c_info.get('concept', 'UNKNOWN'),
                    "level": c_info.get('level', 'UNKNOWN')
                })

            return Response(data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ClusterOrphansView(APIView):
    permission_classes = [IsAdminRole]
    """
    Retorna productos que están en clusters 'SINGLETON' (solitarios)
    para auditar por qué no se unieron.
    """
    
    def get(self, request):
        # Buscar clusters con tamaño 1 (o marcados como SINGLETON si tuviéramos ese flag)
        # Por eficiencia, buscamos en la tabla de metricas
        orphans = UniqueProductCluster.objects.filter(total_competitors=1).order_by('-updated_at')[:20]
        
        data = []
        for o in orphans:
            # Obtener el producto representativo
            prod = o.representative_product
            if prod:
                data.append({
                    "cluster_id": o.cluster_id,
                    "product_id": prod.product_id,
                    "title": prod.title,
                    "image": prod.url_image_s3,
                    "price": prod.sale_price,
                    "date": o.updated_at
                })
        return Response(data)

    def post(self, request):
        """
        Simula la búsqueda de candidatos para un producto huérfano.
        Argumentos: { "product_id": 123 }
        Retorna: Lista de Top 15 (antes 10) Candidatos con scores detallados (Grid V3).
        """
        try:
            target_pid = request.data.get('product_id')
            if not target_pid:
                return Response({"error": "Missing product_id"}, status=400)

            # 1. Obtener datos del producto objetivo (Vector + Texto)
            with connection.cursor() as cur:
                # Get Target Info
                cur.execute("""
                    SELECT p.title, p.url_image_s3, pe.embedding_visual 
                    FROM products p 
                    JOIN product_embeddings pe ON p.product_id = pe.product_id 
                    WHERE p.product_id = %s
                """, (target_pid,))
                res = cur.fetchone()
                if not res:
                    return Response({"error": "Product not found or not vectorized"}, status=404)
                
                target_title, target_image, target_vector = res
                
                # 2. Buscar Top 15 Candidatos Visuales (Expandido para Grid)
                cur.execute("""
                    SELECT 
                        p.product_id, p.title, p.sale_price, p.url_image_s3,
                        (pe.embedding_visual <=> %s) as dist 
                    FROM product_embeddings pe
                    JOIN products p ON pe.product_id = p.product_id
                    WHERE pe.product_id != %s AND pe.embedding_visual IS NOT NULL
                    ORDER BY dist ASC
                    LIMIT 50
                """, (target_vector, target_pid))
                
                candidates = []

                for row in cur.fetchall():
                    c_pid, c_title, c_price, c_img, dist = row
                    
                    # Calcular Scores (Misma lógica que Clusterizer V3)
                    visual_score = max(0, 1.0 - float(dist))
                    text_score = SequenceMatcher(None, str(target_title).lower(), str(c_title).lower()).ratio()
                    final_score = (0.6 * visual_score) + (0.4 * text_score)
                    
                    # Lógica de Rescate (Simulada)
                    method = "REJECTED"
                    if visual_score >= 0.92:
                        method = "VISUAL_MATCH"
                    elif text_score >= 0.95 and visual_score >= 0.65:
                        method = "TEXT_RESCUE"
                    elif final_score >= 0.82:
                        method = "HYBRID_MATCH"

                    candidates.append({
                        "id": c_pid,
                        "title": c_title,
                        "price": float(c_price or 0),
                        "image": c_img,
                        "scores": {
                            "visual": round(visual_score, 2),
                            "text": round(text_score, 2),
                            "final": round(final_score, 2)
                        },
                        "would_match": method != "REJECTED",
                        "method": method
                    })
                
                return Response({
                    "target": {"id": target_pid, "title": target_title, "image": target_image},
                    "candidates": candidates
                })

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ClusterFeedbackView(APIView):
    permission_classes = [IsAdminRole]
    
    def post(self, request):
        """
        Guarda el feedback del usuario sobre una decisión de clustering (RICHER DATA).
        Body: { product_id, candidate_id, decision, feedback, visual_score, text_score, final_score, method, active_weights }
        """
        try:
            import json
            data = request.data
            
            # Limpiar weights si vienen como string
            weights = data.get('active_weights')
            if isinstance(weights, str):
                try:
                    weights = json.loads(weights)
                except:
                    weights = {}

            AIFeedback.objects.create(
                product_id=data.get('product_id'),
                candidate_id=data.get('candidate_id'),
                decision=data.get('decision'), 
                feedback=data.get('feedback'),  # 'CORRECT' / 'INCORRECT'
                
                # Rich Data for ML Training
                visual_score=data.get('visual_score', 0.0),
                text_score=data.get('text_score', 0.0),
                final_score=data.get('final_score', 0.0),
                match_method=data.get('method', 'UNKNOWN'),
                active_weights=weights
            )
            return Response({"status": "saved", "message": "Rich Feedback recorded successfully"})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class ClusterOrphanActionView(APIView):
    permission_classes = [IsAdminRole]
    
    def post(self, request):
        """
        Ejecuta acciones reales sobre el Investigador de Diamantes.
        Actions: MERGE_SELECTED, CONFIRM_SINGLETON, TRASH
        """
        try:
            target_id = request.data.get('product_id')
            action = request.data.get('action')
            candidates = request.data.get('candidates', [])
            
            if not target_id or not action:
                return Response({"error": "Missing params"}, status=400)

            product = Product.objects.filter(product_id=target_id).first()
            if not product:
                return Response({"error": "Product not found"}, status=404)

            print(f"ORPHAN ACTION: {action} on Target {target_id}")

            with transaction.atomic():
                if action == 'TRASH':
                    # Incinerar producto: Borrar Embeddings y ClusterMembership
                    # Esto lo saca del radar del sistema de IA y Clustering
                    ProductEmbedding.objects.filter(product_id=target_id).delete()
                    ProductClusterMembership.objects.filter(product_id=target_id).delete()
                    # Opcional: Marcar producto como inactivo si tuviéramos campo status
                    # product.status = 'TRASH'
                    # product.save()
                    msg = "Product incinerated (Embeddings & Cluster info removed)"

                elif action == 'CONFIRM_SINGLETON':
                    # Confirmar que es único. 
                    # Simplemente nos aseguramos que tenga un cluster propio y válido.
                    # El hecho de que el usuario lo revise ya valida su existencia.
                    # Podríamos agregar un flag 'verified_by_human' en el futuro.
                    msg = "Singleton confirmed"

                elif action == 'MERGE_SELECTED':
                    if not candidates:
                        return Response({"error": "No candidates selected for merge"}, status=400)
                    
                    # 1. Obtener cluster del Target (o crearle uno si por milagro no tiene)
                    membership, _ = ProductClusterMembership.objects.get_or_create(
                        product_id=target_id,
                        defaults={'cluster_id': UniqueProductCluster.objects.create().cluster_id}
                    )
                    target_cluster = membership.cluster

                    # 2. Mover candidatos a este cluster
                    for cand_id in candidates:
                        # Borrar membresía anterior
                        ProductClusterMembership.objects.filter(product_id=cand_id).delete()
                        # Crear nueva en el cluster del target
                        ProductClusterMembership.objects.create(
                            product_id=cand_id,
                            cluster=target_cluster
                            # removed is_representative since it doesn't exist in the model
                        )
                    
                    # 3. Recalcular metricas del cluster (Simulado update de timestamp para refrescar)
                    target_cluster.save()  # Dispara trigger de updated_at
                    msg = f"Merged {len(candidates)} candidates into Cluster {target_cluster.cluster_id}"

            return Response({"status": "success", "message": msg})
            
        except Exception as e:
            print(f"Error executing orphan action: {str(e)}")
            return Response({"error": str(e)}, status=500)
