from __future__ import annotations

import os


_PREFIX = "enc:v1:"


def _get_fernet():
    """
    Returns a Fernet instance if DROPIPASS_ENCRYPTION_KEY is configured.
    Key must be a urlsafe-base64 32-byte key.
    """
    key = os.getenv("DROPIPASS_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    from cryptography.fernet import Fernet

    return Fernet(key.encode("utf-8"))


def encrypt_if_needed(value: str) -> str:
    """
    Encrypts only if Fernet key exists and value is not already encrypted.
    """
    if not value:
        return value
    if value.startswith(_PREFIX):
        return value
    f = _get_fernet()
    if not f:
        return value
    token = f.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_if_needed(value: str) -> str:
    """
    Decrypts only if value has enc prefix and key exists.
    If key is missing, returns the raw stored value (fail-open for local dev).
    """
    if not value:
        return value
    if not value.startswith(_PREFIX):
        return value
    f = _get_fernet()
    if not f:
        return value
    token = value[len(_PREFIX) :]
    return f.decrypt(token.encode("utf-8")).decode("utf-8")

