# -*- coding: utf-8 -*-
"""
Proxy Allocator Service
Asignación de proxy a usuarios y obtención de config para Selenium.
No loguea contraseñas.
"""
import logging
from django.db import transaction

from core.models import ProxyIP, UserProxyAssignment
from core.crypto import decrypt_if_needed

logger = logging.getLogger(__name__)


def _count_assignments_for_proxy(proxy_id):
    """Número de usuarios asignados a un proxy."""
    return UserProxyAssignment.objects.filter(proxy_id=proxy_id).count()


def assign_proxy_to_user(user_id):
    """
    Asigna un proxy disponible al usuario (si hay hueco en algún proxy activo).
    No asigna si el usuario ya tiene proxy.

    Returns:
        UserProxyAssignment si se asignó, None si no hay proxy disponible o ya tenía.
    """
    if UserProxyAssignment.objects.filter(user_id=user_id).exists():
        return UserProxyAssignment.objects.get(user_id=user_id)

    proxies = ProxyIP.objects.filter(status=ProxyIP.STATUS_ACTIVE).order_by('id')
    for proxy in proxies:
        count = _count_assignments_for_proxy(proxy.id)
        if count < proxy.max_accounts:
            with transaction.atomic():
                # Doble comprobación bajo lock
                current = UserProxyAssignment.objects.filter(proxy_id=proxy.id).count()
                if current >= proxy.max_accounts:
                    continue
                assignment = UserProxyAssignment.objects.create(
                    user_id=user_id,
                    proxy_id=proxy.id,
                )
                logger.info("Proxy assigned to user_id=%s proxy_id=%s (no credentials logged)", user_id, proxy.id)
                return assignment
    return None


def get_proxy_config_for_user(user_id):
    """
    Devuelve la config de proxy para Selenium para el usuario, o None si no tiene asignación.

    Returns:
        dict con keys: host, port, username (opcional), password (opcional).
        O None si el usuario no tiene proxy asignado o el proxy está inactivo.
    """
    try:
        assignment = UserProxyAssignment.objects.select_related('proxy').get(user_id=user_id)
    except UserProxyAssignment.DoesNotExist:
        return None

    proxy = assignment.proxy
    if proxy.status != ProxyIP.STATUS_ACTIVE:
        return None

    config = {
        'host': proxy.ip,
        'port': proxy.port,
    }
    if proxy.username:
        config['username'] = proxy.username
    if proxy.password_encrypted:
        config['password'] = decrypt_if_needed(proxy.password_encrypted)
    else:
        config['password'] = None
    return config


def update_last_used(user_id):
    """Actualiza last_used_at de la asignación del usuario (opcional, para auditoría)."""
    from django.utils import timezone
    UserProxyAssignment.objects.filter(user_id=user_id).update(last_used_at=timezone.now())
