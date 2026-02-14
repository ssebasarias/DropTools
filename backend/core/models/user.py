from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken


logger = logging.getLogger(__name__)


class User(AbstractUser):
    """
    Modelo de usuario unificado que combina:
    - auth_user (login del aplicativo) - heredado de AbstractUser
    - user_profiles (perfil, rol, suscripción)
    - dropi_accounts (credenciales Dropi)
    
    Esta es la única tabla de usuarios en el sistema.
    """
    
    ROLE_ADMIN = "ADMIN"
    ROLE_CLIENT = "CLIENT"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_CLIENT, "Client"),
    ]
    
    TIER_BRONZE = "BRONZE"
    TIER_SILVER = "SILVER"
    TIER_GOLD = "GOLD"
    TIER_PLATINUM = "PLATINUM"
    TIER_CHOICES = [
        (TIER_BRONZE, "Bronze"),
        (TIER_SILVER, "Silver"),
        (TIER_GOLD, "Gold"),
        (TIER_PLATINUM, "Platinum"),
    ]
    
    # Campos de user_profiles (perfil y suscripción)
    full_name = models.CharField(max_length=120, blank=True, default="")
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    subscription_tier = models.CharField(max_length=10, choices=TIER_CHOICES, default=TIER_BRONZE)
    subscription_active = models.BooleanField(default=False)
    execution_time = models.TimeField(null=True, blank=True, help_text="Hora diaria para ejecutar el workflow de reportes (formato HH:MM)")
    
    # Campos de dropi_accounts (credenciales Dropi - cuenta principal)
    dropi_email = models.EmailField(max_length=255, null=True, blank=True, help_text="Email de la cuenta Dropi principal")
    dropi_password = models.CharField(max_length=255, null=True, blank=True, help_text="Password de la cuenta Dropi (cifrado en reposo)")

    # Estimación de carga (usado en reservas por hora)
    monthly_orders_estimate = models.PositiveIntegerField(null=True, blank=True, help_text="Órdenes mensuales aproximadas")

    # Timestamps adicionales
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
            models.Index(fields=["role", "subscription_tier"]),
            models.Index(fields=["subscription_active"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.username} ({self.role}/{self.subscription_tier})"
    
    def is_admin(self) -> bool:
        """Retorna True si el usuario es admin"""
        return self.role == self.ROLE_ADMIN or self.is_superuser
    
    def get_dropi_password_plain(self) -> str:
        """
        Retorna la contraseña Dropi desencriptada.
        Mantiene compatibilidad con datos legacy en texto plano.
        """
        value = self.dropi_password or ""
        if not value:
            return ""
        if not value.startswith("enc::"):
            return value
        token = value.replace("enc::", "", 1)
        try:
            decrypted = self._get_dropi_cipher().decrypt(token.encode("utf-8"))
            return decrypted.decode("utf-8")
        except (InvalidToken, ValueError, TypeError) as exc:
            logger.warning("No se pudo desencriptar dropi_password para user_id=%s: %s", self.id, exc)
            return ""
    
    def set_dropi_password_plain(self, raw: str) -> None:
        """
        Guarda la contraseña Dropi en formato cifrado reversible.
        """
        plain = (raw or "").strip()
        if not plain:
            self.dropi_password = ""
            return
        encrypted = self._get_dropi_cipher().encrypt(plain.encode("utf-8")).decode("utf-8")
        self.dropi_password = f"enc::{encrypted}"

    @staticmethod
    def _get_dropi_cipher() -> Fernet:
        seed = getattr(settings, "DROPI_PASSWORD_ENCRYPTION_KEY", None)
        if not seed:
            raise ValueError("Falta DROPI_PASSWORD_ENCRYPTION_KEY para cifrar credenciales de Dropi.")
        key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())
        return Fernet(key)
