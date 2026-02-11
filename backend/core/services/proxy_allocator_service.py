# -*- coding: utf-8 -*-
"""
Proxy Allocator Service
Asignación de proxy a usuarios y obtención de config para Selenium.
Implementa asignación secuencial: 4 usuarios por IP, llenando completamente una IP antes de pasar a la siguiente.
Manejo automático de IPs bloqueadas con migración de usuarios.
No loguea contraseñas.
"""
import logging
from django.db import transaction
from django.utils import timezone

from core.models import ProxyIP, UserProxyAssignment
from core.crypto import decrypt_if_needed

logger = logging.getLogger(__name__)


def _count_assignments_for_proxy(proxy_id):
    """Número de usuarios asignados a un proxy."""
    return UserProxyAssignment.objects.filter(proxy_id=proxy_id).count()


def _force_reassign_proxy(user_id):
    """
    Fuerza la reasignación de un usuario eliminando su asignación actual.
    Función interna para migración cuando el proxy está bloqueado.
    
    Returns:
        UserProxyAssignment si se reasignó, None si no hay proxy disponible.
    """
    # Eliminar asignación actual si existe
    UserProxyAssignment.objects.filter(user_id=user_id).delete()
    
    # Buscar nueva IP disponible usando la lógica secuencial
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
                logger.info("Proxy reassigned to user_id=%s proxy_id=%s (migration from blocked proxy)", user_id, proxy.id)
                return assignment
    return None


def assign_proxy_to_user(user_id):
    """
    Asigna un proxy disponible al usuario usando asignación secuencial.
    Llena completamente una IP (4 usuarios) antes de pasar a la siguiente.
    No asigna si el usuario ya tiene proxy.
    
    Returns:
        UserProxyAssignment si se asignó, None si no hay proxy disponible o ya tenía.
    """
    if UserProxyAssignment.objects.filter(user_id=user_id).exists():
        return UserProxyAssignment.objects.get(user_id=user_id)

    # Buscar IPs activas ordenadas por ID para mantener consistencia
    proxies = ProxyIP.objects.filter(status=ProxyIP.STATUS_ACTIVE).order_by('id')
    
    for proxy in proxies:
        count = _count_assignments_for_proxy(proxy.id)
        # Asignación secuencial: solo asignar si hay espacio en esta IP
        # No pasar a la siguiente hasta que esta esté completamente llena
        if count < proxy.max_accounts:
            with transaction.atomic():
                # Doble comprobación bajo lock para evitar race conditions
                current = UserProxyAssignment.objects.filter(proxy_id=proxy.id).count()
                if current >= proxy.max_accounts:
                    continue
                assignment = UserProxyAssignment.objects.create(
                    user_id=user_id,
                    proxy_id=proxy.id,
                )
                logger.info("Proxy assigned to user_id=%s proxy_id=%s (sequential assignment, %d/%d users)", 
                           user_id, proxy.id, current + 1, proxy.max_accounts)
                return assignment
    
    logger.warning("No available proxy found for user_id=%s", user_id)
    return None


def mark_proxy_blocked(proxy_id, reason=None):
    """
    Marca un proxy como bloqueado y migra automáticamente a los usuarios asignados.
    
    Args:
        proxy_id: ID del proxy a marcar como bloqueado
        reason: Razón del bloqueo (opcional)
    
    Returns:
        Número de usuarios migrados, o None si el proxy no existe o ya está bloqueado
    """
    try:
        proxy = ProxyIP.objects.get(id=proxy_id)
    except ProxyIP.DoesNotExist:
        logger.error("Proxy id=%s not found for blocking", proxy_id)
        return None
    
    if proxy.status == ProxyIP.STATUS_BLOCKED:
        logger.warning("Proxy id=%s is already blocked", proxy_id)
        return None
    
    # Marcar proxy como bloqueado
    proxy.status = ProxyIP.STATUS_BLOCKED
    proxy.blocked_at = timezone.now()
    proxy.block_reason = reason or "Proxy bloqueado por detección de automatización"
    proxy.save()
    
    logger.warning("Proxy id=%s (%s:%s) marked as blocked. Reason: %s", 
                  proxy_id, proxy.ip, proxy.port, proxy.block_reason)
    
    # Migrar usuarios automáticamente
    migrated_count = migrate_users_from_blocked_proxy(proxy_id)
    
    return migrated_count


def migrate_users_from_blocked_proxy(blocked_proxy_id):
    """
    Migra todos los usuarios asignados a un proxy bloqueado a nuevas IPs disponibles.
    
    Args:
        blocked_proxy_id: ID del proxy bloqueado
    
    Returns:
        Número de usuarios migrados exitosamente
    """
    try:
        blocked_proxy = ProxyIP.objects.get(id=blocked_proxy_id)
    except ProxyIP.DoesNotExist:
        logger.error("Blocked proxy id=%s not found for migration", blocked_proxy_id)
        return 0
    
    # Obtener todos los usuarios asignados al proxy bloqueado
    assignments = UserProxyAssignment.objects.filter(proxy_id=blocked_proxy_id).select_related('user')
    user_ids = [assignment.user_id for assignment in assignments]
    
    if not user_ids:
        logger.info("No users assigned to blocked proxy id=%s", blocked_proxy_id)
        return 0
    
    logger.info("Migrating %d users from blocked proxy id=%s (%s:%s)", 
                len(user_ids), blocked_proxy_id, blocked_proxy.ip, blocked_proxy.port)
    
    migrated_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        try:
            # Forzar reasignación eliminando la asignación actual y creando una nueva
            new_assignment = _force_reassign_proxy(user_id)
            if new_assignment:
                migrated_count += 1
                logger.info("User id=%s migrated from proxy id=%s to proxy id=%s", 
                           user_id, blocked_proxy_id, new_assignment.proxy_id)
            else:
                failed_count += 1
                logger.error("Failed to migrate user id=%s from blocked proxy id=%s - no available proxies", 
                            user_id, blocked_proxy_id)
        except Exception as e:
            failed_count += 1
            logger.exception("Error migrating user id=%s from blocked proxy id=%s: %s", 
                           user_id, blocked_proxy_id, str(e))
    
    logger.info("Migration completed: %d users migrated, %d failed from blocked proxy id=%s", 
                migrated_count, failed_count, blocked_proxy_id)
    
    return migrated_count


def get_proxy_config_for_user(user_id):
    """
    Devuelve la config de proxy para Selenium para el usuario.
    Si el proxy asignado está bloqueado, migra automáticamente al usuario a una nueva IP.
    
    Returns:
        dict con keys: host, port, username (opcional), password (opcional).
        O None si el usuario no tiene proxy asignado o no hay proxy disponible después de migración.
    """
    try:
        assignment = UserProxyAssignment.objects.select_related('proxy').get(user_id=user_id)
    except UserProxyAssignment.DoesNotExist:
        # Usuario no tiene asignación, intentar asignar una nueva
        assignment = assign_proxy_to_user(user_id)
        if not assignment:
            return None
        assignment = UserProxyAssignment.objects.select_related('proxy').get(user_id=user_id)

    proxy = assignment.proxy
    
    # Si el proxy está bloqueado, migrar automáticamente
    if proxy.status == ProxyIP.STATUS_BLOCKED:
        logger.warning("User id=%s has blocked proxy id=%s, attempting migration", user_id, proxy.id)
        new_assignment = _force_reassign_proxy(user_id)
        if not new_assignment:
            logger.error("Failed to migrate user id=%s from blocked proxy id=%s", user_id, proxy.id)
            return None
        # Obtener la nueva asignación
        assignment = UserProxyAssignment.objects.select_related('proxy').get(user_id=user_id)
        proxy = assignment.proxy
    
    # Solo retornar config si el proxy está activo
    if proxy.status != ProxyIP.STATUS_ACTIVE:
        logger.warning("User id=%s has proxy id=%s with status=%s, cannot provide config", 
                      user_id, proxy.id, proxy.status)
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
    UserProxyAssignment.objects.filter(user_id=user_id).update(last_used_at=timezone.now())
