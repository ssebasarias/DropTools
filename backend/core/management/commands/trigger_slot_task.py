"""
Comando para disparar manualmente la tarea process_slot_task (slot del reporter)
sin esperar a Celery Beat. Útil para pruebas.

Uso:
  # Hora actual redondeada a la hora en punto
  python manage.py trigger_slot_task

  # Hora específica (0-23) de hoy
  python manage.py trigger_slot_task --hour=10

  # Ejecutar síncrono en este proceso (sin Celery)
  python manage.py trigger_slot_task --hour=10 --sync

  # DEV: usar process_slot_task_dev (respeta capacidad por peso)
  python manage.py trigger_slot_task --hour=10 --dev

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
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Ejecutar la tarea en este proceso (sin encolar en Celery).",
        )
        parser.add_argument(
            "--dev",
            action="store_true",
            help="DEV: usar process_slot_task_dev (respeta capacidad por peso, encola siguiente al liberar).",
        )

    def handle(self, *args, **options):
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

        use_dev = options.get("dev", False)
        do_sync = options.get("sync", False)

        if use_dev:
            from core.tasks import process_slot_task_dev
            task = process_slot_task_dev
        else:
            from core.tasks import process_slot_task
            task = process_slot_task

        if do_sync:
            result = task.apply(args=[slot_time_iso])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ejecutado (sync): {task.__name__}(slot_time_iso={slot_time_iso!r}) -> {result}"
                )
            )
        else:
            result = task.delay(slot_time_iso)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Encolado: {task.__name__}(slot_time_iso={slot_time_iso!r}), task_id={result.id}"
                )
            )
            self.stdout.write(
                "Monitorear: docker compose logs -f celery_worker o Flower http://localhost:5555"
            )
