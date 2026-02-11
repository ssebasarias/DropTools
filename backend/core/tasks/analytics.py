"""
Tareas de analytics para cálculo de métricas diarias
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from datetime import timedelta, datetime as dt

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def calculate_daily_analytics(self, target_date_str=None):
    """
    Tarea periódica para calcular métricas analíticas diarias.
    Debe ejecutarse diariamente (recomendado: 2 AM) vía Celery Beat.
    
    Args:
        target_date_str: Fecha objetivo en formato YYYY-MM-DD (default: ayer)
    
    Returns:
        dict con resultado de la ejecución
    """
    logger.info("📊 Iniciando cálculo de métricas analíticas diarias")
    logger.info(f"   Task ID: {self.request.id}")
    logger.info(f"   Worker: {self.request.hostname}")
    
    try:
        from ..models import User
        from ..services.analytics_service import AnalyticsService
        
        # Determinar fecha objetivo
        if target_date_str:
            try:
                target_date = dt.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                logger.error(f"Formato de fecha inválido: {target_date_str}. Use YYYY-MM-DD")
                return {'success': False, 'error': 'Formato de fecha inválido'}
        else:
            # Por defecto, calcular para ayer
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        logger.info(f"   📅 Fecha objetivo: {target_date}")
        
        # Obtener todos los usuarios activos
        users = User.objects.filter(is_active=True)
        total_users = users.count()
        
        logger.info(f"   👥 Procesando {total_users} usuario(s)...")
        
        success_count = 0
        error_count = 0
        errors = []
        
        for user in users:
            try:
                service = AnalyticsService(user)
                results = service.calculate_all_metrics(target_date)
                
                snapshot = results.get('snapshot')
                if snapshot:
                    logger.info(
                        f"   ✅ Usuario {user.username} (ID: {user.id}): "
                        f"{snapshot.total_orders} órdenes, "
                        f"{len(results.get('carriers', []))} transportadoras, "
                        f"{len(results.get('products', []))} productos"
                    )
                else:
                    logger.warning(f"   ⚠️ Usuario {user.username} (ID: {user.id}): Sin datos para fecha {target_date}")
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = f"Usuario {user.id}: {str(e)}"
                errors.append(error_msg)
                logger.exception(f"   ❌ Error calculando métricas para usuario {user.id}: {e}")
                # Continuar con el siguiente usuario sin afectar otros
                continue
        
        # Resumen
        logger.info("=" * 60)
        logger.info(f"📊 Resumen de cálculo de analytics:")
        logger.info(f"   Fecha procesada: {target_date}")
        logger.info(f"   Usuarios procesados exitosamente: {success_count}")
        if error_count > 0:
            logger.warning(f"   Errores: {error_count}")
            for err in errors[:5]:  # Mostrar solo los primeros 5 errores
                logger.warning(f"      - {err}")
        logger.info("=" * 60)
        
        return {
            'success': True,
            'target_date': target_date.isoformat(),
            'total_users': total_users,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10],  # Limitar a 10 errores en la respuesta
        }
        
    except Exception as e:
        logger.exception(f"❌ Error crítico en calculate_daily_analytics: {e}")
        raise self.retry(exc=e, countdown=300)
