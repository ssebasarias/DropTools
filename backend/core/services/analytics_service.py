# -*- coding: utf-8 -*-
"""
Analytics Service
Servicio para calcular y almacenar métricas analíticas históricas.
Todos los métodos filtran por usuario para asegurar seguridad de datos.
"""
import logging
from datetime import date, timedelta, datetime
from django.db.models import (
    Count, Sum, Q, F, Avg, Max, Min,
    Case, When, Value, IntegerField, DecimalField
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from core.models import (
    RawOrderSnapshot, ReportBatch, OrderReport,
    AnalyticsDailySnapshot, AnalyticsCarrierDaily,
    AnalyticsProductDaily, AnalyticsCarrierReports,
    AnalyticsStatusBreakdown
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Servicio para calcular métricas analíticas y almacenarlas históricamente.
    """
    
    def __init__(self, user):
        """
        Inicializa el servicio con un usuario específico.
        
        Args:
            user: Instancia de User
        """
        self.user = user
        if not user or not user.is_authenticated:
            raise ValueError("Usuario debe estar autenticado")
    
    def calculate_daily_snapshot(self, target_date=None):
        """
        Calcula y guarda snapshot diario de métricas principales.
        
        Args:
            target_date: Fecha objetivo (default: ayer)
        
        Returns:
            AnalyticsDailySnapshot: Instancia creada o actualizada
        """
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        # Obtener batches del usuario para la fecha objetivo
        date_start = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        date_end = date_start + timedelta(days=1)
        
        batches = ReportBatch.objects.filter(
            user=self.user,
            status='SUCCESS',
            created_at__gte=date_start,
            created_at__lt=date_end
        )
        
        batch_ids = list(batches.values_list('id', flat=True))
        if not batch_ids:
            logger.warning(f"No hay batches para usuario {self.user.id} en fecha {target_date}")
            return None
        
        snapshots = RawOrderSnapshot.objects.filter(batch_id__in=batch_ids)
        
        # KPIs Principales
        total_orders = snapshots.count()
        total_guides = snapshots.exclude(
            guide_number__isnull=True
        ).exclude(guide_number='').count()
        
        products_sold_agg = snapshots.aggregate(total=Coalesce(Sum('quantity'), 0))
        products_sold = int(products_sold_agg['total'] or 0)
        
        revenue_agg = snapshots.aggregate(total=Coalesce(Sum('total_amount'), 0))
        total_revenue = revenue_agg['total'] or 0
        
        profit_agg = snapshots.aggregate(total=Coalesce(Sum('profit'), 0))
        total_profit = profit_agg['total'] or 0
        
        # Desglose por Estado
        delivered_count = snapshots.filter(
            current_status__icontains='ENTREGAD'
        ).count()
        
        returns_count = snapshots.filter(
            current_status__icontains='DEVOLUCION'
        ).count()
        
        cancelled_count = snapshots.filter(
            current_status__icontains='CANCELAD'
        ).count()
        
        in_transit_count = snapshots.filter(
            current_status__in=['EN TRANSITO', 'EN CAMINO', 'EN RUTA']
        ).count()
        
        in_warehouse_count = snapshots.filter(
            current_status__icontains='BODEGA'
        ).count()
        
        recollections_count = snapshots.filter(
            current_status__icontains='RECAUDO'
        ).count()
        
        # Porcentajes
        confirmation_pct = round(
            ((total_orders - cancelled_count) / total_orders * 100) if total_orders > 0 else 0,
            2
        )
        cancellation_pct = round(
            (cancelled_count / total_orders * 100) if total_orders > 0 else 0,
            2
        )
        
        # Finanzas Generales
        # Proyectado: solo órdenes confirmadas (sin canceladas)
        projected_revenue_agg = snapshots.exclude(
            current_status__icontains='CANCELAD'
        ).aggregate(total=Coalesce(Sum('total_amount'), 0))
        projected_revenue = projected_revenue_agg['total'] or 0
        
        # Valoración recuperada de cancelados
        recovered_valuation_agg = snapshots.filter(
            current_status__icontains='CANCELAD'
        ).aggregate(total=Coalesce(Sum('total_amount'), 0))
        recovered_valuation = recovered_valuation_agg['total'] or 0
        
        # Utilidad proyectada de cancelados
        projected_profit_bps_agg = snapshots.filter(
            current_status__icontains='CANCELAD'
        ).aggregate(total=Coalesce(Sum('profit'), 0))
        projected_profit_bps = projected_profit_bps_agg['total'] or 0
        
        # Ganancia neta real (solo entregados)
        net_profit_real_agg = snapshots.filter(
            current_status__icontains='ENTREGAD'
        ).aggregate(total=Coalesce(Sum('profit'), 0))
        net_profit_real = net_profit_real_agg['total'] or 0
        
        # Métricas de Rendimiento
        delivery_effectiveness_pct = round(
            (delivered_count / total_orders * 100) if total_orders > 0 else 0,
            2
        )
        
        global_returns_pct = round(
            (returns_count / total_orders * 100) if total_orders > 0 else 0,
            2
        )
        
        annulation_pct = cancellation_pct  # Mismo valor
        
        # Crear o actualizar snapshot
        snapshot, created = AnalyticsDailySnapshot.objects.update_or_create(
            user=self.user,
            date=target_date,
            defaults={
                'total_orders': total_orders,
                'total_guides': total_guides,
                'products_sold': products_sold,
                'total_revenue': float(total_revenue),
                'total_profit': float(total_profit),
                'confirmation_pct': confirmation_pct,
                'cancellation_pct': cancellation_pct,
                'delivered_count': delivered_count,
                'returns_count': returns_count,
                'cancelled_count': cancelled_count,
                'in_transit_count': in_transit_count,
                'in_warehouse_count': in_warehouse_count,
                'recollections_count': recollections_count,
                'projected_revenue': float(projected_revenue),
                'recovered_valuation': float(recovered_valuation),
                'projected_profit_bps': float(projected_profit_bps),
                'net_profit_real': float(net_profit_real),
                'delivery_effectiveness_pct': delivery_effectiveness_pct,
                'global_returns_pct': global_returns_pct,
                'annulation_pct': annulation_pct,
            }
        )
        
        logger.info(
            f"Snapshot diario {'creado' if created else 'actualizado'} para usuario {self.user.id} "
            f"fecha {target_date}: {total_orders} órdenes"
        )
        
        return snapshot
    
    def calculate_carrier_metrics(self, target_date=None):
        """
        Calcula métricas por transportadora para una fecha específica.
        
        Args:
            target_date: Fecha objetivo (default: ayer)
        
        Returns:
            list: Lista de AnalyticsCarrierDaily creados/actualizados
        """
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        date_start = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        date_end = date_start + timedelta(days=1)
        
        batches = ReportBatch.objects.filter(
            user=self.user,
            status='SUCCESS',
            created_at__gte=date_start,
            created_at__lt=date_end
        )
        
        batch_ids = list(batches.values_list('id', flat=True))
        if not batch_ids:
            return []
        
        snapshots = RawOrderSnapshot.objects.filter(batch_id__in=batch_ids)
        
        # Obtener todas las transportadoras únicas
        carriers = snapshots.exclude(
            carrier__isnull=True
        ).exclude(carrier='').values_list('carrier', flat=True).distinct()
        
        results = []
        total_sales = snapshots.filter(
            current_status__icontains='ENTREGAD'
        ).aggregate(total=Coalesce(Sum('total_amount'), 0))['total'] or 0
        
        for carrier in carriers:
            carrier_snapshots = snapshots.filter(carrier=carrier)
            
            approved_count = carrier_snapshots.count()
            delivered_count = carrier_snapshots.filter(
                current_status__icontains='ENTREGAD'
            ).count()
            returns_count = carrier_snapshots.filter(
                current_status__icontains='DEVOLUCION'
            ).count()
            cancelled_count = carrier_snapshots.filter(
                current_status__icontains='CANCELAD'
            ).count()
            recollections_count = carrier_snapshots.filter(
                current_status__icontains='RECAUDO'
            ).count()
            in_transit_count = carrier_snapshots.filter(
                current_status__in=['EN TRANSITO', 'EN CAMINO', 'EN RUTA']
            ).count()
            
            # Tiempos (retrasos) - órdenes que están en tránsito más de X días
            # Por ahora, contamos las que están en tránsito
            times_count = in_transit_count
            times_pct = round(
                (times_count / approved_count * 100) if approved_count > 0 else 0,
                2
            )
            
            # Ventas de esta transportadora
            sales_agg = carrier_snapshots.filter(
                current_status__icontains='ENTREGAD'
            ).aggregate(total=Coalesce(Sum('total_amount'), 0))
            sales_amount = sales_agg['total'] or 0
            
            sales_pct = round(
                (float(sales_amount) / float(total_sales) * 100) if total_sales > 0 else 0,
                2
            )
            
            effectiveness_pct = round(
                (delivered_count / approved_count * 100) if approved_count > 0 else 0,
                2
            )
            
            carrier_metric, created = AnalyticsCarrierDaily.objects.update_or_create(
                user=self.user,
                date=target_date,
                carrier=carrier,
                defaults={
                    'approved_count': approved_count,
                    'delivered_count': delivered_count,
                    'returns_count': returns_count,
                    'cancelled_count': cancelled_count,
                    'recollections_count': recollections_count,
                    'in_transit_count': in_transit_count,
                    'times_count': times_count,
                    'times_pct': times_pct,
                    'sales_amount': float(sales_amount),
                    'sales_pct': sales_pct,
                    'effectiveness_pct': effectiveness_pct,
                }
            )
            
            results.append(carrier_metric)
        
        logger.info(
            f"Métricas de transportadoras calculadas para usuario {self.user.id} "
            f"fecha {target_date}: {len(results)} transportadoras"
        )
        
        return results
    
    def calculate_product_metrics(self, target_date=None):
        """
        Calcula métricas de rentabilidad por producto para una fecha específica.
        
        Args:
            target_date: Fecha objetivo (default: ayer)
        
        Returns:
            list: Lista de AnalyticsProductDaily creados/actualizados
        """
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        date_start = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        date_end = date_start + timedelta(days=1)
        
        batches = ReportBatch.objects.filter(
            user=self.user,
            status='SUCCESS',
            created_at__gte=date_start,
            created_at__lt=date_end
        )
        
        batch_ids = list(batches.values_list('id', flat=True))
        if not batch_ids:
            return []
        
        # Solo productos entregados para métricas de rentabilidad
        snapshots = RawOrderSnapshot.objects.filter(
            batch_id__in=batch_ids,
            current_status__icontains='ENTREGAD'
        )
        
        # Agrupar por producto
        products_data = snapshots.values('product_name').annotate(
            sales_count=Count('id'),
            profit_total=Coalesce(Sum('profit'), 0),
            sale_value=Coalesce(Sum('total_amount'), 0),
            quantity_total=Coalesce(Sum('quantity'), 0),
        )
        
        results = []
        for product_data in products_data:
            product_name = product_data['product_name'] or 'Sin nombre'
            sales_count = product_data['sales_count']
            profit_total = product_data['profit_total'] or 0
            sale_value = product_data['sale_value'] or 0
            quantity_total = product_data['quantity_total'] or 0
            
            # Calcular porcentajes
            margin_pct = round(
                (float(profit_total) / float(sale_value) * 100) if sale_value > 0 else 0,
                2
            )
            
            # % Descuento (necesitaríamos precio original, por ahora 0)
            discount_pct = 0.0
            
            gross_profit = float(profit_total)
            
            product_metric, created = AnalyticsProductDaily.objects.update_or_create(
                user=self.user,
                date=target_date,
                product_name=product_name,
                defaults={
                    'sales_count': sales_count,
                    'profit_total': float(profit_total),
                    'margin_pct': margin_pct,
                    'discount_pct': discount_pct,
                    'sale_value': float(sale_value),
                    'gross_profit': gross_profit,
                }
            )
            
            results.append(product_metric)
        
        logger.info(
            f"Métricas de productos calculadas para usuario {self.user.id} "
            f"fecha {target_date}: {len(results)} productos"
        )
        
        return results
    
    def calculate_carrier_reports(self, target_date=None):
        """
        Calcula conteo de reportes generados por transportadora.
        
        Args:
            target_date: Fecha objetivo (default: ayer)
        
        Returns:
            list: Lista de AnalyticsCarrierReports creados/actualizados
        """
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        date_start = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        date_end = date_start + timedelta(days=1)
        
        # Obtener reportes del usuario en la fecha
        reports = OrderReport.objects.filter(
            user=self.user,
            status='reportado',
            updated_at__gte=date_start,
            updated_at__lt=date_end
        )
        
        # Relacionar reportes con transportadoras a través de RawOrderSnapshot
        # Necesitamos hacer JOIN por customer_phone
        results = []
        
        # Agrupar por transportadora desde los snapshots relacionados
        for report in reports:
            # Buscar snapshot relacionado por teléfono
            snapshot = RawOrderSnapshot.objects.filter(
                batch__user=self.user,
                customer_phone=report.order_phone
            ).first()
            
            if snapshot and snapshot.carrier:
                carrier = snapshot.carrier
                
                # Contar reportes por transportadora en esta fecha
                carrier_reports_count = OrderReport.objects.filter(
                    user=self.user,
                    status='reportado',
                    updated_at__gte=date_start,
                    updated_at__lt=date_end
                ).filter(
                    order_phone__in=RawOrderSnapshot.objects.filter(
                        batch__user=self.user,
                        carrier=carrier
                    ).values_list('customer_phone', flat=True)
                ).count()
                
                last_reported = OrderReport.objects.filter(
                    user=self.user,
                    status='reportado',
                    order_phone__in=RawOrderSnapshot.objects.filter(
                        batch__user=self.user,
                        carrier=carrier
                    ).values_list('customer_phone', flat=True)
                ).order_by('-updated_at').first()
                
                carrier_report, created = AnalyticsCarrierReports.objects.update_or_create(
                    user=self.user,
                    carrier=carrier,
                    report_date=target_date,
                    defaults={
                        'reports_count': carrier_reports_count,
                        'last_reported_at': last_reported.updated_at if last_reported else None,
                    }
                )
                
                if carrier_report not in results:
                    results.append(carrier_report)
        
        logger.info(
            f"Reportes por transportadora calculados para usuario {self.user.id} "
            f"fecha {target_date}: {len(results)} transportadoras"
        )
        
        return results
    
    def calculate_status_breakdown(self, target_date=None):
        """
        Calcula desglose de órdenes por estado.
        
        Args:
            target_date: Fecha objetivo (default: ayer)
        
        Returns:
            list: Lista de AnalyticsStatusBreakdown creados/actualizados
        """
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        date_start = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time())
        )
        date_end = date_start + timedelta(days=1)
        
        batches = ReportBatch.objects.filter(
            user=self.user,
            status='SUCCESS',
            created_at__gte=date_start,
            created_at__lt=date_end
        )
        
        batch_ids = list(batches.values_list('id', flat=True))
        if not batch_ids:
            return []
        
        snapshots = RawOrderSnapshot.objects.filter(batch_id__in=batch_ids)
        
        # Agrupar por estado
        status_data = snapshots.values('current_status').annotate(
            orders_count=Count('id'),
            total_value=Coalesce(Sum('total_amount'), 0),
        )
        
        results = []
        for status_item in status_data:
            status = status_item['current_status'] or 'Sin estado'
            orders_count = status_item['orders_count']
            total_value = status_item['total_value'] or 0
            
            status_breakdown, created = AnalyticsStatusBreakdown.objects.update_or_create(
                user=self.user,
                date=target_date,
                status=status,
                defaults={
                    'orders_count': orders_count,
                    'total_value': float(total_value),
                }
            )
            
            results.append(status_breakdown)
        
        logger.info(
            f"Desglose por estado calculado para usuario {self.user.id} "
            f"fecha {target_date}: {len(results)} estados"
        )
        
        return results
    
    def get_historical_data(self, start_date, end_date, granularity='day'):
        """
        Obtiene datos históricos agregados.
        
        Args:
            start_date: Fecha inicio
            end_date: Fecha fin
            granularity: 'day', 'week', 'month'
        
        Returns:
            dict: Datos históricos organizados
        """
        snapshots = AnalyticsDailySnapshot.objects.filter(
            user=self.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        if granularity == 'week':
            # Agrupar por semana
            from django.db.models.functions import TruncWeek
            snapshots = snapshots.annotate(week=TruncWeek('date'))
            # Implementar agrupación por semana
        elif granularity == 'month':
            # Agrupar por mes
            from django.db.models.functions import TruncMonth
            snapshots = snapshots.annotate(month=TruncMonth('date'))
            # Implementar agrupación por mes
        
        return {
            'snapshots': list(snapshots.values()),
            'start_date': start_date,
            'end_date': end_date,
            'granularity': granularity,
        }
    
    def calculate_all_metrics(self, target_date=None):
        """
        Calcula todas las métricas para una fecha específica.
        
        Args:
            target_date: Fecha objetivo (default: ayer)
        
        Returns:
            dict: Resultados de todos los cálculos
        """
        if target_date is None:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        results = {
            'date': target_date,
            'snapshot': self.calculate_daily_snapshot(target_date),
            'carriers': self.calculate_carrier_metrics(target_date),
            'products': self.calculate_product_metrics(target_date),
            'carrier_reports': self.calculate_carrier_reports(target_date),
            'status_breakdown': self.calculate_status_breakdown(target_date),
        }
        
        logger.info(
            f"Todas las métricas calculadas para usuario {self.user.id} fecha {target_date}"
        )
        
        return results
