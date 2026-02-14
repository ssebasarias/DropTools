from django.db import migrations
from django.conf import settings
import base64
import hashlib

from cryptography.fernet import Fernet


def _cipher():
    seed = getattr(settings, "DROPI_PASSWORD_ENCRYPTION_KEY", None)
    if not seed:
        raise RuntimeError(
            "DROPI_PASSWORD_ENCRYPTION_KEY es obligatoria para ejecutar la migración 0018."
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_dropi_passwords(apps, schema_editor):
    User = apps.get_model("core", "User")
    fernet = _cipher()
    for user in User.objects.exclude(dropi_password__isnull=True).exclude(dropi_password=""):
        value = user.dropi_password or ""
        if value.startswith("enc::"):
            continue
        encrypted = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        user.dropi_password = f"enc::{encrypted}"
        user.save(update_fields=["dropi_password"])


def decrypt_dropi_passwords(apps, schema_editor):
    User = apps.get_model("core", "User")
    fernet = _cipher()
    for user in User.objects.exclude(dropi_password__isnull=True).exclude(dropi_password=""):
        value = user.dropi_password or ""
        if not value.startswith("enc::"):
            continue
        token = value.replace("enc::", "", 1)
        try:
            plain = fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception:
            continue
        user.dropi_password = plain
        user.save(update_fields=["dropi_password"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_order_movement_real_inactivity_fields"),
    ]

    operations = [
        migrations.RunPython(encrypt_dropi_passwords, decrypt_dropi_passwords),
    ]
