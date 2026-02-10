# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings
from core.models import User
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from .models import (
    Product,
    UniqueProductCluster,
    ProductEmbedding,
    Warehouse,
    Category,
    ProductClusterMembership,
    AIFeedback,
    ClusterDecisionLog,
    # UserProfile y DropiAccount ya no se usan, todo está en User
    OrderReport,
    WorkflowProgress,
    ReportBatch,
    RawOrderSnapshot,
    ReporterSlotConfig,
    ReporterHourSlot,
    ReporterReservation,
    ReporterRun,
    ReporterRunUser,
    reporter_reservation_weight_from_orders,
    assign_best_available_slot,
)
from .permissions import IsAdminRole, MinSubscriptionTier
from datetime import datetime, timedelta, time as dt_time
import pathlib
import json
import os
from .docker_utils import get_container_stats, control_container

class DashboardStatsView(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        """
        Centro de Comando Estratégico (V2).
        Retorna inteligencia real del mercado y oportunidades tácticas, 
        ya no solo estado del servidor.
        """
        
        # ---------------------------------------------------------
        # 1. FLASH OPPORTUNITIES (Los mejores hallazgos de las últimas 48h)
        # ---------------------------------------------------------
        # Buscamos productos recientes que prometen alto margen y baja competencia.
        # Estrategia: Productos recientes -> Ordenados por Margen -> Que NO tengan muchos competidores.
        
        cutoff_date = datetime.now() - timedelta(hours=48)
        
        # Obtenemos productos recientes con imagen y precio
        flash_ops = Product.objects.filter(
            created_at__gte=cutoff_date,
            url_image_s3__isnull=False,
            profit_margin__isnull=False
        ).select_related('supplier').order_by('-profit_margin')[:50] # Top 50 candidatos
        
        # --- OPTIMIZACION N+1 ---
        # 1. Extraer los IDs de los productos obtenidos
        p_ids = [p.product_id for p in flash_ops]
        
        # 2. Traer todas las membresías relevantes de una sola vez
        memberships = ProductClusterMembership.objects.filter(
            product_id__in=p_ids
        ).select_related('cluster')
        
        # 3. Crear un diccionario para acceso instantáneo O(1)
        # Map: product_id -> cluster_obj
        cluster_map = {m.product_id: m.cluster for m in memberships}

        tactical_feed = []
        for p in flash_ops:
            # Ahora la búsqueda es en memoria (Instantánea)
            cluster = cluster_map.get(p.product_id)
            
            competitors = 1
            if cluster:
                competitors = cluster.total_competitors
                
            # Solo mostramos si es una "Oportunidad Real" (Baja/Media competencia)
            if competitors <= 10:
                tactical_feed.append({
                    "id": p.product_id,
                    "title": p.title,
                    "image": p.url_image_s3,
                    "price": p.sale_price,
                    "margin": p.profit_margin, # Decimal
                    "competitors": competitors,
                    "supplier": p.supplier.store_name if p.supplier else "N/A",
                    "badge": "SOLITARIO" if competitors == 1 else "GOLD"
                })
                if len(tactical_feed) >= 5: break # Solo queremos los Top 5 para el UI

        # ---------------------------------------------------------
        # 2. MARKET RADAR (Inteligencia por Categoría)
        # ---------------------------------------------------------
        # OPTIMIZACION: Query única con Agregaciones (Elimina N+1 Problems)
        # Calculamos conteo, precio promedio, margen promedio y competencia promedio en una sola consulta.
        
        radar_qs = Category.objects.filter(
            productcategory__product__isnull=False
        ).annotate(
            product_count=Count('productcategory__product', distinct=True),
            avg_price=Avg('productcategory__product__sale_price'),
            avg_margin=Avg('productcategory__product__profit_margin'),
            # Competencia: Promedio de competidores de los clusters asociados a los productos de la categoría
            avg_competitiveness=Avg('productcategory__product__cluster_membership__cluster__total_competitors')
        ).filter(
            product_count__gte=5 # Solo categorías relevantes
        ).order_by('-avg_margin') # Priorizar las más rentables

        radar_data = []
        
        # Iteramos sobre los resultados ya calculados en memoria por la DB
        for cat in radar_qs:
            radar_data.append({
                "category": cat.name,
                "volume": cat.product_count,
                "avg_price": round(cat.avg_price or 0, 2),
                "avg_margin": round(cat.avg_margin or 0, 2),
                # Si no hay clusters, asumimos 1 (baja competencia)
                "competitiveness": round(cat.avg_competitiveness or 1, 1)
            })
            
        # Limitamos a 15 para el frontend (ya vienen ordenados por margen)
        radar_data = radar_data[:15]

        return Response({
            "tactical_feed": tactical_feed,
            "market_radar": radar_data[:15] # Top 15 categorías para no saturar el gráfico
        })

from django.db import connection
# from .ai_utils import get_image_embedding

class GoldMineView(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request):
        """Búsqueda Visual (Reverse Image Search)"""
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=400)
            
        uploaded_file = request.FILES['image']
        
        # 1. Vectorizar imagen llegada
        from .ai_utils import get_image_embedding
        vector = get_image_embedding(uploaded_file)
        if not vector:
             return Response({"error": "Failed to process image"}, status=500)
             
        # 2. Buscar por similaridad (pgvector cosine distance <=>)
        # Buscamos embeddings visuales cercanos y unimos con clusters
        # Traemos los top 50 matches visuales
        sql = """
            SELECT 
                pe.product_id, 
                (pe.embedding_visual <=> %s::vector) as distance
            FROM product_embeddings pe
            WHERE pe.embedding_visual IS NOT NULL
            ORDER BY distance ASC
            LIMIT 50
        """
        
        similar_products = []
        with connection.cursor() as cur:
            cur.execute(sql, (vector,))
            rows = cur.fetchall()
            similar_pids = [r[0] for r in rows]

        # 3. Recuperar detalles de clusters para esos productos
        # Queremos saber a qué cluster pertenecen esos productos similares
        # y devolver el cluster entero o el representante
        results = []
        if similar_pids:
            # Traer info de clusters donde esos productos son miembros o representantes
            # Simplificación: Devolvemos los productos directos encontrados, enriquecidos con su cluster info
            products = Product.objects.filter(product_id__in=similar_pids).select_related('supplier')
            
            # --- OPTIMIZACION N+1 ---
            # Cargar info de clusters en batch
            product_ids = [p.product_id for p in products]
            memberships = ProductClusterMembership.objects.filter(product_id__in=product_ids).select_related('cluster')
            cluster_map = {m.product_id: m.cluster for m in memberships}

            # Map distance
            dist_map = {r[0]: r[1] for r in rows}
            
            for p in products:
                # Búsqueda en memoria O(1)
                cluster_info = cluster_map.get(p.product_id)
                
                results.append({
                    "id": p.product_id,
                    "title": p.title,
                    "price": p.sale_price,
                    "image": p.url_image_s3,
                    "similarity": f"{int((1 - dist_map.get(p.product_id, 1))*100)}%",
                    "competitors": cluster_info.total_competitors if cluster_info else 1,
                    "profit_margin": "N/A", # Calc real
                    "supplier": p.supplier.store_name if p.supplier else "Desconocido",
                    "cluster_id": cluster_info.cluster_id if cluster_info else None
                })
                
            # Ordenar por similaridad descendente
            results.sort(key=lambda x: x['similarity'], reverse=True)

        return Response(results)

    def get(self, request):
        """Búsqueda Textual y Filtros"""
        try:
            min_comp = int(request.query_params.get('min_comp', 0))
            max_comp = int(request.query_params.get('max_comp', 50)) 
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            min_comp, max_comp, limit, offset = 0, 50, 50, 0

        search_query = request.query_params.get('q', '')
        category_filter = request.query_params.get('category', None)

        # 2. Construir Query
        filters = Q(total_competitors__gte=min_comp) & Q(total_competitors__lte=max_comp)
        
        # Filtro opcional de precio si lo envían
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        
        # Debug logging
        if min_price or max_price:
            print(f"ðŸ’° Price filters - Min: {min_price}, Max: {max_price}")
        
        if min_price: 
            filters &= Q(average_price__gte=min_price)
        if max_price:
            filters &= Q(average_price__lte=max_price)

        if search_query:
            filters &= Q(representative_product__title__icontains=search_query)
            
        # Filtro de Categoría
        if category_filter and category_filter != 'all':
            filters &= Q(representative_product__productcategory__category__id=category_filter)

        # 3. Ejecutar consulta
        ops = UniqueProductCluster.objects.filter(filters)\
            .select_related('representative_product', 'representative_product__supplier')\
            .order_by('-average_price')[offset:offset+limit]

        data = []
        for row in ops:
            p = row.representative_product
            if not p: continue
            
            margin_val = 0
            if p.suggested_price and p.sale_price:
                try:
                    margin_val = ((p.suggested_price - p.sale_price) / p.sale_price) * 100
                except: pass
            
            data.append({
                "id": p.product_id,
                "cluster_id": row.cluster_id,
                "title": p.title,
                "price": p.sale_price,
                "image": p.url_image_s3,
                "competitors": row.total_competitors,
                "profit_margin": f"{int(margin_val)}%",
                "saturation": row.saturation_score,
                "supplier": p.supplier.store_name if p.supplier else "Desconocido"
            })
            
        return Response(data)

class GoldMineStatsView(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        """Retorna estadísticas globales de distribución de competidores"""
        
        # Filtros Base (Search, Category, Price)
        # NOTA: NO filtramos por min_comp/max_comp aquí, para mostrar el panorama completo
        search_query = request.query_params.get('q', '')
        category_filter = request.query_params.get('category', None)
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')

        filters = Q()
        
        if min_price: filters &= Q(average_price__gte=min_price)
        if max_price: filters &= Q(average_price__lte=max_price)
        if search_query: filters &= Q(representative_product__title__icontains=search_query)
        if category_filter and category_filter != 'all':
            filters &= Q(representative_product__productcategory__category__id=category_filter)

        # Agregación: Contar cuantos clusters tienen X competidores
        # SELECT total_competitors, COUNT(*) as count FROM unique_product_clusters WHERE filters GROUP BY total_competitors
        stats = UniqueProductCluster.objects.filter(filters)\
            .values('total_competitors')\
            .annotate(count=Count('cluster_id'))\
            .order_by('total_competitors')

        # Formatear para frontend: { "1": 50, "2": 20, ... }
        result = {s['total_competitors']: s['count'] for s in stats}
        return Response(result)


from django.utils import timezone

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
            if not target_pid: return Response({"error": "Missing product_id"}, status=400)

            # 1. Obtener datos del producto objetivo (Vector + Texto)
            from django.db import connection
            
            with connection.cursor() as cur:
                # Get Target Info
                cur.execute("""
                    SELECT p.title, p.url_image_s3, pe.embedding_visual 
                    FROM products p 
                    JOIN product_embeddings pe ON p.product_id = pe.product_id 
                    WHERE p.product_id = %s
                """, (target_pid,))
                res = cur.fetchone()
                if not res: return Response({"error": "Product not found or not vectorized"}, status=404)
                
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
                from difflib import SequenceMatcher

                for row in cur.fetchall():
                    c_pid, c_title, c_price, c_img, dist = row
                    
                    # Calcular Scores (Misma lógica que Clusterizer V3)
                    visual_score = max(0, 1.0 - float(dist))
                    text_score = SequenceMatcher(None, str(target_title).lower(), str(c_title).lower()).ratio()
                    final_score = (0.6 * visual_score) + (0.4 * text_score)
                    
                    # Lógica de Rescate (Simulada)
                    method = "REJECTED"
                    if visual_score >= 0.92: method = "VISUAL_MATCH"
                    elif text_score >= 0.95 and visual_score >= 0.65: method = "TEXT_RESCUE"
                    elif final_score >= 0.82: method = "HYBRID_MATCH"

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


class CategoriesView(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        """Listar todas las categorías disponibles"""
        cats = Category.objects.all().order_by('name')
        data = [{"id": c.id, "name": c.name} for c in cats]
        return Response(data)

from .docker_utils import get_container_stats, control_container, get_docker_logs

from concurrent.futures import ThreadPoolExecutor, as_completed

class SystemLogsView(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        """
        Retorna logs directamente desde Docker (Paralelizado).
        Devuelve Diccionario: { "scraper": [line1, line2...], ... }
        """
        # Mapeo Service ID -> Container Name
        services = {
            "scraper": "droptools_scraper",
            "loader": "droptools_loader",
            "vectorizer": "droptools_vectorizer",
            "classifier": "droptools_classifier",
            "clusterizer": "droptools_clusterizer",
            "shopify": "droptools_shopify", 
            "ai_trainer": "droptools_ai_trainer"
        }
        
        results = {}

        def fetch_logs(service_id, container_name):
            try:
                raw_lines = get_docker_logs(container_name, tail=50)
                return service_id, [{"message": l, "service": service_id} for l in raw_lines]
            except Exception as e:
                return service_id, [{"message": f"Error fetching logs: {str(e)}", "service": service_id}]

        with ThreadPoolExecutor(max_workers=len(services)) as executor:
            future_map = {
                executor.submit(fetch_logs, s_id, c_name): s_id 
                for s_id, c_name in services.items()
            }
            
            for future in as_completed(future_map):
                s_id, logs = future.result()
                results[s_id] = logs
        
        return Response(results)

class ClusterFeedbackView(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request):
        """
        Guarda el feedback del usuario sobre una decisión de clustering (RICHER DATA).
        Body: { product_id, candidate_id, decision, feedback, visual_score, text_score, final_score, method, active_weights }
        """
        try:
            data = request.data
            
            # Limpiar weights si vienen como string
            weights = data.get('active_weights')
            if isinstance(weights, str):
                try: weights = json.loads(weights)
                except: weights = {}

            AIFeedback.objects.create(
                product_id=data.get('product_id'),
                candidate_id=data.get('candidate_id'),
                decision=data.get('decision'), 
                feedback=data.get('feedback'), # 'CORRECT' / 'INCORRECT'
                
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

class ContainerStatsView(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        """
        Retorna estado robusto de los contenedores (CPU, RAM, Status).
        """
        containers = {
            "scraper": "droptools_scraper",
            "loader": "droptools_loader",
            "vectorizer": "droptools_vectorizer",
            "classifier": "droptools_classifier",
            "clusterizer": "droptools_clusterizer",
            "market_agent": "droptools_market_agent",
            "amazon_explorer": "droptools_amazon_explorer",
            "ai_trainer": "droptools_ai_trainer",
            "celery_worker": "droptools_celery_worker",
            "db": "droptools_db"
        }
        
        data = {}
        for friendly_name, c_name in containers.items():
            data[friendly_name] = get_container_stats(c_name)
            
        return Response(data)

class ContainerControlView(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request, service, action):
        """
        Controla encendido/apagado de servicios.
        URL: /api/control/container/<service>/<action>
        """
        # Map logical service ids -> container names
        mapping = {
            "scraper": ["droptools_scraper"],
            "loader": ["droptools_loader"],
            "vectorizer": ["droptools_vectorizer"],
            # For 'classifier' we intentionally map to BOTH classifier containers
            "classifier": ["droptools_classifier", "droptools_classifier_2"],
            "clusterizer": ["droptools_clusterizer"],
            "market_agent": ["droptools_market_agent"],
            "amazon_explorer": ["droptools_amazon_explorer"],
            "ai_trainer": ["droptools_ai_trainer"],
            "celery_worker": ["droptools_celery_worker"]
        }

        container_names = mapping.get(service)
        if not container_names:
            return Response({"error": "Invalid service"}, status=400)

        results = {}
        any_success = False
        for c_name in container_names:
            success, msg = control_container(c_name, action)
            results[c_name] = {"success": success, "message": msg}
            any_success = any_success or success

        if any_success:
            return Response({"status": "ok", "results": results})
        else:
            # If none of the requested actions succeeded, return error with details
            return Response({"error": "All actions failed", "results": results}, status=500)


class ClusterOrphanActionView(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request):
        """
        Ejecuta acciones reales sobre el Investigador de Diamantes.
        Actions: MERGE_SELECTED, CONFIRM_SINGLETON, TRASH
        """
        from django.db import transaction
        
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
                    target_cluster.save() # Dispara trigger de updated_at
                    msg = f"Merged {len(candidates)} candidates into Cluster {target_cluster.cluster_id}"

            return Response({"status": "success", "message": msg})
            
        except Exception as e:
            print(f"Error executing orphan action: {str(e)}")
            return Response({"error": str(e)}, status=500)


from core.models import User

class ReporterConfigView(APIView):
    """
    Gestiona la configuración del Reporter (Credenciales de Dropi).
    """
    def get(self, request):
        # Require authentication (no insecure fallbacks)
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        # Usar User directamente (ahora todo está en la tabla users)
        exec_time = user.execution_time
        # Proxy asignado (solo lectura; no se expone contraseña)
        proxy_display = None
        try:
            from core.models import UserProxyAssignment
            assignment = UserProxyAssignment.objects.select_related('proxy').filter(user=user).first()
            if assignment and assignment.proxy:
                proxy_display = f"{assignment.proxy.ip}:{assignment.proxy.port}"
        except Exception:
            pass
        return Response(
            {
                # Usar credenciales Dropi directamente del User
                "email": user.dropi_email or "",
                # No devolver password por seguridad
                "password": "",
                # Persisted schedule time (HH:MM). Default 08:00 if not set.
                "executionTime": exec_time.strftime("%H:%M") if exec_time else "08:00",
                # Proxy asignado (solo lectura; el usuario no puede cambiarlo)
                "proxy_assigned": proxy_display,
            }
        )

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
             
        try:
            # Actualizar credenciales Dropi directamente en User
            if "email" in request.data or "password" in request.data:
                email = request.data.get("email", "").strip()
                password = request.data.get("password", "").strip()
                
                if email:
                    user.dropi_email = email
                if password:
                    user.set_dropi_password_plain(password)

            # Actualizar schedule time HH:MM
            exec_time_str = request.data.get("executionTime") or request.data.get("execution_time")
            if exec_time_str is not None:
                exec_time_str = str(exec_time_str).strip()
                if exec_time_str == "":
                    user.execution_time = None
                else:
                    try:
                        hh, mm = exec_time_str.split(":")
                        user.execution_time = dt_time(hour=int(hh), minute=int(mm))
                    except Exception:
                        return Response(
                            {"error": "executionTime inválido. Usa formato HH:MM"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            user.save()
            
            return Response(
                {
                    "status": "success",
                    "message": "Configuración actualizada",
                    "executionTime": user.execution_time.strftime("%H:%M") if user.execution_time else None,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)



class ReporterStartView(APIView):
    """
    Inicia el workflow de reportes manualmente.
    - DROPTOOLS_ENV=development: ejecuta el reporter en proceso (Windows/local, Edge, sin Celery).
    - DROPTOOLS_ENV=production: encola la tarea en Celery (Docker/Linux).
    """
    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            if not user.dropi_email:
                return Response(
                    {"error": "No Dropi account configured. Please configure dropi_email in user settings."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from django.conf import settings
            from core.models import WorkflowProgress

            # Reset previous running progress
            WorkflowProgress.objects.filter(
                user=user,
                status__in=['pending', 'step1_running', 'step2_running', 'step3_running']
            ).update(status='failed', current_message='Reiniciado por nueva solicitud')

            from django.utils import timezone
            workflow_progress = WorkflowProgress.objects.create(
                user=user,
                status='step1_running',
                current_message='Iniciando...',
                messages=['Iniciando...'],
                started_at=timezone.now(),
            )

            # Desarrollo: ejecutar reporter en proceso (mismo Python, Edge, sin Celery)
            if not getattr(settings, 'REPORTER_USE_CELERY', True):
                return self._run_reporter_in_process(user, workflow_progress)

            # Producción: encolar en Celery
            return self._enqueue_reporter_celery(user, workflow_progress)

        except Exception as e:
            import traceback
            return Response(
                {"error": f"Error al iniciar workflow: {str(e)}", "traceback": traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _run_reporter_in_process(self, user, workflow_progress):
        """Ejecuta el reporter en el mismo proceso (desarrollo: Windows, Edge, navegador visible)."""
        from django.conf import settings
        from core.reporter_bot.docker_config import get_download_dir
        from core.reporter_bot.unified_reporter import UnifiedReporter
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DESARROLLO] Ejecutando reporter en proceso para user_id={user.id} (navegador visible)")
        workflow_progress.current_message = 'Ejecutando en desarrollo (en proceso)...'
        workflow_progress.save(update_fields=['current_message'])
        try:
            download_dir = get_download_dir()
            unified = UnifiedReporter(
                user_id=user.id,
                headless=False,  # desarrollo: navegador visible
                download_dir=str(download_dir),
                browser_priority=None,  # usa get_reporter_browser_order() -> Edge primero en local
            )
            stats = unified.run()
            success = stats.get('downloader', {}).get('success', False) if stats else False
            if success:
                workflow_progress.status = 'completed'
                workflow_progress.current_message = 'Completado (desarrollo)'
            else:
                workflow_progress.status = 'failed'
                workflow_progress.current_message = 'Falló descarga o comparación (desarrollo)'
            workflow_progress.save(update_fields=['status', 'current_message'])
            return Response({
                "status": "completed" if success else "completed_with_errors",
                "message": "Workflow ejecutado en desarrollo (en proceso)",
                "environment": "development",
                "workflow_progress_id": workflow_progress.id,
                "success": success,
                "stats": stats,
            })
        except Exception as e:
            import traceback
            workflow_progress.status = 'failed'
            workflow_progress.current_message = str(e)[:200]
            workflow_progress.save(update_fields=['status', 'current_message'])
            logger.exception("[DESARROLLO] Error en reporter en proceso")
            return Response({
                "error": str(e),
                "traceback": traceback.format_exc(),
                "environment": "development",
                "workflow_progress_id": workflow_progress.id,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _enqueue_reporter_celery(self, user, workflow_progress):
        """Encola el reporter en Celery (producción o desarrollo Docker)."""
        from django.conf import settings
        from core.tasks import execute_workflow_task
        run_mode = getattr(settings, 'REPORTER_RUN_MODE', 'production')
        workflow_progress.current_message = 'Encolando en Celery...'
        workflow_progress.save(update_fields=['current_message'])
        try:
            task_result = execute_workflow_task.delay(user.id)
            return Response({
                "status": "enqueued",
                "message": "Workflow encolado para ejecución asíncrona",
                "task_id": task_result.id,
                "environment": "production" if run_mode == "production" else "development_docker",
                "run_mode": run_mode,
                "workflow_progress_id": workflow_progress.id
            })
        except Exception as celery_error:
            import traceback
            workflow_progress.status = 'failed'
            workflow_progress.current_message = f'Error al encolar: {str(celery_error)}'
            workflow_progress.save(update_fields=['status', 'current_message'])
            return Response({
                "error": f"No se pudo encolar la tarea: {str(celery_error)}",
                "traceback": traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReporterEnvView(APIView):
    """
    Devuelve el modo activo para que el frontend muestre certeza.
    run_mode: development | development_docker | production
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        from django.conf import settings
        env_name = getattr(settings, 'DROPTOOLS_ENV', getattr(settings, 'DAHELL_ENV', 'production'))
        use_celery = getattr(settings, 'REPORTER_USE_CELERY', True)
        run_mode = getattr(settings, 'REPORTER_RUN_MODE', 'production')
        if run_mode == 'development_docker':
            message = "desarrollo (Docker/Celery)"
        elif run_mode == 'development':
            message = "desarrollo (reporter en proceso)"
        else:
            message = "producción (Celery)"
        return Response({
            "droptools_env": env_name,
            "reporter_use_celery": use_celery,
            "run_mode": run_mode,
            "message": message,
        })


class ReporterStopView(APIView):
    """
    Detiene todos los procesos del reporter en segundo plano (tareas Celery activas y cola).
    Solo disponible en modo desarrollo (development o development_docker) para evitar zombies
    y colisiones al volver a pulsar "Iniciar a Reportar".
    """
    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        from django.conf import settings
        run_mode = getattr(settings, 'REPORTER_RUN_MODE', 'production')
        if run_mode not in ('development', 'development_docker'):
            return Response(
                {"error": "Detener procesos solo está disponible en modo desarrollo."},
                status=status.HTTP_403_FORBIDDEN
            )

        revoked_ids = []
        purged = False
        try:
            from droptools_backend.celery import app
            # Tareas del reporter que queremos revocar
            reporter_task_names = (
                'core.tasks.execute_workflow_task',
                'core.tasks.execute_workflow_task_test',
            )
            inspect = app.control.inspect()
            active = inspect.active() or {}
            for _worker, tasks in active.items():
                for t in tasks:
                    name = t.get('name') or t.get('task')
                    if name in reporter_task_names:
                        tid = t.get('id')
                        if tid:
                            app.control.revoke(tid, terminate=True)
                            revoked_ids.append(tid)
            # Purgar la cola para quitar tareas pendientes (evitar que se ejecuten después)
            try:
                app.control.purge()
                purged = True
            except Exception:
                pass
            # Marcar progreso del usuario como detenido para que el panel muestre "Detenido"
            from core.models import WorkflowProgress
            WorkflowProgress.objects.filter(
                user=user,
                status__in=['pending', 'step1_running', 'step2_running', 'step3_running']
            ).update(
                status='failed',
                current_message='Procesos detenidos por el usuario. No hay tareas en ejecución.'
            )
            msg = f"Procesos detenidos: {len(revoked_ids)} tarea(s) revocada(s). Cola purgada: {purged}."
            return Response({
                "stopped": len(revoked_ids),
                "revoked_ids": revoked_ids,
                "purged": purged,
                "message": msg,
            })
        except Exception as e:
            import traceback
            return Response(
                {"error": str(e), "traceback": traceback.format_exc(), "revoked_ids": revoked_ids, "purged": purged},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporterStatusView(APIView):
    """
    Obtiene el estado actual de los reportes (contadores y estadísticas) y progreso del workflow
    """
    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            from datetime import datetime, timedelta, time as dt_time
            from django.utils import timezone
            from core.models import WorkflowProgress

            # Hoy y mes en timezone configurado (America/Bogota)
            now = timezone.localtime(timezone.now())
            today = now.date()
            first_of_month = today.replace(day=1)

            # Rango explícito de "hoy" (inicio y fin del día local) para evitar desfase con BD en UTC
            tz = timezone.get_current_timezone()
            today_start = tz.localize(datetime.combine(today, dt_time.min))
            today_end = today_start + timedelta(days=1)
            month_start = tz.localize(datetime.combine(first_of_month, dt_time.min))

            total_reported = OrderReport.objects.filter(
                user=user,
                status='reportado',
                updated_at__gte=today_start,
                updated_at__lt=today_end
            ).count()

            total_reported_month = OrderReport.objects.filter(
                user=user,
                status='reportado',
                updated_at__gte=month_start
            ).count()

            pending_24h = OrderReport.objects.filter(
                user=user,
                status='cannot_generate_yet',
                next_attempt_time__gt=timezone.now()
            ).count()
            total_pending = OrderReport.objects.filter(
                user=user
            ).exclude(status='reportado').count()
            
            # Obtener última actualización
            last_report = OrderReport.objects.filter(user=user).order_by('-updated_at').first()
            last_updated = last_report.updated_at.isoformat() if last_report else None
            
            # Obtener progreso del workflow más reciente
            workflow_progress = WorkflowProgress.objects.filter(user=user).order_by('-started_at').first()
            workflow_status = None
            if workflow_progress:
                workflow_status = {
                    "status": workflow_progress.status,
                    "current_message": workflow_progress.current_message,
                    "messages": workflow_progress.messages,
                    "started_at": workflow_progress.started_at.isoformat(),
                    "step1_completed_at": workflow_progress.step1_completed_at.isoformat() if workflow_progress.step1_completed_at else None,
                    "step2_completed_at": workflow_progress.step2_completed_at.isoformat() if workflow_progress.step2_completed_at else None,
                    "step3_completed_at": workflow_progress.step3_completed_at.isoformat() if workflow_progress.step3_completed_at else None,
                    "completed_at": workflow_progress.completed_at.isoformat() if workflow_progress.completed_at else None,
                }
            
            return Response({
                "total_reported": total_reported,
                "total_reported_month": total_reported_month,
                "pending_24h": pending_24h,
                "total_pending": total_pending,
                "last_updated": last_updated,
                "workflow_progress": workflow_status
            })
            
        except Exception as e:
            return Response(
                {"error": f"Error al obtener estado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporterListView(APIView):
    """
    Obtiene la lista de órdenes reportadas con información detallada
    """
    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            from django.utils import timezone
            # Obtener parámetros de paginación
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 50))
            status_filter = request.query_params.get('status', 'reportado')
            
            # Todas las órdenes reportadas del usuario (hoy, mes e histórico), no solo del día
            queryset = OrderReport.objects.filter(user=user)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Ordenar por fecha de actualización (más recientes primero)
            queryset = queryset.order_by('-updated_at')
            
            # Paginación
            start = (page - 1) * page_size
            end = start + page_size
            
            reports = queryset[start:end]
            
            # Serializar resultados
            from django.utils import timezone
            
            # Función helper para corregir encoding (ó -> ó)
            def fix_encoding(text):
                if not text: return text
                try:
                    # Intenta revertir el Mojibake: Bytes UTF-8 interpretados como CP1252
                    return text.encode('cp1252').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Si falla, el texto estaba bien o es otro error
                    return text
            
            results = []
            now = timezone.now()
            for report in reports:
                # Calcular días sin movimiento basado en created_at (cuando se detectó la orden)
                days_without_movement = None
                if report.created_at:
                    created_at = report.created_at
                    if timezone.is_naive(created_at):
                        created_at = timezone.make_aware(created_at, timezone.get_current_timezone())
                    delta = now - created_at
                    days_without_movement = delta.days
                
                results.append({
                    "id": report.id,
                    "order_phone": report.order_phone,
                    "order_id": fix_encoding(report.order_id or ""),
                    "customer_name": fix_encoding(report.customer_name or ""),
                    "product_name": fix_encoding(report.product_name or ""),
                    "status": report.status,
                    "report_generated": report.report_generated,
                    "order_state": fix_encoding(report.order_state or ""),
                    "created_at": report.created_at.isoformat(),
                    "updated_at": report.updated_at.isoformat(),
                    "next_attempt_time": report.next_attempt_time.isoformat() if report.next_attempt_time else None,
                    "days_without_movement": days_without_movement,
                    "days_stuck": days_without_movement  # Alias para compatibilidad
                })
            
            # Contar total
            total = queryset.count()
            
            return Response({
                "results": results,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            })
            
        except Exception as e:
            return Response(
                {"error": f"Error al obtener lista: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# -----------------------------------------------------------------------------
# Reporter slot system: slots, reservations, runs, progress
# -----------------------------------------------------------------------------

class ReporterSlotsView(APIView):
    """
    GET /api/reporter/slots/ — Lista horas reservables (ventana reporter) con capacidad por peso (used_points, capacity_points, available).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            config = ReporterSlotConfig.objects.first()
            hour_start = getattr(config, 'reporter_hour_start', 0) if config else 0
            hour_end = getattr(config, 'reporter_hour_end', 24) if config else 24
            slots = (
                ReporterHourSlot.objects.filter(hour__gte=hour_start, hour__lt=hour_end)
                .annotate(used_points=Sum('reservations__calculated_weight'))
                .order_by('hour')
            )
            from .serializers import ReporterSlotSerializer
            serializer = ReporterSlotSerializer(slots, many=True)
            return Response(serializer.data)
        except Exception as e:
            import logging
            logging.exception("ReporterSlotsView GET failed")
            return Response(
                {"error": f"Error al cargar horarios: {str(e)}", "hint": "Ejecuta: python manage.py migrate"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReporterReservationsView(APIView):
    """
    POST /api/reporter/reservations/ — Crear reserva (slot_id, monthly_orders_estimate).
    GET /api/reporter/reservations/me — Reserva del usuario actual.
    DELETE /api/reporter/reservations/me — Cancelar reserva.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        reservation = ReporterReservation.objects.filter(user=user).select_related('slot').first()
        if not reservation:
            return Response({"reservation": None})
        from .serializers import ReporterReservationSerializer
        serializer = ReporterReservationSerializer(reservation)
        return Response(serializer.data)

    def post(self, request):
        """
        Crear o actualizar reserva con asignación automática de slot.
        
        Body: { "monthly_orders_estimate": 500 }
        
        El sistema asigna automáticamente la mejor hora disponible según:
        - Peso del usuario (calculado desde monthly_orders_estimate)
        - Capacidad disponible en cada slot
        - Ventana horaria configurada (6am-6pm por defecto)
        """
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        
        monthly_orders_estimate = int(request.data.get('monthly_orders_estimate', 0) or 0)
        
        if monthly_orders_estimate <= 0:
            return Response(
                {"error": "monthly_orders_estimate debe ser mayor a 0"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Asignar automáticamente el mejor slot disponible
                best_slot = assign_best_available_slot(user, monthly_orders_estimate)
                
                # Eliminar reserva anterior si existe
                ReporterReservation.objects.filter(user=user).delete()
                
                # Crear nueva reserva
                reservation = ReporterReservation.objects.create(
                    user=user,
                    slot=best_slot,
                    monthly_orders_estimate=monthly_orders_estimate
                )
                
            from .serializers import ReporterReservationSerializer
            serializer = ReporterReservationSerializer(reservation)
            
            return Response({
                **serializer.data,
                "message": f"¡Reserva confirmada! Tus reportes se ejecutarán automáticamente todos los días a las {best_slot.hour:02d}:00"
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            # Error de capacidad (no hay slots disponibles)
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logging.exception("Error al crear reserva automática")
            return Response(
                {"error": f"Error al crear reserva: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        deleted, _ = ReporterReservation.objects.filter(user=user).delete()
        return Response({"deleted": deleted > 0})


class ReporterRunsView(APIView):
    """
    GET /api/reporter/runs/ — Lista runs recientes (por usuario o por slot).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            if not user or not user.is_authenticated:
                return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
            from django.utils import timezone
            from datetime import timedelta
            days = int(request.query_params.get('days', 7))
            since = timezone.now() - timedelta(days=days)
            runs = ReporterRun.objects.filter(
                run_users__user=user,
                scheduled_at__gte=since
            ).select_related('slot').distinct().order_by('-scheduled_at')[:20]
            from .serializers import ReporterRunSerializer
            serializer = ReporterRunSerializer(runs, many=True)
            return Response(serializer.data)
        except Exception as e:
            import logging
            logging.exception("ReporterRunsView GET failed")
            return Response(
                {"error": f"Error al cargar runs: {str(e)}", "hint": "Ejecuta: python manage.py migrate"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReporterRunProgressView(APIView):
    """
    GET /api/reporter/runs/<run_id>/progress/ — Progreso detallado de una Run (por usuario).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
        run = ReporterRun.objects.filter(id=run_id).select_related('slot').first()
        if not run:
            return Response({"error": "Run no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        run_users = ReporterRunUser.objects.filter(run=run).select_related('user')
        users_progress = []
        for ru in run_users:
            users_progress.append({
                "user_id": ru.user_id,
                "username": ru.user.username if ru.user_id else None,
                "download_compare_status": ru.download_compare_status,
                "download_compare_completed_at": ru.download_compare_completed_at.isoformat() if ru.download_compare_completed_at else None,
                "total_pending_orders": ru.total_pending_orders,
                "total_ranges": ru.total_ranges,
                "ranges_completed": ru.ranges_completed,
            })
        return Response({
            "run_id": run.id,
            "run_status": run.status,
            "scheduled_at": run.scheduled_at.isoformat(),
            "slot_hour": run.slot.hour if run.slot_id else None,
            "users": users_progress,
        })


class ClientDashboardAnalyticsView(APIView):
    """
    Analytics para el dashboard del cliente: KPIs, regiones, top productos y
    efectividad por transportadora, derivados de RawOrderSnapshot (reportes Dropi).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        from django.db.models.functions import Coalesce

        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        period = (request.query_params.get("period") or "month").strip().lower()
        if period not in ("day", "week", "fortnight", "month"):
            period = "month"
        batch_id_param = request.query_params.get("batch_id")

        now = timezone.now()
        # day = solo hoy (desde medianoche en timezone del servidor)
        if period == "day":
            today_start = timezone.make_aware(
                datetime.combine(now.date(), dt_time.min),
                timezone.get_current_timezone()
            )
            since = today_start
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "fortnight":
            since = now - timedelta(days=15)
        else:
            # Histórico: último año para que se vean datos de hace muchos días
            since = now - timedelta(days=365)

        period_label = {
            "day": "Hoy",
            "week": "Última semana",
            "fortnight": "Última quincena",
            "month": "Histórico (último año)",
        }.get(period, "Histórico (último año)")

        empty_response = {
            "kpis": {
                "total_orders": 0,
                "delivered": 0,
                "products_sold": 0,
                "total_revenue": 0,
                "confirmation_pct": 0.0,
                "cancellation_pct": 0.0,
            },
            "by_region": [],
            "top_products": [],
            "by_carrier": [],
            "last_updated": None,
            "period_used": period,
            "period_label": period_label,
        }

        try:
            if batch_id_param:
                try:
                    batch_id = int(batch_id_param)
                except (TypeError, ValueError):
                    return Response(empty_response, status=status.HTTP_200_OK)
                batches = ReportBatch.objects.filter(
                    user=user, id=batch_id, status="SUCCESS"
                )[:1]
            else:
                batches = ReportBatch.objects.filter(
                    user=user,
                    status="SUCCESS",
                    created_at__gte=since,
                ).order_by("-created_at")

            batch_ids = list(batches.values_list("id", flat=True))
            # Si no hay batches en el período, usar los más recientes disponibles (fallback histórico)
            if not batch_ids and period != "day":
                batches_fallback = ReportBatch.objects.filter(
                    user=user,
                    status="SUCCESS",
                ).order_by("-created_at")[:10]
                batch_ids = list(batches_fallback.values_list("id", flat=True))
                if batch_ids:
                    batches = batches_fallback
                    period_label = "Histórico (últimos datos disponibles)"
            if not batch_ids:
                return Response(empty_response, status=status.HTTP_200_OK)

            last_batch = batches.first()
            last_updated = last_batch.created_at.isoformat() if last_batch else None

            snapshots = RawOrderSnapshot.objects.filter(batch_id__in=batch_ids)
            total_orders = snapshots.count()
            if total_orders == 0:
                return Response({
                    **empty_response,
                    "last_updated": last_updated,
                }, status=status.HTTP_200_OK)

            delivered_count = snapshots.filter(
                current_status__icontains="ENTREGAD"
            ).count()
            cancelled_count = snapshots.filter(
                current_status__icontains="CANCELAD"
            ).count()
            agg_qty = snapshots.aggregate(s=Coalesce(Sum("quantity"), 0))
            agg_rev = snapshots.aggregate(s=Coalesce(Sum("total_amount"), 0))
            products_sold = int(agg_qty.get("s") or 0)
            _rev = agg_rev.get("s")
            total_revenue = float(_rev) if _rev is not None else 0.0
            confirmation_pct = round(
                (total_orders - cancelled_count) / total_orders * 100, 1
            ) if total_orders else 0.0
            cancellation_pct = round(cancelled_count / total_orders * 100, 1) if total_orders else 0.0

            by_region_qs = (
                snapshots.values("department")
                .annotate(
                    orders=Count("id"),
                    revenue=Coalesce(Sum("total_amount"), 0),
                )
                .order_by("-orders")
            )
            by_region = []
            for x in by_region_qs:
                try:
                    rev = x.get("revenue")
                    by_region.append({
                        "department": (x.get("department") or "Sin departamento").strip() or "Sin departamento",
                        "orders": x.get("orders") or 0,
                        "revenue": float(rev) if rev is not None else 0.0,
                    })
                except (TypeError, ValueError):
                    continue

            top_products_qs = (
                snapshots.values("product_name")
                .annotate(
                    quantity=Coalesce(Sum("quantity"), 0),
                    revenue=Coalesce(Sum("total_amount"), 0),
                )
                .order_by("-quantity")[:10]
            )
            top_products = []
            for x in top_products_qs:
                try:
                    qty, rev = x.get("quantity"), x.get("revenue")
                    top_products.append({
                        "product_name": (x.get("product_name") or "Sin nombre").strip() or "Sin nombre",
                        "quantity": int(qty) if qty is not None else 0,
                        "revenue": float(rev) if rev is not None else 0.0,
                    })
                except (TypeError, ValueError):
                    continue

            carriers = list(
                snapshots.exclude(carrier__isnull=True)
                .exclude(carrier="")
                .values_list("carrier", flat=True)
                .distinct()
            )
            by_carrier = []
            for carrier in carriers:
                carrier_snap = snapshots.filter(carrier=carrier)
                total_c = carrier_snap.count()
                delivered_c = carrier_snap.filter(
                    current_status__icontains="ENTREGAD"
                ).count()
                pct = round(delivered_c / total_c * 100, 1) if total_c else 0
                by_carrier.append({
                    "carrier": carrier,
                    "total": total_c,
                    "delivered": delivered_c,
                    "effectiveness_pct": pct,
                })
            by_carrier.sort(key=lambda x: -x["effectiveness_pct"])

            return Response({
                "kpis": {
                    "total_orders": int(total_orders),
                    "delivered": int(delivered_count),
                    "products_sold": int(products_sold),
                    "total_revenue": float(total_revenue),
                    "confirmation_pct": float(confirmation_pct),
                    "cancellation_pct": float(cancellation_pct),
                },
                "by_region": by_region,
                "top_products": top_products,
                "by_carrier": by_carrier,
                "last_updated": last_updated,
                "period_used": period,
                "period_label": period_label,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import logging
            logging.exception("ClientDashboardAnalyticsView error: %s", e)
            # Devolver estructura vacía en lugar de 500 para que el dashboard cargue y muestre "Aún no hay reportes"
            return Response(empty_response, status=status.HTTP_200_OK)


# =============================================================================
# AUTH API (Login real contra BD)
# =============================================================================

class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "").strip()
        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # Permitimos login por email o username
        user_obj = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        if not user_obj:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        # Autenticar usando el username del usuario encontrado
        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"error": "Usuario inactivo"}, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "subscription_active": user.subscription_active,
                    "full_name": user.full_name,
                    "is_admin": bool(user.role == "ADMIN"),
                },
            },
            status=status.HTTP_200_OK,
        )


class GoogleAuthView(APIView):
    """
    Endpoint para autenticación con Google OAuth.
    
    POST /api/auth/google/
    Body: { "token": "google_id_token" }
    
    Retorna:
    - user: Información del usuario
    - token: Token de autenticación de Django
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        import logging
        from rest_framework.serializers import ValidationError as DRFValidationError
        from .serializers import GoogleAuthSerializer

        logger = logging.getLogger(__name__)
        serializer = GoogleAuthSerializer(data=request.data)

        if not serializer.is_valid():
            err_msg = serializer.errors.get('token', serializer.errors)
            if isinstance(err_msg, list):
                err_msg = err_msg[0] if err_msg else str(serializer.errors)
            return Response(
                {'error': err_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin(),
                    'subscription_tier': user.subscription_tier,
                    'subscription_active': user.subscription_active,
                }
            }, status=status.HTTP_200_OK)
        except DRFValidationError as e:
            detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(detail, list):
                detail = detail[0] if detail else str(detail)
            if isinstance(detail, dict):
                detail = str(detail)
            return Response({'error': detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Google auth 500: %s", e)
            return Response(
                {'error': f'Error al autenticar con Google: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuthRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Registro público:
        - Crea User + UserProfile (CLIENT + BRONZE por defecto)
        - Devuelve token para auto-login
        """
        full_name = (request.data.get("full_name") or request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            return Response({"error": "Este email ya está registrado"}, status=status.HTTP_400_BAD_REQUEST)

        # Use email as username (simple + consistent)
        user = User.objects.create_user(username=email, email=email, password=password)
        user.is_active = True
        # Configurar campos de perfil directamente en User
        user.full_name = full_name
        user.role = User.ROLE_CLIENT
        user.subscription_tier = User.TIER_BRONZE
        # En desarrollo (DEBUG): bronce activo por defecto para poder probar la app
        user.subscription_active = getattr(settings, 'DEBUG', False)
        user.save()

        # Asignar proxy disponible al nuevo usuario (si hay proxies configurados)
        try:
            from core.services.proxy_allocator_service import assign_proxy_to_user
            assign_proxy_to_user(user.id)
        except Exception:
            pass  # Registro exitoso aunque no haya proxy disponible

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "subscription_active": user.subscription_active,
                    "full_name": user.full_name,
                    "is_admin": bool(user.role == "ADMIN"),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Usar User directamente (ahora todo está en la tabla users)
        user = request.user
        return Response(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "subscription_tier": user.subscription_tier,
                    "subscription_active": user.subscription_active,
                    "full_name": user.full_name,
                    "is_admin": bool(user.role == "ADMIN"),
                }
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# ADMIN: Users & Subscriptions management (no payments)
# =============================================================================


class AdminUsersView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        users = User.objects.all().order_by("id")
        rows = []
        for u in users:
            # Usar User directamente (ahora todo está en la tabla users)
            rows.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "username": u.username,
                    "is_active": u.is_active,
                    "profile": {
                        "full_name": u.full_name,
                        "role": u.role,
                        "subscription_tier": u.subscription_tier,
                        "subscription_active": u.subscription_active,
                    },
                }
            )
        return Response({"users": rows}, status=status.HTTP_200_OK)


class AdminSetUserSubscriptionView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, user_id: int):
        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        tier = (request.data.get("subscription_tier") or "").upper().strip()
        active = request.data.get("subscription_active")

        valid_tiers = {"BRONZE", "SILVER", "GOLD", "PLATINUM"}
        if tier and tier not in valid_tiers:
            return Response({"error": "Tier inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar directamente en User (ahora todo está en la tabla users)
        if tier:
            target.subscription_tier = tier
        if active is not None:
            target.subscription_active = bool(active)
        target.save()

        return Response(
            {
                "status": "ok",
                "user_id": target.id,
                "subscription_tier": target.subscription_tier,
                "subscription_active": target.subscription_active,
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Dropi Accounts API (múltiples cuentas secundarias por usuario)
# =============================================================================

class DropiAccountsView(APIView):
    """
    Gestiona la cuenta Dropi del usuario (ahora está en la tabla users)
    Nota: Ahora cada usuario tiene solo UNA cuenta Dropi (dropi_email y dropi_password)
    """
    permission_classes = [MinSubscriptionTier("BRONZE")]

    def get(self, request):
        """Retorna la cuenta Dropi del usuario actual"""
        user = request.user
        
        # Retornar la cuenta Dropi del usuario (ahora está en User)
        accounts = []
        if user.dropi_email:
            accounts.append({
                "id": user.id,  # Usar el ID del usuario
                "label": "reporter",  # Label fijo para compatibilidad
                "email": user.dropi_email,
                "is_default": True  # Siempre es default porque solo hay una
            })
        
        return Response(
            {"accounts": accounts},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """Actualiza la cuenta Dropi del usuario"""
        user = request.user
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar dropi_email y dropi_password en User
        user.dropi_email = email
        user.set_dropi_password_plain(password)
        user.save()
        
        return Response(
            {
                "account": {
                    "id": user.id,
                    "label": "reporter",
                    "email": user.dropi_email,
                    "is_default": True
                }
            },
            status=status.HTTP_201_CREATED,
        )


class DropiAccountSetDefaultView(APIView):
    """
    Marca una cuenta Dropi como default (ahora es un no-op porque solo hay una cuenta)
    Se mantiene por compatibilidad con el frontend
    """
    permission_classes = [MinSubscriptionTier("BRONZE")]

    def post(self, request, account_id: int):
        """
        Como ahora solo hay una cuenta Dropi por usuario, esta vista simplemente retorna OK
        Se mantiene por compatibilidad con el frontend
        """
        user = request.user
        
        # Verificar que el account_id corresponda al usuario actual
        if account_id != user.id:
            return Response({"error": "Cuenta no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        
        # Como solo hay una cuenta, siempre es default
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
