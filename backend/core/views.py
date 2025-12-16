# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from .models import Product, UniqueProductCluster, ProductEmbedding, Warehouse, Category, ProductClusterMembership, AIFeedback
from datetime import datetime, timedelta
import pathlib
import json
from .docker_utils import get_container_stats, control_container

class DashboardStatsView(APIView):
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
        # Agregamos datos para ver qué categorías están saturadas y cuáles son rentables.
        
        # Filtramos categorías con al menos 5 productos para evitar ruido
        categories = Category.objects.annotate(
            product_count=Count('productcategory__product')
        ).filter(product_count__gte=5)
        
        # Calculamos promedios.
        # Nota: La competencia promedio es difícil de sacar directo por ORM sin subqueries complejas,
        # usaremos el promedio de precio como proxy de "Premium" y el count como "Volumen".
        # Para "Saturacion" necesitamos cruzar con Clusters, lo haremos en python para mantenerlo simple y seguro ahora.
        
        radar_data = []
        
        for cat in categories:
            # Avg Price & Margin
            stats = Product.objects.filter(productcategory__category=cat).aggregate(
                avg_price=Avg('sale_price'),
                avg_margin=Avg('profit_margin')
            )
            
            # Competencia Promedio (Muestreo rápido)
            # Tomamos una muestra de 20 productos de la categoría para estimar su saturación
            sample_pids = Product.objects.filter(productcategory__category=cat).values_list('product_id', flat=True)[:20]
            if not sample_pids: continue
            
            # Avg competitors de la muestra
            avg_comp = 0
            clusters_involved = ProductClusterMembership.objects.filter(product_id__in=sample_pids).select_related('cluster')
            if clusters_involved.exists():
                comps = [m.cluster.total_competitors for m in clusters_involved if m.cluster]
                if comps:
                    avg_comp = sum(comps) / len(comps)
            
            radar_data.append({
                "category": cat.name,
                "volume": cat.product_count,
                "avg_price": round(stats['avg_price'] or 0, 2),
                "avg_margin": round(stats['avg_margin'] or 0, 2),
                "competitiveness": round(avg_comp, 1) # Eje X del Radar
            })
            
        # Ordenar por oportunidad (Margen alto)
        radar_data.sort(key=lambda x: x['avg_margin'], reverse=True)

        return Response({
            "tactical_feed": tactical_feed,
            "market_radar": radar_data[:15] # Top 15 categorías para no saturar el gráfico
        })

from django.db import connection
from .ai_utils import get_image_embedding

class GoldMineView(APIView):
    def post(self, request):
        """Búsqueda Visual (Reverse Image Search)"""
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=400)
            
        uploaded_file = request.FILES['image']
        
        # 1. Vectorizar imagen llegada
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
            print(f"💰 Price filters - Min: {min_price}, Max: {max_price}")
        
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





class ClusterAuditView(APIView):
    """
    API para el 'Cluster Lab'.
    1. GET: Retorna los últimos logs de decisión del Clusterizer (JSONL).
    2. POST: (Opcional) Simula un match entre dos productos (Dry Run).
    """
    def get(self, request):
        log_path = pathlib.Path("/app/logs/cluster_audit.jsonl")
        logs = []
        
        # Leer últimas 100 líneas
        try:
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Leemos todo y tomamos el final
                    lines = f.readlines()[-100:]
                    for line in lines:
                        line = line.strip()
                        if not line: continue
                        try:
                            # Intentar reparar JSON truncado si es común
                            if not line.endswith('}'): line += '}'
                            logs.append(json.loads(line))
                        except: 
                            continue
            
            # Invertir para ver lo más reciente primero
            logs.reverse()
            return Response(logs)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class ClusterOrphansView(APIView):
    """
    Retorna productos que están en clusters 'SINGLETON' (solitarios)
    para auditar por qué no se unieron.
    """
    def get(self, request):
        # Buscar clusters con tamaño 1 (o marcados como SINGLETON si tuvieramos ese flag)
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
        Retorna: Lista de Top 5 Candidatos con scores detallados.
        """
        try:
            target_pid = request.data.get('product_id')
            if not target_pid: return Response({"error": "Missing product_id"}, status=400)

            # 1. Obtener datos del producto objetivo (Vector + Texto)
            from django.db import connection
            
            with connection.cursor() as cur:
                # Get Target Info
                cur.execute("""
                    SELECT p.title, pe.embedding_visual 
                    FROM products p 
                    JOIN product_embeddings pe ON p.product_id = pe.product_id 
                    WHERE p.product_id = %s
                """, (target_pid,))
                res = cur.fetchone()
                if not res: return Response({"error": "Product not found or not vectorized"}, status=404)
                
                target_title, target_vector = res
                
                # 2. Buscar Top 10 Candidatos Visuales
                cur.execute("""
                    SELECT 
                        p.product_id, p.title, p.sale_price, p.url_image_s3,
                        (pe.embedding_visual <=> %s) as dist 
                    FROM product_embeddings pe
                    JOIN products p ON pe.product_id = p.product_id
                    WHERE pe.product_id != %s AND pe.embedding_visual IS NOT NULL
                    ORDER BY dist ASC
                    LIMIT 10
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
                    "target": {"id": target_pid, "title": target_title},
                    "candidates": candidates
                })

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CategoriesView(APIView):
    def get(self, request):
        """Listar todas las categorías disponibles"""
        cats = Category.objects.all().order_by('name')
        data = [{"id": c.id, "name": c.name} for c in cats]
        return Response(data)

class SystemLogsView(APIView):
    def get(self, request):
        log_dir = pathlib.Path("/app/logs")
        logs = []
        
        # Archivos a leer
        files = {
            "scraper": "scraper.log",
            "clusterizer": "clusterizer.log",
            "loader": "loader.log",
            "vectorizer": "vectorizer.log",
            "ai_trainer": "ai_trainer.log"
        }
        
        def tail(f, lines=50):
            total_lines_wanted = lines
            BLOCK_SIZE = 1024
            f.seek(0, 2)
            block_end_byte = f.tell()
            lines_to_go = total_lines_wanted
            block_number = -1
            blocks = []
            
            # Leer bloques desde el final hacia atras (Binary Mode)
            while lines_to_go > 0 and block_end_byte > 0:
                if (block_end_byte - BLOCK_SIZE > 0):
                    f.seek(block_number*BLOCK_SIZE, 2)
                    blocks.append(f.read(BLOCK_SIZE))
                else:
                    f.seek(0,0)
                    blocks.append(f.read(block_end_byte))
                
                lines_found = blocks[-1].count(b'\n')
                lines_to_go -= lines_found
                block_end_byte -= BLOCK_SIZE
                block_number -= 1
            
            all_read_bytes = b''.join(reversed(blocks))
            return all_read_bytes.decode('utf-8', errors='replace').splitlines()[-total_lines_wanted:]

        for service, filename in files.items():
            fpath = log_dir / filename
            if fpath.exists():
                try:
                    # Abrir en BINARY mode para soportar seek negativo
                    with open(fpath, 'rb') as f:
                        last_lines = tail(f, lines=30)
                        
                        for line in last_lines:
                            if line.strip():
                                logs.append({
                                    "service": service,
                                    "message": line.strip(),
                                    "raw": line
                                })
                except Exception as e:
                    logs.append({"service": service, "message": f"Error reading log: {str(e)}"})
            else:
                 pass
        
        return Response(logs)

class ClusterFeedbackView(APIView):
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
    def get(self, request):
        """
        Retorna estado robusto de los contenedores (CPU, RAM, Status).
        """
        containers = {
            "scraper": "dahell_scraper",
            "loader": "dahell_loader",
            "vectorizer": "dahell_vectorizer",
            "clusterizer": "dahell_clusterizer",
            "ai_trainer": "dahell_ai_trainer",
            "db": "dahell_db"
        }
        
        data = {}
        for friendly_name, c_name in containers.items():
            data[friendly_name] = get_container_stats(c_name)
            
        return Response(data)

class ContainerControlView(APIView):
    def post(self, request, service, action):
        """
        Controla encendido/apagado de servicios.
        URL: /api/control/container/<service>/<action>
        """
        mapping = {
            "scraper": "dahell_scraper",
            "loader": "dahell_loader",
            "vectorizer": "dahell_vectorizer",
            "clusterizer": "dahell_clusterizer",
            "ai_trainer": "dahell_ai_trainer"
        }
        
        container_name = mapping.get(service)
        if not container_name:
            return Response({"error": "Invalid service"}, status=400)
            
        success, msg = control_container(container_name, action)
        if success:
            return Response({"status": "ok", "message": msg})
        else:
            return Response({"error": msg}, status=500)

