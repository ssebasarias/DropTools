# -*- coding: utf-8 -*-
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Case, When, F, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta, time as dt_time
import unicodedata
from ..models import (
    AnalyticsDailySnapshot,
    AnalyticsCarrierDaily,
    AnalyticsCarrierReports,
    ReportBatch,
    RawOrderSnapshot,
    OrderReport,
)
from ..permissions import MinSubscriptionTier


COLOMBIA_DEPARTMENT_ALIASES = {
    "amazonas": "Amazonas",
    "antioquia": "Antioquia",
    "arauca": "Arauca",
    "atlantico": "Atlántico",
    "bogota dc": "Bogotá D.C.",
    "bogota d c": "Bogotá D.C.",
    "bogota": "Bogotá D.C.",
    "bolivar": "Bolívar",
    "boyaca": "Boyacá",
    "caldas": "Caldas",
    "caqueta": "Caquetá",
    "casanare": "Casanare",
    "cauca": "Cauca",
    "cesar": "Cesar",
    "choco": "Chocó",
    "cordoba": "Córdoba",
    "cundinamarca": "Cundinamarca",
    "guainia": "Guainía",
    "guaviare": "Guaviare",
    "huila": "Huila",
    "la guajira": "La Guajira",
    "magdalena": "Magdalena",
    "meta": "Meta",
    "narino": "Nariño",
    "norte de santander": "Norte de Santander",
    "putumayo": "Putumayo",
    "quindio": "Quindío",
    "risaralda": "Risaralda",
    "san andres y providencia": "San Andrés y Providencia",
    "san andres y providencia y santa catalina": "San Andrés y Providencia",
    "santander": "Santander",
    "sucre": "Sucre",
    "tolima": "Tolima",
    "valle del cauca": "Valle del Cauca",
    "vaupes": "Vaupés",
    "vichada": "Vichada",
}


def _normalize_location_name(value):
    if not value or not isinstance(value, str):
        return ""
    cleaned = unicodedata.normalize("NFD", value.strip().lower())
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) != "Mn")
    return " ".join(cleaned.replace(".", " ").replace(",", " ").split())


def _canonical_colombia_department(raw_department):
    key = _normalize_location_name(raw_department)
    return COLOMBIA_DEPARTMENT_ALIASES.get(key)


class ClientDashboardAnalyticsView(APIView):
    """
    Analytics completo para el dashboard del cliente: KPIs, finanzas, transportadoras,
    productos, estados y todas las métricas analíticas derivadas de RawOrderSnapshot.
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("SILVER")]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        period = (request.query_params.get("period") or "month").strip().lower()
        if period not in ("day", "week", "fortnight", "month"):
            period = "month"
        batch_id_param = request.query_params.get("batch_id")
        use_cached = request.query_params.get("use_cached", "false").lower() == "true"

        now = timezone.now()
        now_local = timezone.localtime(now)
        target_date = now_local.date()
        current_tz = timezone.get_current_timezone()

        def _start_of_day(day):
            return timezone.make_aware(datetime.combine(day, dt_time.min), current_tz)
        day_start = _start_of_day(target_date)
        day_end = _start_of_day(target_date + timedelta(days=1))
        # Para carrier_reports (OrderReport) usamos últimos 30 días
        since = now - timedelta(days=30)

        period_label = {
            "day": "Hoy",
            "week": "Última semana",
            "fortnight": "Última quincena",
            "month": "Histórico (último año)",
        }.get(period, "Histórico (último año)")

        empty_response = {
            "kpis": {
                "total_orders": 0,
                "total_guides": 0,
                "products_sold": 0,
                "total_revenue": 0,
                "total_profit": 0,
                "confirmation_pct": 0.0,
                "cancellation_pct": 0.0,
            },
            "finances_general": {
                "total_value": 0,
                "projected_revenue": 0,
                "recovered_valuation": 0,
                "projected_profit_bps": 0,
            },
            "finances_real": {
                "delivered_revenue": 0,
                "net_profit_real": 0,
            },
            "performance_metrics": {
                "delivery_effectiveness_pct": 0.0,
                "global_returns_pct": 0.0,
                "annulation_pct": 0.0,
            },
            "status_breakdown": [],
            "by_region": [],
            "top_products": [],
            "by_carrier": [],
            "product_profitability": [],
            "carrier_reports": [],
            "last_updated": None,
            "period_used": period,
            "period_label": period_label,
            "data_message": "No hay datos disponibles para el período seleccionado.",
            "snapshot_sync_recommended": False,
        }

        try:
            # Intentar usar datos cacheados si están disponibles
            if use_cached and period == "day":
                snapshot = AnalyticsDailySnapshot.objects.filter(
                    user=user,
                    date=target_date
                ).first()
                if snapshot:
                    # Usar datos pre-calculados
                    return self._build_response_from_snapshot(snapshot, user, period, period_label)
            
            # Misma lógica que el comparer: batch más reciente SUCCESS (sin filtrar por fecha).
            # Comparer: ReportBatch.objects.filter(user=user, status='SUCCESS').order_by('-created_at')[:2]
            if batch_id_param:
                try:
                    batch_id = int(batch_id_param)
                except (TypeError, ValueError):
                    return Response(empty_response, status=status.HTTP_200_OK)
                batches = ReportBatch.objects.filter(
                    user=user, id=batch_id, status="SUCCESS"
                )[:1]
            else:
                # Usar ventanas de tiempo reales para que el período represente datos del rango esperado.
                if period == "day":
                    batches = ReportBatch.objects.filter(
                        user=user,
                        status="SUCCESS",
                        created_at__gte=day_start,
                        created_at__lt=day_end,
                    ).order_by("-created_at")
                else:
                    days_back = {"week": 7, "fortnight": 15, "month": 365}.get(period, 365)
                    cutoff = now - timedelta(days=days_back)
                    batches = ReportBatch.objects.filter(
                        user=user,
                        status="SUCCESS",
                        created_at__gte=cutoff,
                    ).order_by("-created_at")

            batch_ids = list(batches.values_list("id", flat=True))
            if not batch_ids:
                # Fallback: cualquier batch con al menos un snapshot (p. ej. status PROCESSING con datos)
                batches = (
                    ReportBatch.objects.filter(user=user)
                    .annotate(snap_count=Count("snapshots"))
                    .filter(snap_count__gt=0)
                    .order_by("-created_at")[:10]
                )
                batch_ids = list(batches.values_list("id", flat=True))
                if batch_ids:
                    period_label = period_label + " (últimos datos disponibles)"
            if not batch_ids:
                return Response(empty_response, status=status.HTTP_200_OK)

            last_batch = batches.first()
            last_updated = last_batch.created_at.isoformat() if last_batch else None

            snapshots = RawOrderSnapshot.objects.filter(batch_id__in=batch_ids)
            total_orders = snapshots.count()
            if total_orders == 0:
                # Si los lotes del período no tienen snapshots, usar el último lote con snapshots.
                fallback_batches = (
                    ReportBatch.objects.filter(user=user)
                    .annotate(snap_count=Count("snapshots"))
                    .filter(snap_count__gt=0)
                    .order_by("-created_at")[:10]
                )
                fallback_batch_ids = list(fallback_batches.values_list("id", flat=True))
                if fallback_batch_ids:
                    snapshots = RawOrderSnapshot.objects.filter(batch_id__in=fallback_batch_ids)
                    total_orders = snapshots.count()
                    if total_orders > 0:
                        batches = fallback_batches
                        batch_ids = fallback_batch_ids
                        period_label = period_label + " (últimos datos disponibles)"
                        last_batch = batches.first()
                        last_updated = last_batch.created_at.isoformat() if last_batch else last_updated

            if total_orders == 0:
                # Fallback de consistencia: si hay actividad en OrderReport para el período,
                # devolver KPIs básicos para no mostrar dashboard en cero injustificadamente.
                order_reports_qs = OrderReport.objects.filter(user=user)
                if period == "day":
                    order_reports_qs = order_reports_qs.filter(updated_at__gte=day_start, updated_at__lt=day_end)
                else:
                    reports_days_back = {"week": 7, "fortnight": 15, "month": 365}.get(period, 365)
                    reports_cutoff = now - timedelta(days=reports_days_back)
                    order_reports_qs = order_reports_qs.filter(updated_at__gte=reports_cutoff)

                fallback_total_reports = order_reports_qs.count()
                if fallback_total_reports > 0:
                    fallback_status_breakdown = []
                    for item in (
                        order_reports_qs.values("status")
                        .annotate(orders_count=Count("id"))
                        .order_by("-orders_count")
                    ):
                        fallback_status_breakdown.append({
                            "status": item.get("status") or "Sin estado",
                            "orders_count": item.get("orders_count") or 0,
                            "total_value": 0.0,
                        })

                    fallback_reported = order_reports_qs.filter(
                        Q(status="reportado") | Q(report_generated=True)
                    ).count()
                    fallback_confirmation_pct = round(
                        (fallback_reported / fallback_total_reports) * 100, 1
                    ) if fallback_total_reports else 0.0

                    last_report = order_reports_qs.order_by("-updated_at").first()
                    return Response({
                        **empty_response,
                        "kpis": {
                            **empty_response["kpis"],
                            "total_orders": int(fallback_total_reports),
                            "confirmation_pct": float(fallback_confirmation_pct),
                            "cancellation_pct": float(round(100 - fallback_confirmation_pct, 1)),
                        },
                        "status_breakdown": fallback_status_breakdown,
                        "last_updated": last_report.updated_at.isoformat() if last_report else last_updated,
                        "period_label": period_label + " (resumen desde reporter)",
                        "data_message": (
                            "Hay actividad de reporter, pero no hay snapshots de pedidos para calcular "
                            "finanzas/mapa. Ejecuta nuevamente descarga/comparer para poblar analytics detallado."
                        ),
                        "snapshot_sync_recommended": True,
                    }, status=status.HTTP_200_OK)

                return Response({
                    **empty_response,
                    "last_updated": last_updated,
                    "data_message": "No se encontraron reportes cargados para este usuario.",
                }, status=status.HTTP_200_OK)

            # KPIs Principales
            total_guides = snapshots.exclude(guide_number__isnull=True).exclude(guide_number='').count()
            agg_qty = snapshots.aggregate(s=Coalesce(Sum("quantity"), 0))
            agg_rev = snapshots.aggregate(s=Coalesce(Sum("total_amount"), 0))
            agg_profit = snapshots.aggregate(s=Coalesce(Sum("profit"), 0))
            products_sold = int(agg_qty.get("s") or 0)
            total_revenue = float(agg_rev.get("s") or 0)
            total_profit = float(agg_profit.get("s") or 0)

            # Desglose por Estado
            delivered_count = snapshots.filter(current_status__icontains="ENTREGAD").count()
            cancelled_count = snapshots.filter(current_status__icontains="CANCELAD").count()
            returns_count = snapshots.filter(current_status__icontains="DEVOLUCION").count()
            in_transit_count = snapshots.filter(current_status__in=['EN TRANSITO', 'EN CAMINO', 'EN RUTA']).count()
            in_warehouse_count = snapshots.filter(current_status__icontains="BODEGA").count()
            recollections_count = snapshots.filter(current_status__icontains="RECAUDO").count()

            confirmation_pct = round((total_orders - cancelled_count) / total_orders * 100, 1) if total_orders else 0.0
            cancellation_pct = round(cancelled_count / total_orders * 100, 1) if total_orders else 0.0

            # Finanzas Generales
            projected_revenue_agg = snapshots.exclude(current_status__icontains="CANCELAD").aggregate(s=Coalesce(Sum("total_amount"), 0))
            projected_revenue = float(projected_revenue_agg.get("s") or 0)
            
            recovered_valuation_agg = snapshots.filter(current_status__icontains="CANCELAD").aggregate(s=Coalesce(Sum("total_amount"), 0))
            recovered_valuation = float(recovered_valuation_agg.get("s") or 0)
            
            projected_profit_bps_agg = snapshots.filter(current_status__icontains="CANCELAD").aggregate(s=Coalesce(Sum("profit"), 0))
            projected_profit_bps = float(projected_profit_bps_agg.get("s") or 0)

            # Finanzas Reales (Entregados)
            delivered_snapshots = snapshots.filter(current_status__icontains="ENTREGAD")
            delivered_revenue_agg = delivered_snapshots.aggregate(s=Coalesce(Sum("total_amount"), 0))
            delivered_revenue = float(delivered_revenue_agg.get("s") or 0)
            
            net_profit_real_agg = delivered_snapshots.aggregate(s=Coalesce(Sum("profit"), 0))
            net_profit_real = float(net_profit_real_agg.get("s") or 0)

            # Métricas de Rendimiento
            delivery_effectiveness_pct = round(delivered_count / total_orders * 100, 1) if total_orders else 0.0
            global_returns_pct = round(returns_count / total_orders * 100, 1) if total_orders else 0.0
            annulation_pct = cancellation_pct

            # Desglose por Estado
            status_breakdown = []
            status_data = snapshots.values("current_status").annotate(
                orders_count=Count("id"),
                total_value=Coalesce(Sum("total_amount"), 0),
            ).order_by("-orders_count")
            
            for status_item in status_data:
                status_breakdown.append({
                    "status": status_item["current_status"] or "Sin estado",
                    "orders_count": status_item["orders_count"],
                    "total_value": float(status_item["total_value"] or 0),
                })

            # Por Región (solo departamentos de Colombia)
            by_region_dict = {}
            by_region_qs = (
                snapshots.exclude(department__isnull=True).exclude(department="")
                .values("department")
                .annotate(
                    orders=Count("id"),
                    revenue=Coalesce(Sum("total_amount"), 0),
                    avg_shipping_price=Coalesce(Avg("shipping_price"), 0),
                    freight_total=Coalesce(Sum("shipping_price"), 0),
                    city_count=Count("city", distinct=True),
                )
            )
            for x in by_region_qs:
                canonical_department = _canonical_colombia_department(x.get("department"))
                if not canonical_department:
                    continue
                data = by_region_dict.setdefault(
                    canonical_department,
                    {
                        "department": canonical_department,
                        "orders": 0,
                        "revenue": 0.0,
                        "avg_shipping_price": 0.0,
                        "freight_total": 0.0,
                        "city_count": 0,
                    },
                )
                try:
                    orders = int(x.get("orders") or 0)
                    revenue = float(x.get("revenue") or 0)
                    freight_total = float(x.get("freight_total") or 0)
                    city_count = int(x.get("city_count") or 0)
                    data["orders"] += orders
                    data["revenue"] += revenue
                    data["freight_total"] += freight_total
                    data["city_count"] = max(data["city_count"], city_count)
                except (TypeError, ValueError):
                    continue

            # Transportadora líder por región
            region_top_carrier = {}
            by_region_carrier_qs = (
                snapshots.exclude(department__isnull=True).exclude(department="")
                .exclude(carrier__isnull=True).exclude(carrier="")
                .values("department", "carrier")
                .annotate(
                    orders=Count("id"),
                    avg_shipping_price=Coalesce(Avg("shipping_price"), 0),
                )
                .order_by("-orders")
            )
            for row in by_region_carrier_qs:
                canonical_department = _canonical_colombia_department(row.get("department"))
                if not canonical_department:
                    continue
                existing = region_top_carrier.get(canonical_department)
                row_orders = int(row.get("orders") or 0)
                if existing is None or row_orders > existing["orders"]:
                    region_top_carrier[canonical_department] = {
                        "carrier": (row.get("carrier") or "").strip() or "Sin transportadora",
                        "orders": row_orders,
                        "avg_shipping_price": float(row.get("avg_shipping_price") or 0),
                    }

            by_region = []
            for department, region_data in by_region_dict.items():
                orders = region_data["orders"]
                avg_shipping_price = (region_data["freight_total"] / orders) if orders > 0 else 0.0
                leader = region_top_carrier.get(department)
                by_region.append({
                    "department": department,
                    "orders": orders,
                    "revenue": round(region_data["revenue"], 2),
                    "avg_shipping_price": round(avg_shipping_price, 2),
                    "freight_total": round(region_data["freight_total"], 2),
                    "city_count": region_data["city_count"],
                    "top_carrier": leader["carrier"] if leader else "Sin transportadora",
                    "top_carrier_orders": leader["orders"] if leader else 0,
                    "top_carrier_avg_shipping_price": round(leader["avg_shipping_price"], 2) if leader else 0.0,
                })
            by_region.sort(key=lambda item: item["orders"], reverse=True)

            # Top Productos (ventas)
            top_products_qs = (
                snapshots.values("product_name")
                .annotate(quantity=Coalesce(Sum("quantity"), 0), revenue=Coalesce(Sum("total_amount"), 0))
                .order_by("-quantity")[:10]
            )
            top_products = []
            for x in top_products_qs:
                try:
                    top_products.append({
                        "product_name": (x.get("product_name") or "Sin nombre").strip() or "Sin nombre",
                        "quantity": int(x.get("quantity") or 0),
                        "revenue": float(x.get("revenue") or 0),
                    })
                except (TypeError, ValueError):
                    continue

            # Rentabilidad por Producto (solo entregados)
            product_profitability_qs = (
                delivered_snapshots.values("product_name")
                .annotate(
                    sales_count=Count("id"),
                    profit_total=Coalesce(Sum("profit"), 0),
                    sale_value=Coalesce(Sum("total_amount"), 0),
                )
                .annotate(
                    margin_pct=Case(
                        When(sale_value__gt=0, then=F('profit_total') * 100.0 / F('sale_value')),
                        default=Value(0),
                        output_field=DecimalField(max_digits=5, decimal_places=2)
                    )
                )
                .order_by("-profit_total")[:20]
            )
            product_profitability = []
            for x in product_profitability_qs:
                try:
                    product_profitability.append({
                        "product_name": (x.get("product_name") or "Sin nombre").strip() or "Sin nombre",
                        "sales_count": x.get("sales_count") or 0,
                        "profit_total": float(x.get("profit_total") or 0),
                        "margin_pct": float(x.get("margin_pct") or 0),
                        "discount_pct": 0.0,  # No disponible en datos actuales
                        "sale_value": float(x.get("sale_value") or 0),
                        "gross_profit": float(x.get("profit_total") or 0),
                    })
                except (TypeError, ValueError):
                    continue

            # Efectividad por Transportadora (detallada)
            carriers = list(snapshots.exclude(carrier__isnull=True).exclude(carrier="").values_list("carrier", flat=True).distinct())
            by_carrier = []
            total_sales_all = delivered_snapshots.aggregate(s=Coalesce(Sum("total_amount"), 0))["s"] or 0
            
            for carrier in carriers:
                carrier_snap = snapshots.filter(carrier=carrier)
                approved_count = carrier_snap.count()
                delivered_c = carrier_snap.filter(current_status__icontains="ENTREGAD").count()
                returns_c = carrier_snap.filter(current_status__icontains="DEVOLUCION").count()
                cancelled_c = carrier_snap.filter(current_status__icontains="CANCELAD").count()
                recollections_c = carrier_snap.filter(current_status__icontains="RECAUDO").count()
                in_transit_c = carrier_snap.filter(current_status__in=['EN TRANSITO', 'EN CAMINO', 'EN RUTA']).count()
                times_count = in_transit_c
                times_pct = round(times_count / approved_count * 100, 1) if approved_count > 0 else 0
                
                sales_agg = carrier_snap.filter(current_status__icontains="ENTREGAD").aggregate(s=Coalesce(Sum("total_amount"), 0))
                sales_amount = float(sales_agg.get("s") or 0)
                sales_pct = round(sales_amount / total_sales_all * 100, 1) if total_sales_all > 0 else 0
                effectiveness_pct = round(delivered_c / approved_count * 100, 1) if approved_count > 0 else 0
                
                by_carrier.append({
                    "carrier": carrier,
                    "approved_count": approved_count,
                    "delivered_count": delivered_c,
                    "returns_count": returns_c,
                    "cancelled_count": cancelled_c,
                    "recollections_count": recollections_c,
                    "in_transit_count": in_transit_c,
                    "times_count": times_count,
                    "times_pct": times_pct,
                    "sales_amount": sales_amount,
                    "sales_pct": sales_pct,
                    "effectiveness_pct": effectiveness_pct,
                })
            by_carrier.sort(key=lambda x: -x["sales_amount"])

            # Transportadoras Más Reportadas
            carrier_reports = []
            # Obtener reportes de los últimos 30 días desde la fecha más antigua del período
            report_start_date = (now - timedelta(days=30)).date() if period != "day" else now.date()
            carrier_reports_data = AnalyticsCarrierReports.objects.filter(
                user=user,
                report_date__gte=report_start_date
            ).values("carrier").annotate(
                total_reports=Sum("reports_count")
            ).order_by("-total_reports")[:10]
            
            for cr_data in carrier_reports_data:
                carrier_reports.append({
                    "carrier": cr_data["carrier"],
                    "reports_count": cr_data["total_reports"] or 0,
                })
            
            # Si no hay datos en AnalyticsCarrierReports, calcular desde OrderReport
            if not carrier_reports:
                # Agrupar reportes por transportadora desde OrderReport
                reported_phones = OrderReport.objects.filter(
                    user=user,
                    status='reportado',
                    updated_at__gte=since
                ).values_list('order_phone', flat=True)
                
                if reported_phones:
                    carrier_reports_from_snapshots = RawOrderSnapshot.objects.filter(
                        batch__user=user,
                        customer_phone__in=reported_phones,
                        carrier__isnull=False
                    ).exclude(carrier='').values('carrier').annotate(
                        reports_count=Count('id')
                    ).order_by('-reports_count')[:10]
                    
                    for cr_item in carrier_reports_from_snapshots:
                        carrier_reports.append({
                            "carrier": cr_item["carrier"],
                            "reports_count": cr_item["reports_count"] or 0,
                        })

            return Response({
                "kpis": {
                    "total_orders": int(total_orders),
                    "total_guides": int(total_guides),
                    "products_sold": int(products_sold),
                    "total_revenue": float(total_revenue),
                    "total_profit": float(total_profit),
                    "confirmation_pct": float(confirmation_pct),
                    "cancellation_pct": float(cancellation_pct),
                },
                "finances_general": {
                    "total_value": float(total_revenue),
                    "projected_revenue": float(projected_revenue),
                    "recovered_valuation": float(recovered_valuation),
                    "projected_profit_bps": float(projected_profit_bps),
                },
                "finances_real": {
                    "delivered_revenue": float(delivered_revenue),
                    "net_profit_real": float(net_profit_real),
                },
                "performance_metrics": {
                    "delivery_effectiveness_pct": float(delivery_effectiveness_pct),
                    "global_returns_pct": float(global_returns_pct),
                    "annulation_pct": float(annulation_pct),
                },
                "status_breakdown": status_breakdown,
                "by_region": by_region,
                "top_products": top_products,
                "by_carrier": by_carrier,
                "product_profitability": product_profitability,
                "carrier_reports": carrier_reports,
                "last_updated": last_updated,
                "period_used": period,
                "period_label": period_label,
                "snapshot_sync_recommended": False,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import logging
            logging.exception("ClientDashboardAnalyticsView error: %s", e)
            return Response(empty_response, status=status.HTTP_200_OK)
    
    def _build_response_from_snapshot(self, snapshot, user, period, period_label):
        """Construye respuesta desde snapshot pre-calculado."""
        # Implementación simplificada usando datos del snapshot
        # Por ahora, calcular en tiempo real es más completo
        return None


class AnalyticsHistoricalView(APIView):
    """
    Endpoint para obtener datos históricos agregados.
    Retorna series temporales de métricas para análisis temporal.
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("SILVER")]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        granularity = request.query_params.get("granularity", "day").strip().lower()
        
        if granularity not in ("day", "week", "month"):
            granularity = "day"

        # Fechas por defecto: último mes
        if not start_date_str:
            start_date = (timezone.now() - timedelta(days=30)).date()
        else:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not end_date_str:
            end_date = timezone.now().date()
        else:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            snapshots = AnalyticsDailySnapshot.objects.filter(
                user=user,
                date__gte=start_date,
                date__lte=end_date
            ).order_by("date")

            data = []
            for snapshot in snapshots:
                data.append({
                    "date": snapshot.date.isoformat(),
                    "total_orders": snapshot.total_orders,
                    "total_guides": snapshot.total_guides,
                    "products_sold": snapshot.products_sold,
                    "total_revenue": float(snapshot.total_revenue),
                    "total_profit": float(snapshot.total_profit),
                    "delivered_count": snapshot.delivered_count,
                    "returns_count": snapshot.returns_count,
                    "cancelled_count": snapshot.cancelled_count,
                    "delivery_effectiveness_pct": float(snapshot.delivery_effectiveness_pct),
                    "global_returns_pct": float(snapshot.global_returns_pct),
                    "net_profit_real": float(snapshot.net_profit_real),
                })

            return Response({
                "data": data,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "granularity": granularity,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import logging
            logging.exception("AnalyticsHistoricalView error: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyticsCarrierComparisonView(APIView):
    """
    Endpoint para comparativa de transportadoras.
    Retorna datos para gráfico de barras comparativo.
    """
    permission_classes = [IsAuthenticated, MinSubscriptionTier("SILVER")]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

        period = (request.query_params.get("period") or "month").strip().lower()
        if period not in ("day", "week", "month"):
            period = "month"

        now = timezone.now()
        if period == "day":
            target_date = now.date()
        elif period == "week":
            target_date = (now - timedelta(days=7)).date()
        else:
            target_date = (now - timedelta(days=30)).date()

        try:
            # Obtener datos de transportadoras del período
            carrier_data = AnalyticsCarrierDaily.objects.filter(
                user=user,
                date__gte=target_date
            ).values("carrier").annotate(
                total_approved=Sum("approved_count"),
                total_delivered=Sum("delivered_count"),
                total_returns=Sum("returns_count"),
                total_cancelled=Sum("cancelled_count"),
                total_sales=Sum("sales_amount"),
                avg_effectiveness=Avg("effectiveness_pct"),
            ).order_by("-total_sales")

            comparison_data = []
            for carrier_item in carrier_data:
                comparison_data.append({
                    "carrier": carrier_item["carrier"],
                    "approved": carrier_item["total_approved"] or 0,
                    "delivered": carrier_item["total_delivered"] or 0,
                    "returns": carrier_item["total_returns"] or 0,
                    "cancelled": carrier_item["total_cancelled"] or 0,
                    "sales_amount": float(carrier_item["total_sales"] or 0),
                    "effectiveness_pct": float(carrier_item["avg_effectiveness"] or 0),
                })

            return Response({
                "carriers": comparison_data,
                "period": period,
                "period_label": {
                    "day": "Hoy",
                    "week": "Última semana",
                    "month": "Último mes",
                }.get(period, "Último mes"),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import logging
            logging.exception("AnalyticsCarrierComparisonView error: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
