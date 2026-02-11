"""
Cuántos reportes exitosos se hicieron hoy y listado con fecha/hora.

Fuentes:
- OrderMovementReport: órdenes sin movimiento marcadas como resueltas (resolved_at = cuándo se reportó).
- OrderReport: reportes con status=reportado; reported_at = cuándo se generó el reporte (o updated_at si reported_at es null).

Usa zona horaria de Colombia (America/Bogota) para determinar "hoy".

Uso:
  python manage.py reportes_hoy
  python manage.py reportes_hoy --user 2
  python manage.py reportes_hoy --list   # listar cada uno con fecha/hora
  python manage.py reportes_hoy --date 2026-02-10
  python manage.py reportes_hoy --verify  # verificar inconsistencias entre tablas

Con Docker:
  docker compose exec backend python backend/manage.py reportes_hoy --list --verify
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, time as dt_time, timedelta
import pytz
from core.models import OrderMovementReport, OrderReport


class Command(BaseCommand):
    help = "Cuántos reportes exitosos hoy (y opcionalmente listado con fecha/hora)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list", action="store_true", help="Listar cada reporte con fecha y hora.",
        )
        parser.add_argument(
            "--user", type=int, help="Filtrar por user_id (OrderReport y órdenes de sus batches).",
        )
        parser.add_argument(
            "--date",
            type=str,
            help="Fecha a consultar (YYYY-MM-DD). Por defecto hoy en zona horaria Colombia.",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verificar inconsistencias entre OrderMovementReport y OrderReport.",
        )

    def _get_date_range_colombia(self, consulta_date):
        """
        Convierte una fecha a rango UTC usando zona horaria Colombia (America/Bogota).
        Retorna (start_utc, end_utc) para usar en filtros __gte y __lt.
        """
        colombia_tz = pytz.timezone('America/Bogota')
        utc_tz = pytz.UTC
        
        # Crear inicio del día en Colombia
        hoy_colombia_start = colombia_tz.localize(datetime.combine(consulta_date, dt_time.min))
        # Crear fin del día en Colombia
        hoy_colombia_end = colombia_tz.localize(datetime.combine(consulta_date, dt_time.max))
        
        # Convertir a UTC para comparar con BD (que guarda en UTC)
        hoy_start_utc = hoy_colombia_start.astimezone(utc_tz)
        hoy_end_utc = hoy_colombia_end.astimezone(utc_tz)
        # End es exclusivo, así que sumamos 1 segundo para incluir todo el día
        hoy_end_utc = hoy_end_utc + timedelta(seconds=1)
        
        return hoy_start_utc, hoy_end_utc

    def handle(self, *args, **options):
        listar = options.get("list", False)
        user_id = options.get("user")
        date_str = options.get("date")
        verify = options.get("verify", False)

        # Determinar fecha de consulta (en zona horaria Colombia)
        colombia_tz = pytz.timezone('America/Bogota')
        if date_str:
            try:
                consulta_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write(f"Fecha inválida: {date_str}. Use YYYY-MM-DD.")
                return
        else:
            # Hoy según zona horaria Colombia
            ahora_colombia = timezone.now().astimezone(colombia_tz)
            consulta_date = ahora_colombia.date()

        # Obtener rango UTC para filtros
        start_utc, end_utc = self._get_date_range_colombia(consulta_date)

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(f"  REPORTES EXITOSOS — {consulta_date} (zona horaria: Colombia)")
        self.stdout.write("=" * 70)

        # 1) OrderMovementReport (órdenes sin movimiento reportadas)
        qs_movement = OrderMovementReport.objects.filter(
            is_resolved=True,
            resolved_at__gte=start_utc,
            resolved_at__lt=end_utc,
        )
        if user_id:
            qs_movement = qs_movement.filter(batch__user_id=user_id)
        total_movement = qs_movement.count()
        self.stdout.write(f"  OrderMovementReport (resueltas hoy): {total_movement}")

        if listar and total_movement:
            self.stdout.write("  --- Listado (id, resolved_at, order/snapshot) ---")
            for r in qs_movement.select_related("snapshot", "batch").order_by("resolved_at"):
                order_id = r.snapshot.dropi_order_id if r.snapshot_id else "-"
                resolved_at_col = r.resolved_at.astimezone(colombia_tz) if r.resolved_at else None
                self.stdout.write(
                    f"    id={r.id}  resolved_at={resolved_at_col}  order={order_id}  user_batch={r.batch.user_id}"
                )

        # 2) OrderReport (status=reportado; usar reported_at si existe, si no updated_at)
        qs_order = OrderReport.objects.filter(status="reportado").filter(
            Q(reported_at__gte=start_utc, reported_at__lt=end_utc) |
            Q(reported_at__isnull=True, updated_at__gte=start_utc, updated_at__lt=end_utc)
        )
        if user_id:
            qs_order = qs_order.filter(user_id=user_id)
        total_order = qs_order.count()
        self.stdout.write(f"  OrderReport (reportado hoy, por reported_at o updated_at): {total_order}")

        if listar and total_order:
            self.stdout.write("  --- Listado (id, reported_at/updated_at, order_phone, user_id) ---")
            for r in qs_order.order_by("reported_at", "updated_at")[:200]:
                ts = r.reported_at or r.updated_at
                ts_col = ts.astimezone(colombia_tz) if ts else None
                self.stdout.write(
                    f"    id={r.id}  at={ts_col}  order_phone={r.order_phone}  user_id={r.user_id}"
                )
            if total_order > 200:
                self.stdout.write(f"    ... y {total_order - 200} más (use --user para acotar).")

        self.stdout.write("")
        self.stdout.write(f"  TOTAL (referencia: Movement + OrderReport puede haber solapado por misma orden): {total_movement} resueltas (Movement), {total_order} reportados (OrderReport).")
        
        # 3) Verificación de inconsistencias
        if verify or listar:
            self._verify_consistency(user_id, start_utc, end_utc, colombia_tz)
        
        self.stdout.write("")

    def _verify_consistency(self, user_id, start_utc, end_utc, colombia_tz):
        """Verifica inconsistencias entre OrderMovementReport y OrderReport."""
        self.stdout.write("")
        self.stdout.write("-" * 70)
        self.stdout.write("  VERIFICACIÓN DE CONSISTENCIA")
        self.stdout.write("-" * 70)
        
        # Obtener todas las órdenes resueltas en el rango
        qs_movement_all = OrderMovementReport.objects.filter(
            is_resolved=True,
            resolved_at__gte=start_utc,
            resolved_at__lt=end_utc,
        )
        if user_id:
            qs_movement_all = qs_movement_all.filter(batch__user_id=user_id)
        
        # Obtener todas las órdenes reportadas en el rango
        qs_order_all = OrderReport.objects.filter(status="reportado").filter(
            Q(reported_at__gte=start_utc, reported_at__lt=end_utc) |
            Q(reported_at__isnull=True, updated_at__gte=start_utc, updated_at__lt=end_utc)
        )
        if user_id:
            qs_order_all = qs_order_all.filter(user_id=user_id)
        
        # Verificar: OrderMovementReport resuelto pero sin OrderReport reportado
        inconsistencies_missing_orderreport = []
        for mov in qs_movement_all.select_related("snapshot", "batch"):
            phone = mov.snapshot.customer_phone if mov.snapshot_id else None
            if not phone:
                continue
            user_id_mov = mov.batch.user_id
            # Buscar OrderReport con mismo teléfono y usuario
            order_report = OrderReport.objects.filter(
                user_id=user_id_mov,
                order_phone=phone,
                status="reportado"
            ).first()
            if not order_report:
                inconsistencies_missing_orderreport.append({
                    'mov_id': mov.id,
                    'phone': phone,
                    'user_id': user_id_mov,
                    'resolved_at': mov.resolved_at,
                })
        
        # Verificar: OrderReport reportado pero sin OrderMovementReport resuelto
        inconsistencies_missing_movement = []
        for order in qs_order_all:
            # Buscar OrderMovementReport resuelto para este teléfono/usuario
            # Necesitamos buscar por snapshot que tenga ese customer_phone
            from core.models import RawOrderSnapshot
            snapshots = RawOrderSnapshot.objects.filter(
                customer_phone=order.order_phone
            ).values_list('id', flat=True)
            if snapshots:
                mov_resolved = OrderMovementReport.objects.filter(
                    snapshot_id__in=snapshots,
                    batch__user_id=order.user_id,
                    is_resolved=True
                ).first()
                if not mov_resolved:
                    inconsistencies_missing_movement.append({
                        'order_id': order.id,
                        'phone': order.order_phone,
                        'user_id': order.user_id,
                        'reported_at': order.reported_at or order.updated_at,
                    })
        
        # Verificar diferencias de tiempo significativas (>5 minutos)
        time_diffs = []
        for mov in qs_movement_all.select_related("snapshot", "batch"):
            phone = mov.snapshot.customer_phone if mov.snapshot_id else None
            if not phone:
                continue
            order_report = OrderReport.objects.filter(
                user_id=mov.batch.user_id,
                order_phone=phone,
                status="reportado"
            ).first()
            if order_report and mov.resolved_at and (order_report.reported_at or order_report.updated_at):
                ts_order = order_report.reported_at or order_report.updated_at
                # Asegurar ambos datetimes con timezone para restar (evitar naive vs aware)
                mov_ts = mov.resolved_at if timezone.is_aware(mov.resolved_at) else timezone.make_aware(mov.resolved_at, pytz.UTC)
                ord_ts = ts_order if timezone.is_aware(ts_order) else timezone.make_aware(ts_order, pytz.UTC)
                diff_seconds = abs((mov_ts - ord_ts).total_seconds())
                if diff_seconds > 300:  # >5 minutos
                    time_diffs.append({
                        'phone': phone,
                        'mov_resolved_at': mov.resolved_at,
                        'order_reported_at': ts_order,
                        'diff_minutes': diff_seconds / 60,
                    })
        
        # Mostrar resultados
        if inconsistencies_missing_orderreport:
            self.stdout.write(f"  ⚠️  {len(inconsistencies_missing_orderreport)} órdenes con OrderMovementReport resuelto pero SIN OrderReport reportado:")
            for inc in inconsistencies_missing_orderreport[:10]:
                resolved_col = inc['resolved_at'].astimezone(colombia_tz) if inc['resolved_at'] else None
                self.stdout.write(f"    mov_id={inc['mov_id']} phone={inc['phone']} user={inc['user_id']} resolved_at={resolved_col}")
            if len(inconsistencies_missing_orderreport) > 10:
                self.stdout.write(f"    ... y {len(inconsistencies_missing_orderreport) - 10} más.")
        else:
            self.stdout.write("  ✅ Todas las órdenes resueltas tienen OrderReport reportado.")
        
        if inconsistencies_missing_movement:
            self.stdout.write(f"  ⚠️  {len(inconsistencies_missing_movement)} órdenes con OrderReport reportado pero SIN OrderMovementReport resuelto:")
            for inc in inconsistencies_missing_movement[:10]:
                reported_col = inc['reported_at'].astimezone(colombia_tz) if inc['reported_at'] else None
                self.stdout.write(f"    order_id={inc['order_id']} phone={inc['phone']} user={inc['user_id']} reported_at={reported_col}")
            if len(inconsistencies_missing_movement) > 10:
                self.stdout.write(f"    ... y {len(inconsistencies_missing_movement) - 10} más.")
        else:
            self.stdout.write("  ✅ Todas las órdenes reportadas tienen OrderMovementReport resuelto.")
        
        if time_diffs:
            self.stdout.write(f"  ⚠️  {len(time_diffs)} órdenes con diferencia de tiempo >5 min entre resolved_at y reported_at:")
            for diff in time_diffs[:10]:
                mov_col = diff['mov_resolved_at'].astimezone(colombia_tz) if diff['mov_resolved_at'] else None
                order_col = diff['order_reported_at'].astimezone(colombia_tz) if diff['order_reported_at'] else None
                self.stdout.write(f"    phone={diff['phone']} diff={diff['diff_minutes']:.1f} min (mov={mov_col}, order={order_col})")
            if len(time_diffs) > 10:
                self.stdout.write(f"    ... y {len(time_diffs) - 10} más.")
        else:
            self.stdout.write("  ✅ Todas las órdenes tienen timestamps consistentes (<5 min diferencia).")
