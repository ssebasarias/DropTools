from django.db import models
from django.conf import settings


class AuthToken(models.Model):
    PURPOSE_VERIFY_EMAIL = "verify_email"
    PURPOSE_RESET_PASSWORD = "reset_password"
    PURPOSE_CHOICES = [
        (PURPOSE_VERIFY_EMAIL, "Verify email"),
        (PURPOSE_RESET_PASSWORD, "Reset password"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_tokens",
    )
    token_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "auth_tokens"
        indexes = [
            models.Index(fields=["token_hash", "purpose"]),
            models.Index(fields=["user", "purpose"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.purpose}"
