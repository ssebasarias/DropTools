# -*- coding: utf-8 -*-
"""
Gold Mine Service
Lógica de negocio para la vista Gold Mine
"""
from django.db.models import Q
from ..models import UniqueProductCluster


class GoldMineService:
    """
    Servicio para manejar la lógica de búsqueda y filtrado de Gold Mine
    """
    
    @staticmethod
    def get_filtered_products(
        min_comp=0, 
        max_comp=50, 
        category=None,
        min_price=None, 
        max_price=None, 
        search_query='',
        limit=50,
        offset=0
    ):
        """
        Obtiene productos filtrados según criterios de Gold Mine
        
        Args:
            min_comp: Competidores mínimos
            max_comp: Competidores máximos
            category: ID de categoría (opcional)
            min_price: Precio mínimo (opcional)
            max_price: Precio máximo (opcional)
            search_query: Término de búsqueda (opcional)
            limit: Número máximo de resultados
            offset: Offset para paginación
            
        Returns:
            QuerySet de UniqueProductCluster filtrado
        """
        # Construir filtros base
        filters = Q(total_competitors__gte=min_comp) & Q(total_competitors__lte=max_comp)
        
        # Filtro de precio
        if min_price:
            filters &= Q(average_price__gte=min_price)
        if max_price:
            filters &= Q(average_price__lte=max_price)
        
        # Filtro de búsqueda textual
        if search_query:
            filters &= Q(representative_product__title__icontains=search_query)
        
        # Filtro de categoría
        if category and category != 'all':
            filters &= Q(representative_product__productcategory__category__id=category)
        
        # Ejecutar query optimizada
        queryset = UniqueProductCluster.objects.filter(filters)\
            .select_related('representative_product', 'representative_product__supplier')\
            .order_by('-average_price')
        
        # Aplicar paginación
        return queryset[offset:offset+limit]
    
    @staticmethod
    def get_distribution_stats():
        """
        Obtiene estadísticas de distribución de competidores
        
        Returns:
            dict: Estadísticas de distribución por rangos
        """
        from django.db.models import Count
        
        # Contar productos por rango de competidores
        stats = {
            'low': UniqueProductCluster.objects.filter(total_competitors__lte=2).count(),
            'medium': UniqueProductCluster.objects.filter(
                total_competitors__gte=3, 
                total_competitors__lte=5
            ).count(),
            'high': UniqueProductCluster.objects.filter(total_competitors__gte=6).count(),
        }
        
        return stats
    
    @staticmethod
    def search_by_visual_similarity(embedding_vector, limit=50):
        """
        Búsqueda por similaridad visual usando embeddings
        
        Args:
            embedding_vector: Vector de embedding de la imagen
            limit: Número de resultados
            
        Returns:
            list: Lista de productos similares con scores
        """
        from django.db import connection
        from ..models import ProductEmbedding, Product, ProductClusterMembership
        
        # Query usando pgvector para búsqueda por similaridad
        sql = """
            SELECT 
                pe.product_id, 
                (pe.embedding_visual <=> %s::vector) as distance
            FROM product_embeddings pe
            WHERE pe.embedding_visual IS NOT NULL
            ORDER BY distance ASC
            LIMIT %s
        """
        
        similar_products = []
        with connection.cursor() as cursor:
            cursor.execute(sql, (embedding_vector, limit))
            rows = cursor.fetchall()
            similar_pids = [r[0] for r in rows]
        
        if not similar_pids:
            return []
        
        # Obtener detalles de productos
        products = Product.objects.filter(product_id__in=similar_pids)\
            .select_related('supplier')
        
        # Mapear clusters
        memberships = ProductClusterMembership.objects.filter(
            product_id__in=similar_pids
        ).select_related('cluster')
        
        cluster_map = {m.product_id: m.cluster for m in memberships}
        dist_map = {r[0]: r[1] for r in rows}
        
        # Construir resultados
        for product in products:
            cluster_info = cluster_map.get(product.product_id)
            
            similar_products.append({
                'id': product.product_id,
                'title': product.title,
                'price': product.sale_price,
                'image': product.url_image_s3,
                'similarity': f"{int((1 - dist_map.get(product.product_id, 1))*100)}%",
                'competitors': cluster_info.total_competitors if cluster_info else 1,
                'supplier': product.supplier.store_name if product.supplier else 'Desconocido',
                'cluster_id': cluster_info.cluster_id if cluster_info else None
            })
        
        return similar_products
