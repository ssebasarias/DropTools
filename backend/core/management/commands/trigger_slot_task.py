"""
Comando para disparar manualmente la tarea process_slot_task (slot del reporter)
sin esperar a Celery Beat. Útil para pruebas.

Uso:
  # Hora actual redondeada a la hora en punto
  python manage.py trigger_slot_task

  # Hora específica (0-23) de hoy
  python manage.py trigger_slot_task --hour=10

Con Docker:
  docker compose exec backend python manage.py trigger_slot_task --hour=10
"""
from django.core.management.base import BaseCommand
from django.utils import timezone as tz


class Command(BaseCommand):
    help = "Encola process_slot_task para la hora indicada (o la hora actual)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hour",
            type=int,
            default=None,
            help="Hora del día (0-23). Si no se indica, usa la hora actual redondeada.",
        )

    def handle(self, *args, **options):
        from core.tasks import process_slot_task

        hour = options.get("hour")
        if hour is not None:
            if not 0 <= hour <= 23:
                self.stdout.write(self.style.ERROR("--hour debe estar entre 0 y 23."))
                return
            now = tz.now()
            slot_dt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_time_iso = slot_dt.isoformat()
        else:
            now = tz.now()
            slot_dt = now.replace(minute=0, second=0, microsecond=0)
            slot_time_iso = slot_dt.isoformat()

        result = process_slot_task.delay(slot_time_iso)
        self.stdout.write(
            self.style.SUCCESS(
                f"Encolado: process_slot_task(slot_time_iso={slot_time_iso!r}), task_id={result.id}"
            )
        )
        self.stdout.write(
            "Monitorear: docker compose logs -f celery_worker o Flower http://localhost:5555"
        )
