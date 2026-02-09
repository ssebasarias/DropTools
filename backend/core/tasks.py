"""
Tareas asíncronas de Celery para DropTools
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import time
import sys
import os

# Importar al nivel del módulo para evitar problemas en workers
# El PYTHONPATH ya está configurado en docker-compose.yml
# Importar al nivel del módulo para evitar problemas en workers
# El PYTHONPATH ya está configurado en docker-compose.yml
from core.reporter_bot.unified_reporter import UnifiedReporter
from core.reporter_bot.resource_logger import ResourceLogger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def execute_workflow_task(self, user_id):
    """
    Ejecuta el workflow completo de reportes para un usuario
    
    Args:
        user_id: ID del usuario en la tabla users
    
    Returns:
        dict con resultado de la ejecución
    """
    logger.info(f"🚀 Iniciando workflow para usuario {user_id}")
    logger.info(f"   Task ID: {self.request.id}")
    logger.info(f"   Worker: {self.request.hostname}")
    
    try:
        # Obtener credenciales del usuario
        from core.models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ValueError(f"Usuario con ID {user_id} no existe")
        
        if not user.dropi_email or not user.dropi_password:
            raise ValueError(f"Usuario {user_id} no tiene credenciales Dropi configuradas")
        
        # Importar configuración de Docker
        from core.reporter_bot.docker_config import get_download_dir
        
        # Obtener directorio de descarga explícito (base, sin user_id aun, UnifiedReporter lo maneja o se lo pasamos completo)
        # UnifiedReporter espera el dir base y él le añade el user_id internamente, o usamos el base.
        # Revisando UnifiedReporter: self.driver_manager... download_dir=self.download_dir
        # Revisando Downloader: self.user_download_dir = self.download_dir_base / str(self.user_id)
        # Pasemos el BASE para que sea consistente.
        
        download_dir = get_download_dir() # Esto retorna BASE/results/downloads y asegura que existe
        
        logger.info(f"   📂 Directorio de descargas configurado: {download_dir}")
        
        # Config reporter: una sola fuente en docker_config (Docker=chrome,firefox / local=edge,chrome,firefox)
        from core.reporter_bot.docker_config import get_reporter_browser_order
        logger.info(f"   🌐 Orden de navegadores: {get_reporter_browser_order()}")
        
        # Pasar logger con recursos (CPU/RAM) en cada mensaje para ver picos de consumo
        reporter_logger = ResourceLogger(logger)
        unified_reporter = UnifiedReporter(
            user_id=user_id,
            headless=True,
            browser='edge',
            download_dir=str(download_dir),
            browser_priority=None,  # UnifiedReporter usa get_reporter_browser_order() según entorno
            logger=reporter_logger,
        )
        
        # Ejecutar workflow
        logger.info(f"   Ejecutando workflow unificado...")
        stats = unified_reporter.run()
        
        # Verificar éxito basado en stats
        # Consideramos éxito si el downloader funcionó, ya que el resto depende de si hay datos
        # Downloader es el paso crítico que suele fallar por bloqueos
        success = stats.get('downloader', {}).get('success', False) if stats else False
        
        if success:
            logger.info(f"✅ Workflow completado exitosamente para usuario {user_id}")
            return {
                'success': True,
                'user_id': user_id,
                'task_id': self.request.id,
                'message': 'Workflow completado exitosamente'
            }
        else:
            logger.error(f"❌ Workflow falló para usuario {user_id}")
            return {
                'success': False,
                'user_id': user_id,
                'task_id': self.request.id,
                'message': 'Workflow falló durante la ejecución'
            }
            
    except Exception as e:
        logger.error(f"❌ Error en workflow para usuario {user_id}: {str(e)}")
        logger.exception(e)
        
        # Reintentar en 5 minutos
        try:
            raise self.retry(exc=e, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error(f"❌ Máximo de reintentos alcanzado para usuario {user_id}")
            return {
                'success': False,
                'user_id': user_id,
                'task_id': self.request.id,
                'message': f'Error: {str(e)}',
                'max_retries_exceeded': True
            }


@shared_task
def test_celery_task(message="Hello from Celery!"):
    """
    Tarea de prueba simple para verificar que Celery funciona
    """
    logger.info(f"📨 Tarea de prueba ejecutada: {message}")
    time.sleep(2)  # Simular trabajo
    logger.info(f"✅ Tarea de prueba completada")
    return {
        'success': True,
        'message': message,
        'timestamp': time.time()
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def execute_workflow_task_test(self, user_id):
    """
    Ejecuta el workflow en modo de prueba (se detiene después de navegar a órdenes)
    
    Args:
        user_id: ID del usuario en la tabla users
    
    Returns:
        dict con resultado de la ejecución
    """
    logger.info(f"🧪 Iniciando workflow de PRUEBA para usuario {user_id}")
    logger.info(f"   Task ID: {self.request.id}")
    logger.info(f"   Worker: {self.request.hostname}")
    
    try:
        # Obtener credenciales del usuario
        from core.models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ValueError(f"Usuario con ID {user_id} no existe")
        
        if not user.dropi_email or not user.dropi_password:
            raise ValueError(f"Usuario {user_id} no tiene credenciales Dropi configuradas")
        
        # Crear orquestador con credenciales y modo de prueba (logger para ver mensajes en celery_worker)
        unified_reporter = UnifiedReporter(
            user_id=user_id,
            headless=True,
            browser='chrome',
            logger=logger,
        )
        
        # Ejecutar workflow
        # Nota: UnifiedReporter no tiene un 'test_mode' explícito en run(),
        # pero para fines de prueba ejecutamos el flujo completo y verificamos que no falle violentamente.
        # Si se requiere un modo dry-run real, habría que implementarlo en UnifiedReporter.
        logger.info(f"   Ejecutando workflow de prueba...")
        stats = unified_reporter.run()
        success = stats.get('downloader', {}).get('success', False) if stats else False
        
        if success:
            logger.info(f"✅ Workflow de prueba completado exitosamente para usuario {user_id}")
            return {
                'success': True,
                'user_id': user_id,
                'task_id': self.request.id,
                'message': 'Workflow de prueba completado: navegación a órdenes exitosa'
            }
        else:
            logger.error(f"❌ Workflow de prueba falló para usuario {user_id}")
            return {
                'success': False,
                'user_id': user_id,
                'task_id': self.request.id,
                'message': 'Workflow de prueba falló durante la ejecución'
            }
            
    except Exception as e:
        logger.error(f"❌ Error en workflow de prueba para usuario {user_id}: {str(e)}")
        logger.exception(e)
        
        # Reintentar en 5 minutos
        try:
            raise self.retry(exc=e, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error(f"❌ Máximo de reintentos alcanzado para usuario {user_id}")
            return {
                'success': False,
                'user_id': user_id,
                'task_id': self.request.id,
                'message': f'Error: {str(e)}',
                'max_retries_exceeded': True
            }


@shared_task(bind=True)
def execute_multiple_workflows(self, user_ids):
    """
    Ejecuta workflows para múltiples usuarios en paralelo
    
    Args:
        user_ids: Lista de IDs de usuarios
    
    Returns:
        dict con resultados de todas las ejecuciones
    """
    from celery import group
    
    logger.info(f"🚀 Iniciando {len(user_ids)} workflows en paralelo")
    
    # Crear grupo de tareas
    job = group(execute_workflow_task.s(user_id) for user_id in user_ids)
    
    # Ejecutar en paralelo
    result = job.apply_async()
    
    logger.info(f"✅ {len(user_ids)} workflows encolados")
    
    return {
        'success': True,
        'total_workflows': len(user_ids),
        'user_ids': user_ids,
        'group_id': result.id
    }


# -----------------------------------------------------------------------------
# Reporter slot system: process_slot_task, download_compare_task, report_range_task
# -----------------------------------------------------------------------------

@shared_task(bind=True)
def process_slot_task(self, slot_time_iso=None):
    """
    Disparado por Celery Beat cada hora. Crea ReporterRun para ese slot,
    lista usuarios con reserva en esa hora y encola download_compare_task por cada uno.
    slot_time_iso: datetime en ISO (ej. "2025-01-31T10:00:00"). Si None, usa hora actual redondeada a la hora.
    """
    from django.utils import timezone as tz
    from datetime import datetime
    from core.models import ReporterHourSlot, ReporterReservation, ReporterRun, ReporterRunUser

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
        download_compare_task.delay(uid, run.id)

    logger.info(f"   Enqueued {len(user_ids)} download_compare_task for run_id={run.id}")
    return {'success': True, 'run_id': run.id, 'user_count': len(user_ids)}


def _run_capacity_aware_key(run_id):
    return f"reporter:run:capacity_aware:{run_id}"


def _is_run_capacity_aware(run_id):
    """Solo DEV: run creado por process_slot_task_dev."""
    try:
        from core.reporter_bot.selenium_semaphore import _get_redis
        r = _get_redis()
        return bool(r.get(_run_capacity_aware_key(run_id)))
    except Exception:
        return False


@shared_task(bind=True)
def process_slot_task_dev(self, slot_time_iso=None):
    """
    DEV: Igual que process_slot_task pero respeta capacidad por peso.
    Solo encola usuarios que caben (suma de calculated_weight <= slot.capacity_points).
    Los que no caben quedan DC_PENDING; enqueue_next_pending_for_run los encola al liberarse peso.
    """
    from django.utils import timezone as tz
    from datetime import datetime
    from core.models import ReporterHourSlot, ReporterReservation, ReporterRun, ReporterRunUser
    from core.reporter_bot.selenium_semaphore import _get_redis

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
    logger.info(f"⏰ process_slot_task_dev: slot_time={slot_time_iso} hour={hour} (capacity-aware)")

    slot = ReporterHourSlot.objects.filter(hour=hour).first()
    if not slot:
        logger.warning(f"No ReporterHourSlot for hour={hour}")
        return {'success': False, 'error': f'No slot for hour {hour}'}

    capacity = getattr(slot, 'capacity_points', 6) or 6
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
        return {'success': True, 'run_id': run.id, 'user_count': 0, 'enqueued': 0, 'pending_by_capacity': 0}

    used = 0
    to_enqueue = []
    for res in reservations:
        w = res.calculated_weight
        if used + w <= capacity:
            to_enqueue.append(res.user_id)
            used += w
        else:
            logger.info(f"   User {res.user_id} (weight={w}) no cabe: used={used} cap={capacity}")

    run = ReporterRun.objects.create(
        slot=slot,
        scheduled_at=slot_dt,
        status=ReporterRun.STATUS_RUNNING,
        started_at=tz.now()
    )
    r = _get_redis()
    r.set(_run_capacity_aware_key(run.id), '1', ex=86400)

    all_user_ids = [res.user_id for res in reservations]
    for uid in all_user_ids:
        ReporterRunUser.objects.create(
            run=run,
            user_id=uid,
            download_compare_status=ReporterRunUser.DC_PENDING
        )
    for uid in to_enqueue:
        download_compare_task.delay(uid, run.id)

    pending_count = len(all_user_ids) - len(to_enqueue)
    logger.info(f"   Enqueued {len(to_enqueue)} download_compare_task, {pending_count} pendientes por capacidad")
    return {
        'success': True,
        'run_id': run.id,
        'user_count': len(all_user_ids),
        'enqueued': len(to_enqueue),
        'pending_by_capacity': pending_count,
    }


@shared_task
def enqueue_next_pending_for_run(run_id):
    """
    DEV: Tras liberar peso (DC completado o todos los rangos de un usuario),
    encola el siguiente DC_PENDING que quepa en capacidad.
    """
    from core.models import ReporterRun, ReporterRunUser, ReporterReservation

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
    for ru in pending:
        w = weights.get(ru.user_id, 1)
        if used + w <= capacity:
            download_compare_task.delay(ru.user_id, run_id)
            logger.info(f"   Encolado siguiente por capacidad: user_id={ru.user_id} run_id={run_id}")
            break


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def download_compare_task(self, user_id, run_id):
    """
    Adquiere slot Selenium, ejecuta Download+Compare para el usuario,
    libera slot, crea rangos en BD y encola report_range_task por cada rango.
    """
    from django.utils import timezone as tz
    from core.models import User, ReporterRun, ReporterRunUser, OrderMovementReport, ReportBatch
    from core.reporter_bot.unified_reporter import UnifiedReporter
    from core.reporter_bot.resource_logger import ResourceLogger
    from core.reporter_bot.docker_config import get_download_dir
    from core.reporter_bot.selenium_semaphore import acquire, release
    from core.reporter_range_service import create_ranges_for_user

    logger.info(f"📥 download_compare_task: user_id={user_id} run_id={run_id}")
    run_user = ReporterRunUser.objects.filter(run_id=run_id, user_id=user_id).first()
    if not run_user:
        logger.error(f"ReporterRunUser not found for run={run_id} user={user_id}")
        return {'success': False, 'error': 'RunUser not found'}

    if not acquire(timeout_seconds=3300):
        logger.warning("Selenium semaphore acquire timeout, retrying...")
        raise self.retry(countdown=120)

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
            return {'success': True, 'run_id': run_id, 'user_id': user_id, 'total_detected': 0}

        ranges_created = create_ranges_for_user(run_id, user_id, total_detected)
        run_user.total_ranges = len(ranges_created)
        run_user.save(update_fields=['total_ranges', 'updated_at'])

        for (rs, re) in ranges_created:
            report_range_task.delay(run_id, user_id, rs, re)

        logger.info(f"   Enqueued {len(ranges_created)} report_range_task for user_id={user_id}")
        if _is_run_capacity_aware(run_id):
            enqueue_next_pending_for_run.delay(run_id)
        return {'success': True, 'run_id': run_id, 'user_id': user_id, 'total_detected': total_detected, 'ranges': len(ranges_created)}
    except Exception as e:
        release()
        run_user.download_compare_status = ReporterRunUser.DC_FAILED
        run_user.save(update_fields=['download_compare_status', 'updated_at'])
        logger.exception(f"download_compare_task failed: {e}")
        raise self.retry(exc=e, countdown=120)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def report_range_task(self, run_id, user_id, range_start, range_end):
    """
    Adquiere slot Selenium y lock por rango, ejecuta Reporter solo para [range_start, range_end],
    actualiza ReporterRange y ReporterRunUser.ranges_completed, libera lock y slot.
    """
    from django.utils import timezone as tz
    from django.db import transaction
    from django.db.models import F
    from core.models import ReporterRun, ReporterRange, ReporterRunUser, User
    from core.reporter_bot.unified_reporter import UnifiedReporter
    from core.reporter_bot.resource_logger import ResourceLogger
    from core.reporter_bot.docker_config import get_download_dir
    from core.reporter_bot.selenium_semaphore import (
        acquire,
        release,
        acquire_range_lock,
        release_range_lock,
    )

    task_id = self.request.id
    logger.info(f"📋 report_range_task: run_id={run_id} user_id={user_id} range=[{range_start},{range_end}]")

    if not acquire(timeout_seconds=3300):
        raise self.retry(countdown=60)

    if not acquire_range_lock(run_id, user_id, range_start, task_id):
        release()
        logger.warning(f"Range lock not acquired for run={run_id} user={user_id} range_start={range_start}, skipping")
        return {'success': False, 'skipped': True, 'reason': 'lock_not_acquired'}

    range_obj = ReporterRange.objects.filter(
        run_id=run_id, user_id=user_id, range_start=range_start
    ).first()
    if not range_obj:
        release_range_lock(run_id, user_id, range_start)
        release()
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
            release()
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
        procesados = (stats.get('reporter') or {}).get('procesados', 0)
        logger.info(f"   Range [{range_start},{range_end}] completed: {procesados} reportados")
        run_user_after = ReporterRunUser.objects.filter(run_id=run_id, user_id=user_id).first()
        if run_user_after and run_user_after.total_ranges and run_user_after.ranges_completed >= run_user_after.total_ranges:
            from core.tasks import _is_run_capacity_aware, enqueue_next_pending_for_run
            if _is_run_capacity_aware(run_id):
                enqueue_next_pending_for_run.delay(run_id)
        return {'success': True, 'run_id': run_id, 'user_id': user_id, 'range_start': range_start, 'procesados': procesados}
    except Exception as e:
        release()
        release_range_lock(run_id, user_id, range_start)
        range_obj.status = ReporterRange.STATUS_FAILED
        range_obj.save(update_fields=['status'])
        logger.exception(f"report_range_task failed: {e}")
        raise self.retry(exc=e, countdown=60)
