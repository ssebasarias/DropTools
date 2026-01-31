"""
Comando para cargar los usuarios iniciales en la base de datos.
Credenciales de aplicación y Dropi se guardan en la tabla users (no en .env).

Uso:
  python manage.py load_initial_users

Con Docker:
  docker compose exec backend python manage.py load_initial_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


# Usuarios a cargar: aplicación (email/contraseña) y Dropi (dropi_email/dropi_password)
INITIAL_USERS = [
    {
        "id": 1,
        "full_name": "admin",
        "email": "guerreroarias20@gmail.com",
        "password": "#Yummi_0091",
        "role": User.ROLE_ADMIN,
        "subscription_tier": User.TIER_PLATINUM,
        "subscription_active": True,
        "dropi_email": "guerreroarias20@gmail.com",
        "dropi_password": "PAgRRquZSmh86_k",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "id": 2,
        "full_name": "martin",
        "email": "martin@dahell.com",
        "password": "martin123",
        "role": User.ROLE_CLIENT,
        "subscription_tier": User.TIER_PLATINUM,
        "subscription_active": True,
        "dropi_email": "dahellonline@gmail.com",
        "dropi_password": "Bigotes2001@",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "id": 3,
        "full_name": "sebastian",
        "email": "sebastian@dahell.com",
        "password": "sebas123",
        "role": User.ROLE_CLIENT,
        "subscription_tier": User.TIER_PLATINUM,
        "subscription_active": True,
        "dropi_email": "guerreroarias20@gmail.com",
        "dropi_password": "PAgRRquZSmh86_k",
        "is_staff": False,
        "is_superuser": False,
    },
]


class Command(BaseCommand):
    help = "Carga los usuarios iniciales (app + Dropi) en la tabla users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-id",
            action="store_true",
            help="Intentar asignar IDs 1,2,3 (solo en BD vacía o con cuidado).",
        )

    def handle(self, *args, **options):
        force_id = options.get("force_id", False)
        created_count = 0
        updated_count = 0

        for data in INITIAL_USERS:
            desired_id = data["id"]
            email = data["email"]
            password = data["password"]
            username = email  # login por email

            existing = User.objects.filter(email=email).first() or User.objects.filter(username=username).first()
            if existing:
                existing.username = username
                existing.email = email
                existing.set_password(password)
                existing.full_name = data["full_name"]
                existing.role = data["role"]
                existing.subscription_tier = data["subscription_tier"]
                existing.subscription_active = data["subscription_active"]
                existing.dropi_email = data["dropi_email"]
                existing.dropi_password = data["dropi_password"]
                existing.is_staff = data["is_staff"]
                existing.is_superuser = data["is_superuser"]
                existing.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Actualizado: {email} (ID: {existing.id})")
                )
            else:
                user = User(
                    username=username,
                    email=email,
                    full_name=data["full_name"],
                    role=data["role"],
                    subscription_tier=data["subscription_tier"],
                    subscription_active=data["subscription_active"],
                    dropi_email=data["dropi_email"],
                    dropi_password=data["dropi_password"],
                    is_staff=data["is_staff"],
                    is_superuser=data["is_superuser"],
                )
                user.set_password(password)
                if force_id and not User.objects.filter(pk=desired_id).exists():
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
