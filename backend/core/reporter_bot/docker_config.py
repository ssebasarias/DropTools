"""
Configuración específica para la ejecución en Docker/Celery/Redis.
Este archivo centraliza las rutas y configuraciones necesarias para que el bot
funcione correctamente dentro del contenedor, replicando el comportamiento local.
"""

import os
from pathlib import Path
from django.conf import settings

# Detectar si estamos en Docker (usualmente se verifica por archivo .dockerenv o variable de entorno)
IS_DOCKER = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

# Directorio base dentro del contenedor (mapeado a ./backend en host)
# En docker-compose.yml: ./backend:/app/backend
# settings.BASE_DIR debería ser /app/backend
BASE_DIR = settings.BASE_DIR

# Configuración de Directorios de Descarga
# IMPORTANTE: Esta ruta debe ser accesible tanto por Python como por Chrome Headless
if IS_DOCKER:
    # Ruta absoluta dentro del contenedor
    DOWNLOAD_DIR_BASE = BASE_DIR / 'results' / 'downloads'
else:
    # Ruta local (Windows)
    DOWNLOAD_DIR_BASE = BASE_DIR / 'results' / 'downloads'

# Configuración de Redis/Celery (Referencias para debug)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

def get_download_dir(user_id=None):
    """
    Retorna el directorio de descarga configurado y asegurado.
    Si se pasa user_id, retorna el subdirectorio específico.
    """
    base = DOWNLOAD_DIR_BASE
    
    # Asegurar que existe el base con permisos
    try:
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)
            # En Linux/Docker, intentar dar permisos amplios para evitar problemas entre usuarios (celery vs root)
            if IS_DOCKER:
                try:
                    os.chmod(base, 0o777)
                except:
                    pass
    except Exception as e:
        print(f"Warning: No se pudo crear/chmod el directorio base {base}: {e}")

    if user_id:
        user_dir = base / str(user_id)
        if not user_dir.exists():
            user_dir.mkdir(parents=True, exist_ok=True)
            if IS_DOCKER:
                try:
                    os.chmod(user_dir, 0o777)
                except:
                    pass
        return user_dir
        
    return base

def get_chrome_options_args():
    """
    Retorna argumentos adicionales para Chrome en Docker
    """
    if IS_DOCKER:
        return [
            '--headless=new',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--remote-debugging-port=9222' # Útil para debug
        ]
    return []
