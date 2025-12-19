# -*- coding: utf-8 -*-
"""
Dashboard Views
Vistas relacionadas con el dashboard principal y estadísticas del sistema
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from ..models import Product, UniqueProductCluster, ProductEmbedding, Warehouse, Category
from datetime import datetime, timedelta


class DashboardStatsView(APIView):
    def get(self, request):
        """
        Centro de Comando Estratégico (V2).
        Retorna inteligencia real del mercado y oportunidades tácticas, 
        ya no solo estado del servidor.
        """
        # 1. Total productos únicos identificados (clusters)
        total_unique_products = UniqueProductCluster.objects.count()

        # 2. Distribución de competencia
        # Baja: 1-2 competitors
        # Media: 3-5 competitors
        # Alta: 6+ competitors
        low_comp = UniqueProductCluster.objects.filter(total_competitors__lte=2).count()
        med_comp = UniqueProductCluster.objects.filter(total_competitors__gte=3, total_competitors__lte=5).count()
        high_comp = UniqueProductCluster.objects.filter(total_competitors__gte=6).count()

        # 3. Oportunidades tácticas (GOLD MINE): Productos de baja competencia
        # Criterio: ≤ 3 competidores AND precio > $20,000
        gold_mine_opportunities = UniqueProductCluster.objects.filter(
            total_competitors__lte=3,
            average_price__gte=20000
        ).count()

        # 4. Top categorías por saturación (sobrepoblación)
        # Clustering permite medir saturación real
        top_saturated_categories = list(
            UniqueProductCluster.objects
                .filter(representative_product__productcategory__category__isnull=False)
                .values('representative_product__productcategory__category__name')
                .annotate(count=Count('cluster_id'))
                .order_by('-count')[:5]  # Top 5
        )

        # Renombrar clave para claridad
        for cat in top_saturated_categories:
            cat['category'] = cat.pop('representative_product__productcategory__category__name', 'Desconocida')

        # 5. Radar de Categorías - Distribución de productos únicos por categoría
        # Limitamos a Top 10 para el Chart.js (evitar sobrecarga visual)
        radar_data = list(
            UniqueProductCluster.objects
                .filter(representative_product__productcategory__category__isnull=False)
                .values('representative_product__productcategory__category__name')
                .annotate(count=Count('cluster_id'))
                .order_by('-count')[:10]
        )

        for item in radar_data:
            item['category'] = item.pop('representative_product__productcategory__category__name', 'Desconocida')

        # 6. Total categorías activas (con al menos un producto)
        total_categories = Category.objects.filter(
            productcategory__product__isnull=False
        ).distinct().count()

        # 7. Inteligencia de mercado: Precio promedio global
        avg_market_price = UniqueProductCluster.objects.aggregate(Avg('average_price'))['average_price__avg'] or 0

        # 8. Productos con embeddings visuales listos (AI ready)
        products_with_embeddings = ProductEmbedding.objects.filter(embedding_visual__isnull=False).count()

        # 9. Total productos en bruto (raw)
        total_raw_products = Product.objects.count()

        return Response({
            "total_unique_products": total_unique_products,
            "total_raw_products": total_raw_products,
            "competition_distribution": {
                "low": low_comp,
                "medium": med_comp,
                "high": high_comp
            },
            "gold_mine_opportunities": gold_mine_opportunities,
            "top_saturated_categories": top_saturated_categories,
            "radar_categories": radar_data,
            "total_categories": total_categories,
            "avg_market_price": round(avg_market_price, 2),
            "ai_ready_products": products_with_embeddings
        })
