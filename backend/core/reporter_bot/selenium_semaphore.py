"""
Semáforo Redis para limitar procesos Selenium simultáneos (MAX_ACTIVE_SELENIUM).
Usado por download_compare_task y report_range_task.
"""
import time
import logging

logger = logging.getLogger(__name__)

SEMAPHORE_KEY = 'reporter:selenium:semaphore'


def _get_redis():
    """Obtiene cliente Redis desde CELERY_BROKER_URL."""
    from django.conf import settings
    import redis
    url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
    return redis.from_url(url, decode_responses=True)


def get_max_slots():
    """Devuelve el máximo de slots (desde DB ReporterSlotConfig o settings)."""
    try:
        from django.conf import settings
        from core.models import ReporterSlotConfig
        config = ReporterSlotConfig.objects.first()
        if config:
            return config.max_active_selenium
        return getattr(settings, 'MAX_ACTIVE_SELENIUM', 6)
    except Exception:
        from django.conf import settings
        return getattr(settings, 'MAX_ACTIVE_SELENIUM', 6)


def acquire(timeout_seconds=3300, poll_interval=10):
    """
    Adquiere un slot del semáforo. Espera hasta timeout_seconds si no hay slot libre.
    Returns:
        True si se adquirió el slot, False si timeout.
    """
    r = _get_redis()
    max_slots = get_max_slots()
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        current = r.incr(SEMAPHORE_KEY)
        if current <= max_slots:
            logger.debug(f"Selenium semaphore acquired (current={current}, max={max_slots})")
            return True
        r.decr(SEMAPHORE_KEY)
        time.sleep(min(poll_interval, deadline - time.time()))

    logger.warning("Selenium semaphore acquire timeout")
    return False


def release():
    """Libera un slot del semáforo. No baja de 0."""
    r = _get_redis()
    current = r.decr(SEMAPHORE_KEY)
    if current < 0:
        r.set(SEMAPHORE_KEY, 0)
        current = 0
    logger.debug(f"Selenium semaphore released (current={current})")
    return current


def current_count():
    """Devuelve el número actual de slots ocupados (solo lectura)."""
    r = _get_redis()
    try:
        return int(r.get(SEMAPHORE_KEY) or 0)
    except Exception:
        return 0


def reset_for_testing():
    """Pone el contador a 0. Solo para pruebas."""
    r = _get_redis()
    r.set(SEMAPHORE_KEY, 0)
    return 0


def reset_semaphore():
    """
    Resetea el semáforo a 0. Usar cuando workers murieron sin llamar release()
    (contador desincronizado). Llamar desde management command o cron cuando
    no haya tareas reporter activas (ej. celery inspect active).
    Returns:
        int: valor del contador antes del reset.
    """
    r = _get_redis()
    prev = int(r.get(SEMAPHORE_KEY) or 0)
    r.set(SEMAPHORE_KEY, 0)
    if prev > 0:
        logger.warning(f"Selenium semaphore reset (previous count={prev})")
    return prev


# -----------------------------------------------------------------------------
# Lock por rango (evitar doble procesamiento)
# -----------------------------------------------------------------------------

RANGE_LOCK_PREFIX = 'reporter:range:lock:'
RANGE_LOCK_TTL = 3000  # 50 min en segundos


def range_lock_key(run_id, user_id, range_start):
    return f"{RANGE_LOCK_PREFIX}{run_id}:{user_id}:{range_start}"


def acquire_range_lock(run_id, user_id, range_start, task_id, ttl_seconds=None):
    """
    Intenta adquirir el lock para el rango. Solo un worker puede procesarlo.
    Returns:
        True si se adquirió el lock, False si otro worker lo tiene.
    """
    r = _get_redis()
    key = range_lock_key(run_id, user_id, range_start)
    ttl = ttl_seconds or RANGE_LOCK_TTL
    acquired = r.set(key, task_id, nx=True, ex=ttl)
    if acquired:
        logger.debug(f"Range lock acquired: run={run_id} user={user_id} range_start={range_start}")
    return bool(acquired)


def release_range_lock(run_id, user_id, range_start):
    """Libera el lock del rango."""
    r = _get_redis()
    key = range_lock_key(run_id, user_id, range_start)
    r.delete(key)
    logger.debug(f"Range lock released: run={run_id} user={user_id} range_start={range_start}")
