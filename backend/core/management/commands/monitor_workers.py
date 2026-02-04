"""
Monitor en tiempo real de workers Reporter (slot, run_users, semáforo).
Vista simple estilo dashboard en terminal. Solo lectura a BD y Redis.

Uso:
  python manage.py monitor_workers

  # Intervalo en segundos (default 5)
  python manage.py monitor_workers --interval 10

Con Docker:
  docker compose exec backend python manage.py monitor_workers
"""
import time
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Monitor en tiempo real: runs, run_users, semáforo Selenium, proxy, rechazos por capacidad."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Segundos entre refrescos (default 5).",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Mostrar una vez y salir (sin loop).",
        )

    def handle(self, *args, **options):
        interval = max(1, options.get("interval", 5))
        once = options.get("once", False)
        try:
            while True:
                self._render()
                if once:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("\nMonitor detenido (Ctrl+C).")

    def _render(self):
        from core.models import ReporterRun, ReporterRunUser, ReporterReservation
        from core.reporter_bot.selenium_semaphore import current_count, get_max_slots, _get_redis
        from core.tasks import _run_capacity_aware_key

        now = timezone.now()
        since = now - timezone.timedelta(hours=24)
        runs = (
            ReporterRun.objects.filter(scheduled_at__gte=since, status=ReporterRun.STATUS_RUNNING)
            .select_related("slot")
            .order_by("-scheduled_at")[:10]
        )
        r = _get_redis()
        sem_current = current_count()
        sem_max = get_max_slots()

        lines = []
        lines.append("=" * 60)
        lines.append(f"  REPORTER MONITOR  {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append(f"  Semáforo Selenium: {sem_current} / {sem_max} ocupados")
        lines.append("-" * 60)

        for run in runs:
            cap_aware = bool(r.get(_run_capacity_aware_key(run.id)))
            cap_label = " [capacity-aware]" if cap_aware else ""
            lines.append(f"  Run {run.id}  slot {run.slot.hour:02d}:00  {run.scheduled_at}{cap_label}")
            run_users = list(
                ReporterRunUser.objects.filter(run=run).select_related("user").order_by("id")
            )
            if not run_users:
                lines.append("    (sin usuarios)")
                continue
            reservations = {
                res.user_id: res.calculated_weight
                for res in ReporterReservation.objects.filter(
                    slot=run.slot, user_id__in=[ru.user_id for ru in run_users]
                )
            }
            for ru in run_users:
                w = reservations.get(ru.user_id, 1)
                dc = ru.download_compare_status
                if dc == "running":
                    accion = "descargando/comparando"
                elif dc == "completed":
                    if ru.total_ranges and ru.ranges_completed < ru.total_ranges:
                        accion = f"reportando rangos ({ru.ranges_completed}/{ru.total_ranges})"
                    else:
                        accion = "completado"
                elif dc == "pending":
                    accion = "pendiente (capacidad)" if cap_aware else "pendiente"
                else:
                    accion = dc
                proxy_info = _proxy_for_user(ru.user_id)
                lines.append(
                    f"    user_id={ru.user_id}  peso={w}  {accion}  proxy={proxy_info or '-'}"
                )
            lines.append("")

        if not runs:
            lines.append("  No hay runs en ejecución en las últimas 24h.")
            lines.append("")

        lines.append("-" * 60)
        self.stdout.write("\n".join(lines))

    def clear_screen(self):
        import sys
        if sys.platform == "win32":
            import os
            os.system("cls")
        else:
            self.stdout.write("\033[2J\033[H")


def _proxy_for_user(user_id):
    """Devuelve host:port del proxy del usuario (DEV o BD). No loguea credenciales."""
    try:
        from django.conf import settings
        if getattr(settings, "IS_DEVELOPMENT", False):
            from core.services.proxy_dev_loader import get_dev_proxy_config
            cfg = get_dev_proxy_config(user_id)
            if cfg:
                return f"{cfg.get('host', '')}:{cfg.get('port', 8080)}"
        from core.services.proxy_allocator_service import get_proxy_config_for_user
        cfg = get_proxy_config_for_user(user_id)
        if cfg:
            return f"{cfg.get('host', '')}:{cfg.get('port', 8080)}"
    except Exception:
        pass
    return None
