# -*- coding: utf-8 -*-
"""
Dashboard Service
Lógica de negocio para el Dashboard
"""
from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta
from ..models import (
    Product,
    UniqueProductCluster,
    ProductEmbedding,
    Category,
    ProductClusterMembership
)


class DashboardService:
    """
    Servicio para manejar la lógica del Dashboard
    """
    
    @staticmethod
    def get_tactical_opportunities(hours=48, limit=5):
        """
        Obtiene oportunidades tácticas (productos recientes de alto valor)
        
        Args:
            hours: Ventana de tiempo en horas
            limit: Número máximo de oportunidades
            
        Returns:
            list: Lista de oportunidades con detalles
        """
        cutoff_date = datetime.now() - timedelta(hours=hours)
        
        # Productos recientes con margen alto
        flash_ops = Product.objects.filter(
            created_at__gte=cutoff_date,
            url_image_s3__isnull=False,
            profit_margin__isnull=False
        ).select_related('supplier').order_by('-profit_margin')[:50]
        
        # Obtener membresías de clusters
        p_ids = [p.product_id for p in flash_ops]
        memberships = ProductClusterMembership.objects.filter(
            product_id__in=p_ids
        ).select_related('cluster')
        
        cluster_map = {m.product_id: m.cluster for m in memberships}
        
        tactical_feed = []
        for p in flash_ops:
            cluster = cluster_map.get(p.product_id)
            competitors = cluster.total_competitors if cluster else 1
            
            # Solo oportunidades de baja/media competencia
            if competitors <= 10:
                tactical_feed.append({
                    'id': p.product_id,
                    'title': p.title,
                    'image': p.url_image_s3,
                    'price': p.sale_price,
                    'margin': p.profit_margin,
                    'competitors': competitors,
                    'supplier': p.supplier.store_name if p.supplier else 'N/A',
                    'badge': 'SOLITARIO' if competitors == 1 else 'GOLD'
                })
                
                if len(tactical_feed) >= limit:
                    break
        
        return tactical_feed
    
    @staticmethod
    def get_market_radar(limit=15):
        """
        Obtiene radar de mercado por categorías
        
        Args:
            limit: Número máximo de categorías
            
        Returns:
            list: Radar de categorías con métricas
        """
        radar_qs = Category.objects.filter(
            productcategory__product__isnull=False
        ).annotate(
            product_count=Count('productcategory__product', distinct=True),
            avg_price=Avg('productcategory__product__sale_price'),
            avg_margin=Avg('productcategory__product__profit_margin'),
            avg_competitiveness=Avg(
                'productcategory__product__cluster_membership__cluster__total_competitors'
            )
        ).filter(
            product_count__gte=5  # Solo categorías relevantes
        ).order_by('-avg_margin')
        
        radar_data = []
        for cat in radar_qs[:limit]:
            radar_data.append({
                'category': cat.name,
                'volume': cat.product_count,
                'avg_price': round(cat.avg_price or 0, 2),
                'avg_margin': round(cat.avg_margin or 0, 2),
                'competitiveness': round(cat.avg_competitiveness or 1, 1)
            })
        
        return radar_data
    
    @staticmethod
    def get_general_stats():
        """
        Obtiene estadísticas generales del dashboard
        
        Returns:
            dict: Estadísticas generales
        """
        # Totales
        total_unique_products = UniqueProductCluster.objects.count()
        total_raw_products = Product.objects.count()
        
        # Distribución de competencia
        low_comp = UniqueProductCluster.objects.filter(total_competitors__lte=2).count()
        med_comp = UniqueProductCluster.objects.filter(
            total_competitors__gte=3, 
            total_competitors__lte=5
        ).count()
        high_comp = UniqueProductCluster.objects.filter(total_competitors__gte=6).count()
        
        # Oportunidades Gold Mine
        gold_mine_opportunities = UniqueProductCluster.objects.filter(
            total_competitors__lte=3,
            average_price__gte=20000
        ).count()
        
        # Categorías activas
        total_categories = Category.objects.filter(
            productcategory__product__isnull=False
        ).distinct().count()
        
        # Precio promedio
        avg_market_price = UniqueProductCluster.objects.aggregate(
            Avg('average_price')
        )['average_price__avg'] or 0
        
        # Productos con embeddings
        products_with_embeddings = ProductEmbedding.objects.filter(
            embedding_visual__isnull=False
        ).count()
        
        return {
            'total_unique_products': total_unique_products,
            'total_raw_products': total_raw_products,
            'competition_distribution': {
                'low': low_comp,
                'medium': med_comp,
                'high': high_comp
            },
            'gold_mine_opportunities': gold_mine_opportunities,
            'total_categories': total_categories,
            'avg_market_price': round(avg_market_price, 2),
            'ai_ready_products': products_with_embeddings
        }
