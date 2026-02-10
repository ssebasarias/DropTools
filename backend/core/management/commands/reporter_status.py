"""
Muestra el estado de los reportes del bot (OrderReport) por usuario.
Útil para ver si el reporter ha reportado órdenes o está fallando.

Uso:
  python manage.py reporter_status
  python manage.py reporter_status --user-id 2
  docker compose exec backend python backend/manage.py reporter_status --user-id 2
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Count
from core.models import OrderReport


User = get_user_model()


class Command(BaseCommand):
    help = "Muestra estado de reportes (OrderReport) por usuario: reportado, error, etc."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="ID del usuario (por defecto todos los que tienen OrderReport)",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]

        if user_id:
            users = User.objects.filter(id=user_id)
            if not users.exists():
                self.stdout.write(self.style.ERROR(f"Usuario con id={user_id} no existe."))
                return
        else:
            users = User.objects.filter(
                id__in=OrderReport.objects.values_list("user_id", flat=True).distinct()
            ).order_by("id")

        for user in users:
            self._print_user_status(user)

    def _print_user_status(self, user):
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Usuario: {user.email} (ID: {user.id})")
        self.stdout.write("=" * 60)

        total = OrderReport.objects.filter(user=user).count()
        if total == 0:
            self.stdout.write("  Sin registros en OrderReport.")
            return

        # Conteo por status
        status_counts = (
            OrderReport.objects.filter(user=user)
            .values("status")
            .annotate(c=Count("id"))
            .order_by("-c")
        )

        self.stdout.write(f"  Total registros: {total}")
        for s in status_counts:
            label = s["status"] or "(null)"
            self.stdout.write(f"    {label}: {s['c']}")

        reportado = OrderReport.objects.filter(user=user, status="reportado").count()
        errores = OrderReport.objects.filter(user=user, status="error").count()

        self.stdout.write("")
        if reportado > 0:
            self.stdout.write(self.style.SUCCESS(f"  Reportados con exito: {reportado}"))
        if errores > 0:
            self.stdout.write(self.style.WARNING(f"  Errores: {errores}"))

        # Últimos 5 (para ver tendencia)
        ultimos = OrderReport.objects.filter(user=user).order_by("-updated_at")[:5]
        self.stdout.write("")
        self.stdout.write("  Ultimos 5 registros:")
        for r in ultimos:
            self.stdout.write(f"    {r.order_phone} | {r.status} | {r.updated_at}")

        self.stdout.write("")
