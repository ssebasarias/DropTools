"""
Comando para replicar datos del reporter de un usuario fuente a otros usuarios.
Copia ReportBatch + RawOrderSnapshot + OrderMovementReport (is_resolved=False) del usuario
fuente al último batch SUCCESS; crea batches nuevos para cada usuario destino con los
mismos snapshots y order_movement_reports. No modifica ni borra datos del usuario fuente.

Uso:
  python manage.py replicate_reporter_user_data --source-user=2 --target-users=3,4
  python manage.py replicate_reporter_user_data --source-user=2 --target-users=3,4 --dry-run

Con Docker:
  docker compose exec backend python manage.py replicate_reporter_user_data --source-user=2 --target-users=3,4
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import ReportBatch, RawOrderSnapshot, OrderMovementReport

User = get_user_model()


class Command(BaseCommand):
    help = "Replica ReportBatch + RawOrderSnapshot + OrderMovementReport del usuario fuente a los usuarios destino."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-user",
            type=int,
            required=True,
            help="ID del usuario del que se copian los datos (ej. 2).",
        )
        parser.add_argument(
            "--target-users",
            type=str,
            required=True,
            help="IDs de usuarios destino separados por coma (ej. 3,4).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo imprimir qué se copiaría, sin escribir en BD.",
        )

    def handle(self, *args, **options):
        source_user_id = options["source_user"]
        target_ids = [int(x.strip()) for x in options["target_users"].split(",") if x.strip()]
        dry_run = options.get("dry_run", False)

        source_user = User.objects.filter(id=source_user_id).first()
        if not source_user:
            self.stdout.write(self.style.ERROR(f"Usuario fuente {source_user_id} no existe."))
            return

        source_batch = (
            ReportBatch.objects.filter(user_id=source_user_id, status="SUCCESS")
            .order_by("-created_at")
            .first()
        )
        if not source_batch:
            self.stdout.write(
                self.style.ERROR(f"Usuario {source_user_id} no tiene ningún ReportBatch con status=SUCCESS.")
            )
            return

        snapshots = list(RawOrderSnapshot.objects.filter(batch=source_batch).order_by("id"))
        reports = list(
            OrderMovementReport.objects.filter(batch=source_batch, is_resolved=False)
        )
        self.stdout.write(
            f"Origen: user_id={source_user_id}, batch_id={source_batch.id}, "
            f"snapshots={len(snapshots)}, order_movement_reports(is_resolved=False)={len(reports)}"
        )

        if dry_run:
            for tid in target_ids:
                u = User.objects.filter(id=tid).first()
                if not u:
                    self.stdout.write(self.style.WARNING(f"  Usuario destino {tid} no existe; se omitiría."))
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [DRY-RUN] Se crearían 1 ReportBatch, {len(snapshots)} RawOrderSnapshot, "
                            f"{len(reports)} OrderMovementReport para user_id={tid} ({u.email})."
                        )
                    )
            return

        for tid in target_ids:
            target_user = User.objects.filter(id=tid).first()
            if not target_user:
                self.stdout.write(self.style.WARNING(f"Usuario destino {tid} no existe; omitido."))
                continue

            new_batch = ReportBatch.objects.create(
                user_id=tid,
                account_email=target_user.dropi_email or target_user.email,
                status="SUCCESS",
                total_records=source_batch.total_records,
            )
            snapshot_map = {}  # old_snapshot_id -> new_snapshot_id
            for snap in snapshots:
                new_snap = RawOrderSnapshot.objects.create(
                    batch=new_batch,
                    dropi_order_id=snap.dropi_order_id,
                    shopify_order_id=snap.shopify_order_id,
                    guide_number=snap.guide_number,
                    current_status=snap.current_status,
                    carrier=snap.carrier,
                    customer_name=snap.customer_name,
                    customer_phone=snap.customer_phone,
                    customer_email=snap.customer_email,
                    address=snap.address,
                    city=snap.city,
                    department=snap.department,
                    product_name=snap.product_name,
                    product_id=snap.product_id,
                    sku=snap.sku,
                    variation=snap.variation,
                    quantity=snap.quantity,
                    total_amount=snap.total_amount,
                    profit=snap.profit,
                    shipping_price=snap.shipping_price,
                    supplier_price=snap.supplier_price,
                    store_type=snap.store_type,
                    store_name=snap.store_name,
                    order_date=snap.order_date,
                    order_time=snap.order_time,
                    report_date=snap.report_date,
                )
                snapshot_map[snap.id] = new_snap.id

            for rep in reports:
                new_snap_id = snapshot_map.get(rep.snapshot_id)
                if new_snap_id is None:
                    continue
                OrderMovementReport.objects.create(
                    batch=new_batch,
                    snapshot_id=new_snap_id,
                    days_since_order=rep.days_since_order,
                    is_resolved=False,
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Replicado a user_id={tid} ({target_user.email}): batch_id={new_batch.id}, "
                    f"{len(snapshot_map)} snapshots, {len(reports)} order_movement_reports."
                )
            )

        self.stdout.write(self.style.SUCCESS("Listo."))
