"""
Servicio para crear rangos de órdenes a reportar (por usuario y run).
Usado después de download_compare_task para encolar report_range_task por cada rango.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_range_size():
    """Tamaño de cada rango (desde ReporterSlotConfig o settings)."""
    try:
        from core.models import ReporterSlotConfig
        config = ReporterSlotConfig.objects.first()
        if config:
            return config.range_size
    except Exception:
        pass
    from django.conf import settings
    return getattr(settings, 'REPORTER_RANGE_SIZE', 100)


def create_ranges_for_user(run_id, user_id, total_pending_orders):
    """
    Crea filas ReporterRange para el usuario en la run, dividiendo 1..total_pending_orders
    en bloques de range_size. Devuelve la lista de rangos creados (range_start, range_end).
    """
    from core.models import ReporterRun, ReporterRange
    size = get_range_size()
    if total_pending_orders <= 0:
        return []
    ranges_created = []
    start = 1
    while start <= total_pending_orders:
        end = min(start + size - 1, total_pending_orders)
        ReporterRange.objects.create(
            run_id=run_id,
            user_id=user_id,
            range_start=start,
            range_end=end,
            status=ReporterRange.STATUS_PENDING
        )
        ranges_created.append((start, end))
        start = end + 1
    logger.info(f"Created {len(ranges_created)} ranges for user={user_id} run={run_id} (total_orders={total_pending_orders})")
    return ranges_created
