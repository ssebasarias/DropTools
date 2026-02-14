import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ..models import AuthToken


class TokenValidationError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_auth_token(user, purpose: str, expires_in_seconds: int, metadata=None, replace_active=True):
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = timezone.now() + timedelta(seconds=expires_in_seconds)

    with transaction.atomic():
        if replace_active:
            AuthToken.objects.filter(
                user=user,
                purpose=purpose,
                used_at__isnull=True,
            ).update(used_at=timezone.now())

        AuthToken.objects.create(
            user=user,
            token_hash=token_hash,
            purpose=purpose,
            expires_at=expires_at,
            metadata=metadata,
        )
    return raw_token


def get_token_record(raw_token: str, purpose: str):
    if not raw_token:
        raise TokenValidationError("missing")

    record = (
        AuthToken.objects.select_related("user")
        .filter(token_hash=hash_token(raw_token), purpose=purpose)
        .order_by("-created_at")
        .first()
    )
    if not record:
        raise TokenValidationError("invalid")
    return record


def validate_token(raw_token: str, purpose: str):
    record = get_token_record(raw_token, purpose)
    now = timezone.now()
    if record.used_at:
        raise TokenValidationError("used")
    if record.expires_at <= now:
        raise TokenValidationError("expired")
    return record


def consume_token(record):
    if record.used_at:
        return record
    record.used_at = timezone.now()
    record.save(update_fields=["used_at"])
    return record
