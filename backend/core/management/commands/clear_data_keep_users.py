"""
Borra todos los datos de la base de datos EXCEPTO la tabla de usuarios (users).
Útil para dejar reportes, órdenes, productos, clusters, etc. en cero y conservar
solo las cuentas de usuario (login, rol, suscripción, credenciales Dropi).

Uso:
  python backend/manage.py clear_data_keep_users
  python backend/manage.py clear_data_keep_users --no-sessions   # no borra sesiones (no cerrar sesión a nadie)
"""
from django.core.management.base import BaseCommand
from django.apps import apps


# Orden de borrado: tablas "hijas" primero (tienen FK a otras que también vaciamos).
# No se toca core.User (tabla users).
DELETE_ORDER = [
    # Reporter / órdenes (hijos primero)
    "core.OrderMovementReport",
    "core.RawOrderSnapshot",
    "core.OrderReport",
    "core.WorkflowProgress",
    "core.ReportBatch",
    # Productos / clusters (hijos primero)
    "core.ProductEmbedding",
    "core.ProductClusterMembership",
    "core.MarketIntelligenceLog",
    "core.UniqueProductCluster",
    "core.ProductCategory",
    "core.ProductStockLog",
    "core.Product",
    "core.AIFeedback",
    "core.ClusterDecisionLog",
    "core.ClusterConfig",
    "core.MarketplaceFeedback",
    "core.Category",
    "core.FutureEvent",
    "core.Warehouse",
    "core.Supplier",
    "core.ConceptWeights",
    "core.DomainReputation",
    "core.MarketAnalysisReport",
    "core.CompetitorFinding",
]


class Command(BaseCommand):
    help = "Borra todos los datos excepto la tabla de usuarios (users)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-sessions",
            action="store_true",
            help="No borrar sesiones (los usuarios no tendrán que volver a iniciar sesión).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué se borraría, sin ejecutar.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        clear_sessions = not options["no_sessions"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se borrará nada."))

        deleted = {}
        for label in DELETE_ORDER:
            try:
                model = apps.get_model(label)
            except LookupError:
                continue
            count = model.objects.count()
            if count > 0:
                deleted[label] = count
                if not dry_run:
                    model.objects.all().delete()
                    self.stdout.write(f"  Borrados {count} registros de {label}")

        if clear_sessions and not dry_run:
            from django.contrib.sessions.models import Session
            session_count = Session.objects.count()
            Session.objects.all().delete()
            deleted["django.contrib.sessions.Session"] = session_count
            self.stdout.write(f"  Borradas {session_count} sesiones")

        if dry_run:
            for label, count in deleted.items():
                self.stdout.write(f"  [DRY RUN] Se borrarían {count} de {label}")
            self.stdout.write(self.style.SUCCESS("DRY RUN completado. Ejecuta sin --dry-run para aplicar."))
        else:
            total = sum(deleted.values())
            self.stdout.write(self.style.SUCCESS(f"Listo. Borrados {total} registros en total. Tabla 'users' intacta."))
