from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from .models import Product, UniqueProductCluster, ProductEmbedding, Warehouse, Category, ProductClusterMembership
from datetime import datetime, timedelta
import pathlib

class DashboardStatsView(APIView):
    def get(self, request):
        # 1. Estadísticas Generales
        total_products = Product.objects.count()
        clusters = UniqueProductCluster.objects.count()
        vectors = ProductEmbedding.objects.count()

        # 2. Métricas de Backlog (KPIs Salud)
        # Cuenta archivos .jsonl en raw_data
        raw_dir = pathlib.Path("/app/raw_data")
        pending_jsonl = len(list(raw_dir.glob("*.jsonl"))) if raw_dir.exists() else 0

        # Productos con imagen pero SIN embedding (o embedding antiguo)
        # Nota: La tabla product_embeddings es 1-1. Si no existe registro o es NULL, falta.
        # Aproximación rápida: (Total Prods con Foto) - (Total Vectores)
        total_with_img = Product.objects.filter(url_image_s3__isnull=False).exclude(url_image_s3="").count()
        pending_vectorization = max(0, total_with_img - vectors)

        # 3. Tasa de Errores (Error Rate) - Última Hora
        # Leemos logs rápidamente buscando "ERROR" en las ultimas lineas
        error_count_last_hour = 0
        log_dir = pathlib.Path("/app/logs")
        try:
            for log_file in log_dir.glob("*.log"):
                with open(log_file, 'r', encoding='utf-8') as f:
                    # Leemos ultimas 100 lineas para un check rapido
                    lines = f.readlines()[-200:]
                    for line in lines:
                        if "ERROR" in line or "Exception" in line:
                            error_count_last_hour += 1
        except:
            pass # Fail soft

        # Datos para gráfico (Simulados - Idealmente conectar a una tabla de historicos)
        chart_data = [
            {"name": "08:00", "products": 4000, "profit": 2400, "errors": 2},
            {"name": "12:00", "products": 3000, "profit": 1398, "errors": 5},
            {"name": "16:00", "products": 2000, "profit": 9800, "errors": 1},
            {"name": "20:00", "products": 2780, "profit": 3908, "errors": error_count_last_hour}, # Dato real actual
            {"name": "Now",  "products": 1890, "profit": 4800, "errors": 0},
        ]

        return Response({
            "total_products": total_products,
            "active_clusters": clusters,
            "vectorized_count": vectors,
            "system_status": "Healthy" if error_count_last_hour < 10 else "Degraded",
            "backlog_metrics": {
                "jsonl_files": pending_jsonl,
                "pending_vectors": pending_vectorization,
                "recent_errors": error_count_last_hour
            },
            "chart_data": chart_data
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
            
            # Map distance
            dist_map = {r[0]: r[1] for r in rows}
            
            for p in products:
                # Buscar cluster info manual o via modelo
                # Nota: Idealmente join con UniqueProductCluster, pero un producto puede ser miembro de un cluster
                # y no ser el representante.
                # Para Gold Mine, nos interesa el "Oportunidad de Cluster".
                
                member = ProductClusterMembership.objects.filter(product_id=p.product_id).first()
                cluster_info = member.cluster if member else None
                
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
            "vectorizer": "vectorizer.log"
        }
        
        for service, filename in files.items():
            fpath = log_dir / filename
            if fpath.exists():
                try:
                    # Leer ultimas 50 lineas de manera eficiente
                    with open(fpath, 'r', encoding='utf-8') as f:
                        # Leemos todo y tomamos el final (para logs gigantes usar seek)
                        lines = f.readlines()
                        last_lines = lines[-50:]
                        
                        for line in last_lines:
                            logs.append({
                                "service": service,
                                "message": line.strip(),
                                # Intento básico de extraer timestamp para ordenar si fuese necesario
                                "raw": line
                            })
                except Exception as e:
                    logs.append({"service": service, "message": f"Error reading logs: {e}"})
            else:
                 logs.append({"service": service, "message": "Log file not created yet."})
        
        return Response(logs)
