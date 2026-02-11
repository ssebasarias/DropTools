"""
Estado de lotes (ReporterRange) por run: cuántos hay, por estado, y qué worker tiene cada uno.

Uso:
  python manage.py reporter_ranges_status
  python manage.py reporter_ranges_status --run 21
  python manage.py reporter_ranges_status --last 10

Con Docker:
  docker compose exec backend python backend/manage.py reporter_ranges_status
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import ReporterRun, ReporterRunUser, ReporterRange


class Command(BaseCommand):
    help = "Muestra lotes (rangos) por run: total, por estado, y qué worker procesa cada uno."

    def add_arguments(self, parser):
        parser.add_argument("--run", type=int, help="Solo esta run_id.")
        parser.add_argument("--last", type=int, default=5, help="Últimas N runs (default 5).")

    def handle(self, *args, **options):
        run_id = options.get("run")
        last_n = options.get("last", 5)

        if run_id:
            runs = ReporterRun.objects.filter(id=run_id).order_by("-id")
        else:
            runs = ReporterRun.objects.order_by("-id")[:last_n]

        for run in runs:
            self._print_run(run)
        if not runs:
            self.stdout.write("No hay runs.")

    def _print_run(self, run):
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Run id={run.id}  slot={run.slot_id}  status={run.status}  scheduled={run.scheduled_at}")
        self.stdout.write("-" * 60)

        for ru in ReporterRunUser.objects.filter(run=run).order_by("id"):
            total_r = ReporterRange.objects.filter(run=run, user_id=ru.user_id).count()
            by_status = dict(
                ReporterRange.objects.filter(run=run, user_id=ru.user_id)
                .values("status")
                .annotate(c=Count("id"))
                .values_list("status", "c")
            )
            self.stdout.write(
                f"  user_id={ru.user_id}  total_ranges(ru)={ru.total_ranges}  ranges_completed={ru.ranges_completed}  "
                f"ReporterRange rows={total_r}  by_status={by_status}"
            )

            # Rangos en proceso o bloqueados: mostrar locked_by (worker/task)
            processing = ReporterRange.objects.filter(
                run=run, user_id=ru.user_id, status__in=(ReporterRange.STATUS_PROCESSING, ReporterRange.STATUS_LOCKED)
            ).order_by("range_start")
            for r in processing:
                self.stdout.write(f"    -> range [{r.range_start},{r.range_end}] status={r.status} locked_by={r.locked_by or '-'}")

        self.stdout.write("")
