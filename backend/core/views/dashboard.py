# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Avg, Count
from datetime import datetime, timedelta
from ..models import Product, ProductClusterMembership, Category
from ..permissions import IsAdminRole


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
        ).select_related('supplier').order_by('-profit_margin')[:50]  # Top 50 candidatos
        
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
                    "margin": p.profit_margin,  # Decimal
                    "competitors": competitors,
                    "supplier": p.supplier.store_name if p.supplier else "N/A",
                    "badge": "SOLITARIO" if competitors == 1 else "GOLD"
                })
                if len(tactical_feed) >= 5:
                    break  # Solo queremos los Top 5 para el UI

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
            product_count__gte=5  # Solo categorías relevantes
        ).order_by('-avg_margin')  # Priorizar las más rentables

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
            "market_radar": radar_data[:15]  # Top 15 categorías para no saturar el gráfico
        })
