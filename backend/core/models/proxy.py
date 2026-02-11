from django.db import models
from django.conf import settings
from .user import User


class ProxyIP(models.Model):
    """
    Proxy o IP estática para uso con Selenium (cuentas Dropi).
    Limita cantidad de usuarios por IP (max_accounts).
    """
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_BLOCKED = 'blocked'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Activo'),
        (STATUS_INACTIVE, 'Inactivo'),
        (STATUS_BLOCKED, 'Bloqueado'),
    ]

    ip = models.CharField(max_length=255, db_index=True, help_text="Host o IP del proxy")
    port = models.PositiveIntegerField(default=8080, help_text="Puerto del proxy")
    username = models.CharField(max_length=255, null=True, blank=True)
    password_encrypted = models.CharField(max_length=512, null=True, blank=True, help_text="Contraseña (encriptada si DROPIPASS_ENCRYPTION_KEY está configurado)")
    max_accounts = models.PositiveSmallIntegerField(default=4, help_text="Máximo de cuentas (usuarios) por este proxy")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    blocked_at = models.DateTimeField(null=True, blank=True, help_text="Fecha cuando se bloqueó el proxy")
    block_reason = models.TextField(null=True, blank=True, help_text="Razón del bloqueo del proxy")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'proxy_ips'
        verbose_name = "Proxy IP"
        verbose_name_plural = "Proxy IPs"
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.ip}:{self.port} (max={self.max_accounts})"


class UserProxyAssignment(models.Model):
    """
    Asignación de un proxy a un usuario (un usuario, un proxy).
    Usado por el reporter para inyectar proxy en Selenium.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='proxy_assignment'
    )
    proxy = models.ForeignKey(
        ProxyIP,
        on_delete=models.CASCADE,
        related_name='user_assignments'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_proxy_assignments'
        verbose_name = "Asignación Usuario Proxy"
        verbose_name_plural = "Asignaciones Usuario Proxy"
        indexes = [
            models.Index(fields=['proxy']),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.proxy_id}"
