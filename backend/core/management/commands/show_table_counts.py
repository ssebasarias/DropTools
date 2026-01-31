"""
Muestra el número de registros en las tablas principales (core y sesiones).
Útil para verificar que clear_data_keep_users dejó todo en cero excepto users.

Uso:
  python backend/manage.py show_table_counts
"""
from django.core.management.base import BaseCommand
from django.apps import apps


# Tablas que vacía clear_data_keep_users (mismo orden lógico para la salida)
TABLES_TO_SHOW = [
    "core.OrderMovementReport",
    "core.RawOrderSnapshot",
    "core.OrderReport",
    "core.WorkflowProgress",
    "core.ReportBatch",
    "core.ProductEmbedding",
    "core.ProductClusterMembership",
    "core.UniqueProductCluster",
    "core.ProductCategory",
    "core.ProductStockLog",
    "core.Product",
    "core.User",
]


class Command(BaseCommand):
    help = "Muestra conteos de registros en tablas principales (para verificar vaciado)."

    def handle(self, *args, **options):
        self.stdout.write("Tabla                          | Registros")
        self.stdout.write("-" * 42)

        total_rest = 0
        for label in TABLES_TO_SHOW:
            try:
                model = apps.get_model(label)
            except LookupError:
                continue
            count = model.objects.count()
            # Nombre corto para la tabla (model name o db_table)
            name = getattr(model._meta, "db_table", label) or label
            name = name.ljust(30)
            self.stdout.write(f"  {name} | {count}")
            if label != "core.User":
                total_rest += count

        # Sesiones (opcional)
        try:
            from django.contrib.sessions.models import Session
            session_count = Session.objects.count()
            self.stdout.write(f"  {'django_session'.ljust(30)} | {session_count}")
            total_rest += session_count
        except Exception:
            pass

        self.stdout.write("-" * 42)
        users = 0
        try:
            User = apps.get_model("core.User")
            users = User.objects.count()
        except LookupError:
            pass
        self.stdout.write(self.style.SUCCESS(f"  users (conservados)           | {users}"))
        self.stdout.write(f"  Total resto (debe ser 0 si vaciaste) | {total_rest}")
