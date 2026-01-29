"""
Configuración de Celery para Dahell Intelligence
"""
import os
from celery import Celery

# Configurar Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dahell_backend.settings')

# Crear aplicación Celery
app = Celery('dahell')

# Configuración desde Django settings con namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# Configuración adicional
app.conf.update(
    # Broker y Backend
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    
    # Serialización
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='America/Bogota',
    enable_utc=True,
    
    # Concurrencia
    worker_concurrency=4,  # 4 tareas simultáneas por worker
    worker_prefetch_multiplier=1,  # Tomar 1 tarea a la vez
    
    # Timeouts
    task_time_limit=3600,  # 1 hora máximo por tarea
    task_soft_time_limit=3300,  # Advertencia a los 55 minutos
    
    # Resultados
    result_expires=3600,  # Resultados expiran en 1 hora
    
    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de prueba para verificar que Celery funciona"""
    print(f'Request: {self.request!r}')
