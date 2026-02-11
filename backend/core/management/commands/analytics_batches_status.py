# -*- coding: utf-8 -*-
"""Diagnóstico: batches y snapshots por usuario para Analytics."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from core.models import User, ReportBatch, RawOrderSnapshot


class Command(BaseCommand):
    help = "Lista ReportBatch y RawOrderSnapshot por usuario (para depurar Analytics vacío)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            default=None,
            help="ID de usuario (si no se pasa, lista todos los que tienen batches)",
        )

    def handle(self, *args, **options):
        user_id = options.get("user")
        now = timezone.now()
        last_24h = now - timezone.timedelta(hours=24)

        self.stdout.write("=" * 60)
        self.stdout.write("ANALYTICS: ReportBatch y RawOrderSnapshot por usuario")
        self.stdout.write("=" * 60)

        if user_id is not None:
            try:
                users = [User.objects.get(id=user_id)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Usuario id={user_id} no existe."))
                return
        else:
            users = list(
                User.objects.filter(
                    id__in=ReportBatch.objects.values_list("user_id", flat=True).distinct()
                ).order_by("id")
            )

        for user in users:
            self.stdout.write(f"\nUsuario id={user.id} | {getattr(user, 'email', user.username)}")
            batches = ReportBatch.objects.filter(user=user).order_by("-created_at")
            total_batches = batches.count()
            by_status = batches.values("status").annotate(c=Count("id"))
            self.stdout.write(f"  ReportBatch total: {total_batches}")
            for s in by_status:
                self.stdout.write(f"    - status={s['status']}: {s['c']}")

            with_snapshots = ReportBatch.objects.filter(user=user).annotate(
                snap_count=Count("snapshots")
            ).filter(snap_count__gt=0)
            batch_ids_with_data = list(with_snapshots.values_list("id", flat=True)[:10])
            self.stdout.write(f"  Batches con al menos 1 snapshot: {with_snapshots.count()}")

            if batch_ids_with_data:
                snap_total = RawOrderSnapshot.objects.filter(batch_id__in=batch_ids_with_data).count()
                self.stdout.write(f"  Snapshots (en esos batches): {snap_total}")
                self.stdout.write("  Últimos 5 batches con datos:")
                for b in batches.filter(id__in=batch_ids_with_data)[:5]:
                    n = RawOrderSnapshot.objects.filter(batch_id=b.id).count()
                    created_local = timezone.localtime(b.created_at)
                    self.stdout.write(f"    - batch id={b.id} status={b.status} created={created_local} snapshots={n}")
            else:
                self.stdout.write(self.style.WARNING("  No hay ningún batch con snapshots para este usuario."))
                self.stdout.write("  Analytics mostrará vacío hasta que se ejecute el downloader y se guarden datos.")

            batches_last_24h = batches.filter(created_at__gte=last_24h)
            self.stdout.write(f"  Batches creados en últimas 24h: {batches_last_24h.count()}")

        self.stdout.write("\n" + "=" * 60)
