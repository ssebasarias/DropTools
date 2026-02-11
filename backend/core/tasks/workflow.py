"""
Tareas de workflow para ejecución de reportes
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from celery import group
import time

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
        from ..models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ValueError(f"Usuario con ID {user_id} no existe")
        
        if not user.dropi_email or not user.dropi_password:
            raise ValueError(f"Usuario {user_id} no tiene credenciales Dropi configuradas")
        
        # Importar configuración de Docker
        from ..reporter_bot.docker_config import get_download_dir
        
        # Obtener directorio de descarga explícito (base, sin user_id aun, UnifiedReporter lo maneja o se lo pasamos completo)
        download_dir = get_download_dir()  # Esto retorna BASE/results/downloads y asegura que existe
        
        logger.info(f"   📂 Directorio de descargas configurado: {download_dir}")
        
        # Config reporter: una sola fuente en docker_config (Docker=chrome,firefox / local=edge,chrome,firefox)
        from ..reporter_bot.docker_config import get_reporter_browser_order
        logger.info(f"   🌐 Orden de navegadores: {get_reporter_browser_order()}")
        
        # Pasar logger con recursos (CPU/RAM) en cada mensaje para ver picos de consumo
        from ..reporter_bot.resource_logger import ResourceLogger
        from ..reporter_bot.unified_reporter import UnifiedReporter
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
        from ..models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ValueError(f"Usuario con ID {user_id} no existe")
        
        if not user.dropi_email or not user.dropi_password:
            raise ValueError(f"Usuario {user_id} no tiene credenciales Dropi configuradas")
        
        # Crear orquestador con credenciales y modo de prueba (logger para ver mensajes en celery_worker)
        from ..reporter_bot.unified_reporter import UnifiedReporter
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
    logger.info(f"🚀 Iniciando {len(user_ids)} workflows en paralelo")
    
    # Crear grupo de tareas
    # Usar import absoluto para evitar circular
    from core.tasks.workflow import execute_workflow_task
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
