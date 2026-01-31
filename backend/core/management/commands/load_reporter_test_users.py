"""
Comando para cargar usuarios de prueba del reporter desde un archivo JSON.
Crea o actualiza usuarios por email/username; no hardcodea contraseñas (vienen del archivo).

Uso:
  python manage.py load_reporter_test_users --file=scripts/reporter_test_users.json

Con Docker:
  docker compose exec backend python manage.py load_reporter_test_users --file=scripts/reporter_test_users.json
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Carga usuarios de prueba del reporter desde un archivo JSON (crea/actualiza por email)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="scripts/reporter_test_users.json",
            help="Ruta al archivo JSON con la lista de usuarios.",
        )
        parser.add_argument(
            "--force-id",
            action="store_true",
            help="Intentar asignar el id del JSON al crear (solo si el id no existe).",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        force_id = options.get("force_id", False)

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {file_path}"))
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"JSON inválido: {e}"))
            return

        if not isinstance(data, list):
            self.stdout.write(self.style.ERROR("El JSON debe ser una lista de usuarios."))
            return

        created_count = 0
        updated_count = 0

        for item in data:
            email = item.get("email") or item.get("username")
            if not email:
                self.stderr.write(f"  Omitido: entrada sin email/username")
                continue

            username = item.get("username", email)
            password = item.get("password", "")
            full_name = item.get("full_name", "")
            role = item.get("role", User.ROLE_CLIENT)
            subscription_tier = item.get("subscription_tier", User.TIER_PLATINUM)
            subscription_active = item.get("subscription_active", True)
            dropi_email = item.get("dropi_email", "")
            dropi_password = item.get("dropi_password", "")
            is_staff = item.get("is_staff", False)
            is_superuser = item.get("is_superuser", False)
            desired_id = item.get("id")

            existing = (
                User.objects.filter(email=email).first()
                or User.objects.filter(username=username).first()
            )
            if existing:
                existing.username = username
                existing.email = email
                if password:
                    existing.set_password(password)
                existing.full_name = full_name
                existing.role = role
                existing.subscription_tier = subscription_tier
                existing.subscription_active = subscription_active
                existing.dropi_email = dropi_email or None
                existing.dropi_password = dropi_password or ""
                existing.is_staff = is_staff
                existing.is_superuser = is_superuser
                existing.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Actualizado: {email} (ID: {existing.id})")
                )
            else:
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=role,
                    subscription_tier=subscription_tier,
                    subscription_active=subscription_active,
                    dropi_email=dropi_email or None,
                    dropi_password=dropi_password or "",
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )
                if password:
                    user.set_password(password)
                if force_id and desired_id is not None and not User.objects.filter(pk=desired_id).exists():
                    user.pk = desired_id
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Creado: {email} (ID: {user.id})")
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Listo: {created_count} creados, {updated_count} actualizados.")
        )
