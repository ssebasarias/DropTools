"""
Comando para crear o actualizar reservas del reporter en un slot (útil para testeo).
Asigna los user_id indicados al slot con la hora dada; si ya tienen reserva, la actualiza.

Uso:
  python manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10

Con Docker:
  docker compose exec backend python backend/manage.py ensure_reporter_reservations --user-ids=2,3,4 --hour=10
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import ReporterHourSlot, ReporterReservation

User = get_user_model()


class Command(BaseCommand):
    help = "Crea o actualiza reservas del reporter para user_ids en el slot de la hora indicada."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-ids",
            type=str,
            required=True,
            help="IDs de usuarios separados por coma (ej. 2,3,4).",
        )
        parser.add_argument(
            "--hour",
            type=int,
            required=True,
            help="Hora del slot (0-23).",
        )
        parser.add_argument(
            "--monthly-orders",
            type=int,
            default=500,
            help="monthly_orders_estimate para cada reserva (default 500).",
        )

    def handle(self, *args, **options):
        user_ids = [int(x.strip()) for x in options["user_ids"].split(",") if x.strip()]
        hour = options["hour"]
        monthly_orders = options.get("monthly_orders", 500)

        if not 0 <= hour <= 23:
            self.stdout.write(self.style.ERROR("--hour debe estar entre 0 y 23."))
            return

        slot = ReporterHourSlot.objects.filter(hour=hour).first()
        if not slot:
            self.stdout.write(self.style.ERROR(f"No existe ReporterHourSlot para hour={hour}."))
            return

        for uid in user_ids:
            user = User.objects.filter(id=uid).first()
            if not user:
                self.stdout.write(self.style.WARNING(f"Usuario {uid} no existe; omitido."))
                continue
            res, created = ReporterReservation.objects.update_or_create(
                user=user,
                defaults={"slot": slot, "monthly_orders_estimate": monthly_orders},
            )
            action = "Creada" if created else "Actualizada"
            self.stdout.write(
                self.style.SUCCESS(f"  {action} reserva: user_id={uid} ({user.email}) → slot {hour:02d}:00")
            )

        self.stdout.write(self.style.SUCCESS("Listo."))
