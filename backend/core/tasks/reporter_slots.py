"""
Tareas del sistema de reporter slots (reservas por hora, rangos, scheduler)
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone as tz
from datetime import datetime

logger = get_task_logger(__name__)


def _run_capacity_aware_key(run_id):
    return f"reporter:run:capacity_aware:{run_id}"


def _is_run_capacity_aware(run_id):
    """Solo DEV: run creado por process_slot_task_dev."""
    try:
        from ..reporter_bot.selenium_semaphore import _get_redis
        r = _get_redis()
        return bool(r.get(_run_capacity_aware_key(run_id)))
    except Exception:
        return False


def _is_run_user_fully_done(run_user):
    """
    Determina si un ReporterRunUser ya terminó su participación en la run.
    """
    from ..models import ReporterRunUser

    if run_user.download_compare_status in (ReporterRunUser.DC_PENDING, ReporterRunUser.DC_RUNNING):
        return False
    if run_user.download_compare_status == ReporterRunUser.DC_FAILED:
        return True
    total_ranges = run_user.total_ranges or 0
    return run_user.ranges_completed >= total_ranges


def _finalize_run_if_done(run_id):
    """
    Cierra la run cuando todos los usuarios terminaron:
    - completed: sin fallos
    - failed: al menos un fallo en download/compare o rangos
    """
    from ..models import ReporterRun, ReporterRunUser, ReporterRange

    run = ReporterRun.objects.filter(id=run_id).first()
    if not run:
        return None
    if run.status in (ReporterRun.STATUS_COMPLETED, ReporterRun.STATUS_FAILED):
        return run.status

    run_users = list(ReporterRunUser.objects.filter(run_id=run_id))
    if not run_users:
        return None

    if not all(_is_run_user_fully_done(ru) for ru in run_users):
        return None

    has_failures = any(ru.download_compare_status == ReporterRunUser.DC_FAILED for ru in run_users)
    if not has_failures:
        has_failures = ReporterRange.objects.filter(
            run_id=run_id,
            status=ReporterRange.STATUS_FAILED
        ).exists()

    run.status = ReporterRun.STATUS_FAILED if has_failures else ReporterRun.STATUS_COMPLETED
    run.finished_at = tz.now()
    run.save(update_fields=['status', 'finished_at'])
    logger.info(f"Run {run_id} finalized with status={run.status}")
    return run.status


@shared_task(bind=True)
def process_slot_task(self, slot_time_iso=None):
    """
    Disparado por Celery Beat cada hora. Crea ReporterRun para ese slot,
    lista usuarios con reserva en esa hora y encola download_compare_task por cada uno.
    slot_time_iso: datetime en ISO (ej. "2025-01-31T10:00:00"). Si None, usa hora actual redondeada a la hora.
    """
    from ..models import ReporterHourSlot, ReporterReservation, ReporterRun, ReporterRunUser
    # Importar download_compare_task usando import absoluto para evitar circular
    from core.tasks.reporter_slots import download_compare_task as download_compare_task_func

    if slot_time_iso is None:
        now = tz.now()
        slot_dt = now.replace(minute=0, second=0, microsecond=0)
        slot_time_iso = slot_dt.isoformat()
    else:
        try:
            if isinstance(slot_time_iso, str):
                slot_dt = datetime.fromisoformat(slot_time_iso.replace('Z', '+00:00'))
                if slot_dt.tzinfo is None:
                    slot_dt = tz.make_aware(slot_dt, tz.get_current_timezone())
            else:
                slot_dt = slot_time_iso
        except Exception as e:
            logger.error(f"Invalid slot_time_iso: {slot_time_iso}: {e}")
            return {'success': False, 'error': str(e)}
    hour = slot_dt.hour
    logger.info(f"⏰ process_slot_task: slot_time={slot_time_iso} hour={hour}")

    slot = ReporterHourSlot.objects.filter(hour=hour).first()
    if not slot:
        logger.warning(f"No ReporterHourSlot for hour={hour}")
        return {'success': False, 'error': f'No slot for hour {hour}'}

    run = ReporterRun.objects.create(
        slot=slot,
        scheduled_at=slot_dt,
        status=ReporterRun.STATUS_RUNNING,
        started_at=tz.now()
    )
    users = ReporterReservation.objects.filter(slot=slot).values_list('user_id', flat=True)
    user_ids = list(users)
    if not user_ids:
        logger.info(f"   No users reserved for slot {hour:02d}:00")
        run.status = ReporterRun.STATUS_COMPLETED
        run.finished_at = tz.now()
        run.save()
        return {'success': True, 'run_id': run.id, 'user_count': 0}

    for uid in user_ids:
        ReporterRunUser.objects.create(
            run=run,
            user_id=uid,
            download_compare_status=ReporterRunUser.DC_PENDING
        )
        download_compare_task_func.delay(uid, run.id)

    logger.info(f"   Enqueued {len(user_ids)} download_compare_task for run_id={run.id}")
    return {'success': True, 'run_id': run.id, 'user_count': len(user_ids)}


@shared_task(bind=True)
def process_slot_task_dev(self, slot_time_iso=None):
    """
    Procesa un slot horario: crea run y encola download_compare_task para todos los usuarios asignados.
    
    Con el nuevo sistema de límites por peso, todos los usuarios asignados al slot se procesan
    (hasta 6 workers en paralelo según max_active_selenium).
    """
    from ..models import ReporterHourSlot, ReporterReservation, ReporterRun, ReporterRunUser
    from ..reporter_bot.selenium_semaphore import _get_redis
    # Importar download_compare_task usando import absoluto para evitar circular
    from core.tasks.reporter_slots import download_compare_task as download_compare_task_func

    if slot_time_iso is None:
        now = tz.now()
        slot_dt = now.replace(minute=0, second=0, microsecond=0)
        slot_time_iso = slot_dt.isoformat()
    else:
        try:
            if isinstance(slot_time_iso, str):
                slot_dt = datetime.fromisoformat(slot_time_iso.replace('Z', '+00:00'))
                if slot_dt.tzinfo is None:
                    slot_dt = tz.make_aware(slot_dt, tz.get_current_timezone())
            else:
                slot_dt = slot_time_iso
        except Exception as e:
            logger.error(f"Invalid slot_time_iso: {slot_time_iso}: {e}")
            return {'success': False, 'error': str(e)}
    hour = slot_dt.hour
    logger.info(f"⏰ process_slot_task_dev: slot_time={slot_time_iso} hour={hour} (weight-limits-aware)")

    slot = ReporterHourSlot.objects.filter(hour=hour).first()
    if not slot:
        logger.warning(f"No ReporterHourSlot for hour={hour}")
        return {'success': False, 'error': f'No slot for hour {hour}'}

    reservations = list(
        ReporterReservation.objects.filter(slot=slot).select_related('user').order_by('id')
    )
    if not reservations:
        run = ReporterRun.objects.create(
            slot=slot,
            scheduled_at=slot_dt,
            status=ReporterRun.STATUS_COMPLETED,
            started_at=tz.now(),
            finished_at=tz.now()
        )
        return {'success': True, 'run_id': run.id, 'user_count': 0, 'enqueued': 0}

    # Crear run para este slot
    run = ReporterRun.objects.create(
        slot=slot,
        scheduled_at=slot_dt,
        status=ReporterRun.STATUS_RUNNING,
        started_at=tz.now()
    )
    r = _get_redis()
    r.set(_run_capacity_aware_key(run.id), '1', ex=86400)

    # Crear ReporterRunUser para todos los usuarios asignados al slot
    all_user_ids = [res.user_id for res in reservations]
    for uid in all_user_ids:
        ReporterRunUser.objects.create(
            run=run,
            user_id=uid,
            download_compare_status=ReporterRunUser.DC_PENDING
        )
    
    # Encolar download_compare_task para todos los usuarios
    # Los workers (hasta 6 según max_active_selenium) procesarán en paralelo
    # Usar import absoluto para evitar import circular
    from core.tasks.reporter_slots import download_compare_task as download_compare_task_func
    for uid in all_user_ids:
        download_compare_task_func.delay(uid, run.id)

    logger.info(f"   Enqueued {len(all_user_ids)} download_compare_task for {len(all_user_ids)} users")
    return {
        'success': True,
        'run_id': run.id,
        'user_count': len(all_user_ids),
        'enqueued': len(all_user_ids),
    }


@shared_task
def enqueue_next_pending_for_run(run_id):
    """
    DEV: Tras liberar peso (DC completado o todos los rangos de un usuario),
    encola el siguiente DC_PENDING que quepa en capacidad.
    (Mantenido por compatibilidad, pero ya no se usa con el nuevo sistema)
    """
    from ..models import ReporterRun, ReporterRunUser, ReporterReservation
    # Importar download_compare_task usando import absoluto para evitar circular
    from core.tasks.reporter_slots import download_compare_task as download_compare_task_func

    if not _is_run_capacity_aware(run_id):
        return
    run = ReporterRun.objects.filter(id=run_id).select_related('slot').first()
    if not run or not run.slot:
        return
    capacity = getattr(run.slot, 'capacity_points', 6) or 6
    run_users = list(ReporterRunUser.objects.filter(run_id=run_id))
    if not run_users:
        return
    weights = dict(
        ReporterReservation.objects.filter(slot=run.slot, user_id__in=[ru.user_id for ru in run_users]).values_list('user_id', 'calculated_weight')
    )
    used = 0
    for ru in run_users:
        w = weights.get(ru.user_id, 1)
        if ru.download_compare_status == ReporterRunUser.DC_RUNNING:
            used += w
        elif ru.download_compare_status == ReporterRunUser.DC_COMPLETED and ru.ranges_completed < ru.total_ranges:
            used += w
    pending = [ru for ru in run_users if ru.download_compare_status == ReporterRunUser.DC_PENDING]
    pending.sort(key=lambda x: x.id)
    # Usar import absoluto para evitar import circular
    from core.tasks.reporter_slots import download_compare_task as download_compare_task_func
    for ru in pending:
        w = weights.get(ru.user_id, 1)
        if used + w <= capacity:
            download_compare_task_func.delay(ru.user_id, run_id)
            logger.info(f"   Encolado siguiente por capacidad: user_id={ru.user_id} run_id={run_id}")
            break


@shared_task
def enqueue_next_range_priority_aware(run_id):
    """
    Busca el siguiente rango pendiente priorizando usuarios por peso (3 → 2 → 1).
    
    Cuando un worker termina con un usuario pequeño, esta función busca rangos pendientes
    de usuarios grandes para que el worker los ayude.
    
    Args:
        run_id: ID de la ReporterRun
    """
    from ..models import ReporterRun, ReporterRunUser, ReporterReservation, ReporterRange
    from ..reporter_bot.selenium_semaphore import acquire_range_lock
    # Importar report_range_task usando import absoluto para evitar circular
    from core.tasks.reporter_slots import report_range_task as report_range_task_func

    if not _is_run_capacity_aware(run_id):
        return
    
    run = ReporterRun.objects.filter(id=run_id).select_related('slot').first()
    if not run:
        return
    
    # Obtener todos los usuarios de la run con rangos pendientes
    run_users = list(
        ReporterRunUser.objects.filter(
            run_id=run_id
        ).filter(
            download_compare_status=ReporterRunUser.DC_COMPLETED
        ).exclude(
            total_ranges=0
        )
    )
    
    if not run_users:
        return
    
    # Obtener pesos de usuarios desde ReporterReservation
    user_ids = [ru.user_id for ru in run_users]
    weights = dict(
        ReporterReservation.objects.filter(
            slot=run.slot,
            user_id__in=user_ids
        ).values_list('user_id', 'calculated_weight')
    )
    
    # Filtrar usuarios que tienen rangos pendientes
    users_with_pending_ranges = []
    for ru in run_users:
        if ru.ranges_completed < ru.total_ranges:
            weight = weights.get(ru.user_id, 1)
            users_with_pending_ranges.append((ru.user_id, weight))
    
    if not users_with_pending_ranges:
        return
    
    # Ordenar por peso descendente (3 → 2 → 1)
    users_with_pending_ranges.sort(key=lambda x: x[1], reverse=True)
    
    # Buscar primer rango disponible, priorizando por peso
    for user_id, weight in users_with_pending_ranges:
        # Buscar primer rango pendiente de este usuario
        pending_range = ReporterRange.objects.filter(
            run_id=run_id,
            user_id=user_id,
            status=ReporterRange.STATUS_PENDING
        ).order_by('range_start').first()
        
        if not pending_range:
            continue
        
        # Intentar adquirir lock del rango
        # Usar un task_id temporal para el lock (se actualizará cuando report_range_task lo tome)
        task_id = f"priority_aware_{run_id}_{user_id}_{pending_range.range_start}"
        if acquire_range_lock(run_id, user_id, pending_range.range_start, task_id):
            # Lock adquirido, encolar report_range_task
            report_range_task_func.delay(run_id, user_id, pending_range.range_start, pending_range.range_end)
            logger.info(
                f"   Encolado rango prioritario: run_id={run_id} user_id={user_id} "
                f"weight={weight} range=[{pending_range.range_start},{pending_range.range_end}]"
            )
            return
    
    # No se encontró ningún rango disponible (todos están siendo procesados)
    logger.debug(f"   No hay rangos disponibles para asignación prioritaria en run_id={run_id}")


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def download_compare_task(self, user_id, run_id):
    """
    Adquiere slot Selenium, ejecuta Download+Compare para el usuario,
    libera slot, crea rangos en BD y encola report_range_task por cada rango.
    """
    from ..models import User, ReporterRun, ReporterRunUser, OrderMovementReport, ReportBatch
    from ..reporter_bot.unified_reporter import UnifiedReporter
    from ..reporter_bot.resource_logger import ResourceLogger
    from ..reporter_bot.docker_config import get_download_dir
    from ..reporter_bot.selenium_semaphore import acquire, release
    from ..reporter_range_service import create_ranges_for_user
    # Importar funciones usando imports absolutos para evitar circular
    from core.tasks.reporter_slots import report_range_task as report_range_task_func
    from core.tasks.reporter_slots import enqueue_next_pending_for_run, _is_run_capacity_aware

    logger.info(f"📥 download_compare_task: user_id={user_id} run_id={run_id}")
    run_user = ReporterRunUser.objects.filter(run_id=run_id, user_id=user_id).first()
    if not run_user:
        logger.error(f"ReporterRunUser not found for run={run_id} user={user_id}")
        return {'success': False, 'error': 'RunUser not found'}

    if not acquire(timeout_seconds=3300):
        logger.warning("Selenium semaphore acquire timeout, retrying...")
        raise self.retry(countdown=120)

    released = False
    try:
        run_user.download_compare_status = ReporterRunUser.DC_RUNNING
        run_user.save(update_fields=['download_compare_status', 'updated_at'])

        user = User.objects.filter(id=user_id).first()
        if not user or not user.dropi_email or not user.dropi_password:
            run_user.download_compare_status = ReporterRunUser.DC_FAILED
            run_user.save(update_fields=['download_compare_status', 'updated_at'])
            return {'success': False, 'error': 'User or credentials missing'}

        download_dir = get_download_dir()
        reporter_logger = ResourceLogger(logger)
        unified = UnifiedReporter(
            user_id=user_id,
            headless=True,
            download_dir=str(download_dir),
            browser='edge',
            browser_priority=None,
            logger=reporter_logger,
        )
        stats = unified.run_download_compare_only()
        release()
        released = True

        total_detected = (stats.get('comparer') or {}).get('total_detected', 0)
        run_user.download_compare_status = ReporterRunUser.DC_COMPLETED
        run_user.download_compare_completed_at = tz.now()
        run_user.total_pending_orders = total_detected
        run_user.save(update_fields=[
            'download_compare_status', 'download_compare_completed_at',
            'total_pending_orders', 'updated_at'
        ])

        if total_detected <= 0:
            run_user.total_ranges = 0
            run_user.save(update_fields=['total_ranges', 'updated_at'])
            _finalize_run_if_done(run_id)
            return {'success': True, 'run_id': run_id, 'user_id': user_id, 'total_detected': 0}

        ranges_created = create_ranges_for_user(run_id, user_id, total_detected)
        run_user.total_ranges = len(ranges_created)
        run_user.save(update_fields=['total_ranges', 'updated_at'])

        # Usar import absoluto para evitar import circular
        from core.tasks.reporter_slots import report_range_task as report_range_task_func
        for (rs, re) in ranges_created:
            report_range_task_func.delay(run_id, user_id, rs, re)

        logger.info(
            f"   Enqueued {len(ranges_created)} report_range_task for user_id={user_id}. "
            f"Up to 6 workers will process ranges in parallel (same account, same IP)."
        )
        if _is_run_capacity_aware(run_id):
            enqueue_next_pending_for_run.delay(run_id)
        _finalize_run_if_done(run_id)
        return {'success': True, 'run_id': run_id, 'user_id': user_id, 'total_detected': total_detected, 'ranges': len(ranges_created)}
    except Exception as e:
        run_user.download_compare_status = ReporterRunUser.DC_FAILED
        run_user.save(update_fields=['download_compare_status', 'updated_at'])
        _finalize_run_if_done(run_id)
        logger.exception(f"download_compare_task failed: {e}")
        raise self.retry(exc=e, countdown=120)
    finally:
        if not released:
            release()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def report_range_task(self, run_id, user_id, range_start, range_end):
    """
    Adquiere slot Selenium y lock por rango, ejecuta Reporter solo para [range_start, range_end],
    actualiza ReporterRange y ReporterRunUser.ranges_completed, libera lock y slot.
    """
    from django.db import transaction
    from django.db.models import F
    from ..models import ReporterRun, ReporterRange, ReporterRunUser, User
    from ..reporter_bot.unified_reporter import UnifiedReporter
    from ..reporter_bot.resource_logger import ResourceLogger
    from ..reporter_bot.docker_config import get_download_dir
    from ..reporter_bot.selenium_semaphore import (
        acquire,
        release,
        acquire_range_lock,
        release_range_lock,
    )
    # Las funciones _is_run_capacity_aware y enqueue_next_range_priority_aware están en este mismo archivo

    task_id = self.request.id
    worker_name = getattr(self.request, 'hostname', 'unknown')
    logger.info(
        f"📋 report_range_task: run_id={run_id} user_id={user_id} range=[{range_start},{range_end}] "
        f"(worker={worker_name}, same IP as other ranges)"
    )

    if not acquire(timeout_seconds=3300):
        raise self.retry(countdown=60)

    released = False
    lock_acquired = False

    if not acquire_range_lock(run_id, user_id, range_start, task_id):
        release()
        released = True
        logger.warning(f"Range lock not acquired for run={run_id} user={user_id} range_start={range_start}, skipping")
        return {'success': False, 'skipped': True, 'reason': 'lock_not_acquired'}
    lock_acquired = True

    range_obj = ReporterRange.objects.filter(
        run_id=run_id, user_id=user_id, range_start=range_start
    ).first()
    if not range_obj:
        if lock_acquired:
            release_range_lock(run_id, user_id, range_start)
            lock_acquired = False
        release()
        released = True
        return {'success': False, 'error': 'Range not found'}

    try:
        with transaction.atomic():
            range_obj.status = ReporterRange.STATUS_LOCKED
            range_obj.locked_at = tz.now()
            range_obj.locked_by = task_id
            range_obj.save(update_fields=['status', 'locked_at', 'locked_by'])
        range_obj.status = ReporterRange.STATUS_PROCESSING
        range_obj.save(update_fields=['status'])

        user = User.objects.filter(id=user_id).first()
        if not user or not user.dropi_email or not user.dropi_password:
            range_obj.status = ReporterRange.STATUS_FAILED
            range_obj.save(update_fields=['status'])
            release_range_lock(run_id, user_id, range_start)
            lock_acquired = False
            release()
            released = True
            _finalize_run_if_done(run_id)
            return {'success': False, 'error': 'User or credentials missing'}

        download_dir = get_download_dir()
        reporter_logger = ResourceLogger(logger)
        unified = UnifiedReporter(
            user_id=user_id,
            headless=True,
            download_dir=str(download_dir),
            browser='edge',
            browser_priority=None,
            logger=reporter_logger,
        )
        stats = unified.run_report_orders_only(range_start, range_end)
        release()
        released = True

        with transaction.atomic():
            range_obj.status = ReporterRange.STATUS_COMPLETED
            range_obj.completed_at = tz.now()
            range_obj.save(update_fields=['status', 'completed_at'])
            ReporterRunUser.objects.filter(
                run_id=run_id, user_id=user_id
            ).update(
                ranges_completed=F('ranges_completed') + 1,
                updated_at=tz.now()
            )

        release_range_lock(run_id, user_id, range_start)
        lock_acquired = False
        procesados = (stats.get('reporter') or {}).get('procesados', 0)
        logger.info(f"   Range [{range_start},{range_end}] completed: {procesados} reportados")
        
        # Verificar si el usuario tiene más rangos pendientes
        run_user_after = ReporterRunUser.objects.filter(run_id=run_id, user_id=user_id).first()
        if not run_user_after:
            _finalize_run_if_done(run_id)
            return {'success': True, 'run_id': run_id, 'user_id': user_id, 'range_start': range_start, 'procesados': procesados}
        
        # Verificar si el usuario completó todos sus rangos
        if run_user_after.total_ranges and run_user_after.ranges_completed >= run_user_after.total_ranges:
            # Usuario completó todos sus rangos, buscar siguiente rango de usuarios de mayor peso (multi-usuario)
            if _is_run_capacity_aware(run_id):
                enqueue_next_range_priority_aware.delay(run_id)
        # Si el usuario tiene más rangos pendientes: no encolar aquí. Todos los rangos ya fueron
        # encolados en download_compare_task (una tarea por rango). Cualquier worker libre tomará
        # la siguiente tarea de la cola y el trabajo se reparte entre los 6 workers.
        
        _finalize_run_if_done(run_id)
        return {'success': True, 'run_id': run_id, 'user_id': user_id, 'range_start': range_start, 'procesados': procesados}
    except Exception as e:
        if lock_acquired:
            release_range_lock(run_id, user_id, range_start)
            lock_acquired = False
        range_obj.status = ReporterRange.STATUS_FAILED
        range_obj.save(update_fields=['status'])
        _finalize_run_if_done(run_id)
        logger.exception(f"report_range_task failed: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        if not released:
            release()
        if lock_acquired:
            release_range_lock(run_id, user_id, range_start)
