# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from .models import (
    Product,
    UniqueProductCluster,
    ProductEmbedding,
    Warehouse,
    Category,
    ProductClusterMembership,
    AIFeedback,
    ClusterDecisionLog,
    UserProfile,
    DropiAccount,
)
from .permissions import IsAdminRole, MinSubscriptionTier
from datetime import datetime, timedelta
import pathlib
import json
from .docker_utils import get_container_stats, control_container

class DashboardStatsView(APIView):
    permission_classes = [IsAdminRole]
    def get(self, request):
        """
        Centro de Comando EstratÃ©gico (V2).
        Retorna inteligencia real del mercado y oportunidades tÃ¡cticas, 
        ya no solo estado del servidor.
        """
        
        # ---------------------------------------------------------
        # 1. FLASH OPPORTUNITIES (Los mejores hallazgos de las Ãºltimas 48h)
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
        
        # 2. Traer todas las membresÃ­as relevantes de una sola vez
        memberships = ProductClusterMembership.objects.filter(
            product_id__in=p_ids
        ).select_related('cluster')
        
        # 3. Crear un diccionario para acceso instantÃ¡neo O(1)
        # Map: product_id -> cluster_obj
        cluster_map = {m.product_id: m.cluster for m in memberships}

        tactical_feed = []
        for p in flash_ops:
            # Ahora la bÃºsqueda es en memoria (InstantÃ¡nea)
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
        # 2. MARKET RADAR (Inteligencia por CategorÃ­a)
        # ---------------------------------------------------------
        # OPTIMIZACION: Query Ãºnica con Agregaciones (Elimina N+1 Problems)
        # Calculamos conteo, precio promedio, margen promedio y competencia promedio en una sola consulta.
        
        radar_qs = Category.objects.filter(
            productcategory__product__isnull=False
        ).annotate(
            product_count=Count('productcategory__product', distinct=True),
            avg_price=Avg('productcategory__product__sale_price'),
            avg_margin=Avg('productcategory__product__profit_margin'),
            # Competencia: Promedio de competidores de los clusters asociados a los productos de la categorÃ­a
            avg_competitiveness=Avg('productcategory__product__cluster_membership__cluster__total_competitors')
        ).filter(
            product_count__gte=5 # Solo categorÃ­as relevantes
        ).order_by('-avg_margin') # Priorizar las mÃ¡s rentables

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
            "market_radar": radar_data[:15] # Top 15 categorÃ­as para no saturar el grÃ¡fico
        })

from django.db import connection
# from .ai_utils import get_image_embedding

class GoldMineView(APIView):
    permission_classes = [IsAdminRole]
    def post(self, request):
        """BÃºsqueda Visual (Reverse Image Search)"""
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
        # Queremos saber a quÃ© cluster pertenecen esos productos similares
        # y devolver el cluster entero o el representante
        results = []
        if similar_pids:
            # Traer info de clusters donde esos productos son miembros o representantes
            # SimplificaciÃ³n: Devolvemos los productos directos encontrados, enriquecidos con su cluster info
            products = Product.objects.filter(product_id__in=similar_pids).select_related('supplier')
            
            # --- OPTIMIZACION N+1 ---
            # Cargar info de clusters en batch
            product_ids = [p.product_id for p in products]
            memberships = ProductClusterMembership.objects.filter(product_id__in=product_ids).select_related('cluster')
            cluster_map = {m.product_id: m.cluster for m in memberships}

            # Map distance
            dist_map = {r[0]: r[1] for r in rows}
            
            for p in products:
                # BÃºsqueda en memoria O(1)
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
        """BÃºsqueda Textual y Filtros"""
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
        
        # Filtro opcional de precio si lo envÃ­an
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
            
        # Filtro de CategorÃ­a
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
        """Retorna estadÃ­sticas globales de distribuciÃ³n de competidores"""
        
        # Filtros Base (Search, Category, Price)
        # NOTA: NO filtramos por min_comp/max_comp aquÃ­, para mostrar el panorama completo
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

        # AgregaciÃ³n: Contar cuantos clusters tienen X competidores
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
    MÃ©tricas para el Sidebar del Cluster Lab (XP y Progreso).
    """
    def get(self, request):
        try:
            # 1. Total AuditorÃ­as Realizadas (XP del Usuario)
            total_feedback = AIFeedback.objects.count()
            
            # --- XP DIARIA ---
            now = timezone.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_xp = AIFeedback.objects.filter(created_at__gte=start_of_day).count()
            
            # 2. Total Decisiones IA Registradas
            total_logs = ClusterDecisionLog.objects.count()

            # 3. PrecisiÃ³n Humana (Correcciones vs Confirmaciones)
            correct_feedback = AIFeedback.objects.filter(feedback='CORRECT').count()
            incorrect_feedback = AIFeedback.objects.filter(feedback='INCORRECT').count()
            
            # --- SALUD DEL SISTEMA ---
            # HuÃ©rfanos: Clusters con singletons
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
    1. GET: Retorna los Ãºltimos logs de decisiÃ³n del Clusterizer (Persistent DB).
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
    Retorna productos que estÃ¡n en clusters 'SINGLETON' (solitarios)
    para auditar por quÃ© no se unieron.
    """
    def get(self, request):
        # Buscar clusters con tamaÃ±o 1 (o marcados como SINGLETON si tuvieramos ese flag)
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
        Simula la bÃºsqueda de candidatos para un producto huÃ©rfano.
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
                    
                    # Calcular Scores (Misma lÃ³gica que Clusterizer V3)
                    visual_score = max(0, 1.0 - float(dist))
                    text_score = SequenceMatcher(None, str(target_title).lower(), str(c_title).lower()).ratio()
                    final_score = (0.6 * visual_score) + (0.4 * text_score)
                    
                    # LÃ³gica de Rescate (Simulada)
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
        """Listar todas las categorÃ­as disponibles"""
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
            "scraper": "dahell_scraper",
            "loader": "dahell_loader",
            "vectorizer": "dahell_vectorizer",
            "classifier": "dahell_classifier",
            "clusterizer": "dahell_clusterizer",
            "shopify": "dahell_shopify", 
            "ai_trainer": "dahell_ai_trainer"
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
        Guarda el feedback del usuario sobre una decisiÃ³n de clustering (RICHER DATA).
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
            "scraper": "dahell_scraper",
            "loader": "dahell_loader",
            "vectorizer": "dahell_vectorizer",
            "classifier": "dahell_classifier",
            "clusterizer": "dahell_clusterizer",
            "market_agent": "dahell_market_agent",
            "amazon_explorer": "dahell_amazon_explorer",
            "ai_trainer": "dahell_ai_trainer",
            "db": "dahell_db"
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
            "scraper": ["dahell_scraper"],
            "loader": ["dahell_loader"],
            "vectorizer": ["dahell_vectorizer"],
            # For 'classifier' we intentionally map to BOTH classifier containers
            "classifier": ["dahell_classifier", "dahell_classifier_2"],
            "clusterizer": ["dahell_clusterizer"],
            "market_agent": ["dahell_market_agent"],
            "amazon_explorer": ["dahell_amazon_explorer"],
            "ai_trainer": ["dahell_ai_trainer"]
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

            print(f"âš¡ ORPHAN ACTION: {action} on Target {target_id}")

            with transaction.atomic():
                if action == 'TRASH':
                    # Incinerar producto: Borrar Embeddings y ClusterMembership
                    # Esto lo saca del radar del sistema de IA y Clustering
                    ProductEmbedding.objects.filter(product_id=target_id).delete()
                    ProductClusterMembership.objects.filter(product_id=target_id).delete()
                    # Opcional: Marcar producto como inactivo si tuvieramos campo status
                    # product.status = 'TRASH'
                    # product.save()
                    msg = "Product incinerated (Embeddings & Cluster info removed)"

                elif action == 'CONFIRM_SINGLETON':
                    # Confirmar que es Ãºnico. 
                    # Simplemente nos aseguramos que tenga un cluster propio y valido.
                    # El hecho de que el usuario lo revise ya valida su existencia.
                    # PodrÃ­amos agregar un flag 'verified_by_human' en el futuro.
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
                        # Borrar membresÃ­a anterior
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


from django.contrib.auth.models import User

class ReporterConfigView(APIView):
    """
    Gestiona la configuración del Reporter (Credenciales de Dropi).
    """
    def get(self, request):
        # Require authentication (no insecure fallbacks)
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        # Obtener o crear perfil
        try:
            profile = user.profile
        except Exception: # UserProfile.DoesNotExist might not be available if import failed previously
            try:
                profile = UserProfile.objects.create(user=user)
            except Exception as e:
                # Si UserProfile no está importado? (imported from .models above)
                from .models import UserProfile
                profile, _ = UserProfile.objects.get_or_create(user=user)

        return Response({
            "email": profile.dropi_email or "",
            # Never return secrets to the frontend; configuration is managed via DropiAccounts API.
            "password": "",
            "executionTime": "08:00" # Placeholder, no persistido aún
        })

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
             
        try:
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            profile.dropi_email = request.data.get('email')
            profile.dropi_password = request.data.get('password')
            profile.save()
            
            return Response({"status": "success", "message": "Credentials updated"})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# =============================================================================
# AUTH API (Login real contra BD)
# =============================================================================

class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # Permitimos login por email o username
        user_obj = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        if not user_obj:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(username=user_obj.username, password=password)
        if not user:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"error": "Usuario inactivo"}, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)
        profile, _ = UserProfile.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": profile.role,
                    "subscription_tier": getattr(profile, "subscription_tier", "BRONZE"),
                    "subscription_active": bool(getattr(profile, "subscription_active", False)),
                    "full_name": profile.full_name,
                    "is_admin": bool(profile.role == "ADMIN"),
                },
            },
            status=status.HTTP_200_OK,
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
        user.save()

        profile = UserProfile.objects.create(
            user=user,
            full_name=full_name,
            role=UserProfile.ROLE_CLIENT,
            subscription_tier=getattr(UserProfile, "TIER_BRONZE", "BRONZE"),
            subscription_active=False,
        )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": profile.role,
                    "subscription_tier": getattr(profile, "subscription_tier", "BRONZE"),
                    "subscription_active": bool(getattr(profile, "subscription_active", False)),
                    "full_name": profile.full_name,
                    "is_admin": bool(profile.role == "ADMIN"),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(
            {
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "role": profile.role,
                    "subscription_tier": getattr(profile, "subscription_tier", "BRONZE"),
                    "subscription_active": bool(getattr(profile, "subscription_active", False)),
                    "full_name": profile.full_name,
                    "is_admin": bool(profile.role == "ADMIN"),
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
            p, _ = UserProfile.objects.get_or_create(user=u)
            rows.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "username": u.username,
                    "is_active": u.is_active,
                    "profile": {
                        "full_name": p.full_name,
                        "role": p.role,
                        "subscription_tier": getattr(p, "subscription_tier", "BRONZE"),
                        "subscription_active": bool(getattr(p, "subscription_active", False)),
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

        prof, _ = UserProfile.objects.get_or_create(user=target)
        if tier:
            prof.subscription_tier = tier
        if active is not None:
            prof.subscription_active = bool(active)
        prof.save()

        return Response(
            {
                "status": "ok",
                "user_id": target.id,
                "subscription_tier": getattr(prof, "subscription_tier", "BRONZE"),
                "subscription_active": bool(getattr(prof, "subscription_active", False)),
            },
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Dropi Accounts API (múltiples cuentas secundarias por usuario)
# =============================================================================

class DropiAccountsView(APIView):
    permission_classes = [MinSubscriptionTier("BRONZE")]

    def get(self, request):
        accounts = DropiAccount.objects.filter(user=request.user).order_by("-is_default", "id")
        return Response(
            {
                "accounts": [
                    {
                        "id": a.id,
                        "label": a.label,
                        "email": a.email,
                        "is_default": a.is_default,
                    }
                    for a in accounts
                ]
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        label = (request.data.get("label") or "default").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        is_default = bool(request.data.get("is_default", False))

        if not email or not password:
            return Response({"error": "email y password son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # Si se marca default, apagamos los demás
        if is_default:
            DropiAccount.objects.filter(user=request.user, is_default=True).update(is_default=False)

        acct = DropiAccount(user=request.user, label=label, email=email, is_default=is_default)
        acct.set_password_plain(password)
        acct.save()
        return Response(
            {"account": {"id": acct.id, "label": acct.label, "email": acct.email, "is_default": acct.is_default}},
            status=status.HTTP_201_CREATED,
        )


class DropiAccountSetDefaultView(APIView):
    permission_classes = [MinSubscriptionTier("BRONZE")]

    def post(self, request, account_id: int):
        acct = DropiAccount.objects.filter(user=request.user, id=account_id).first()
        if not acct:
            return Response({"error": "Cuenta no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        DropiAccount.objects.filter(user=request.user, is_default=True).exclude(id=acct.id).update(is_default=False)
        acct.is_default = True
        acct.save()
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
