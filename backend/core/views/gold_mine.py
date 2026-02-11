# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.db.models import Q, Count
from ..models import UniqueProductCluster, Product, ProductClusterMembership
from ..permissions import IsAdminRole


class GoldMineView(APIView):
    permission_classes = [IsAdminRole]
    
    def post(self, request):
        """Búsqueda Visual (Reverse Image Search)"""
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=400)
            
        uploaded_file = request.FILES['image']
        
        # 1. Vectorizar imagen llegada
        from ..ai_utils import get_image_embedding
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
                    "profit_margin": "N/A",  # Calc real
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
            if not p:
                continue
            
            margin_val = 0
            if p.suggested_price and p.sale_price:
                try:
                    margin_val = ((p.suggested_price - p.sale_price) / p.sale_price) * 100
                except:
                    pass
            
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
        
        if min_price:
            filters &= Q(average_price__gte=min_price)
        if max_price:
            filters &= Q(average_price__lte=max_price)
        if search_query:
            filters &= Q(representative_product__title__icontains=search_query)
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
