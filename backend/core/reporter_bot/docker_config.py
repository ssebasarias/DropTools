"""
Configuración específica para la ejecución en Docker/Celery/Redis vs local.

Separa explícitamente:
- LOCAL (Windows): manage.py unified_reporter, Edge/Chrome/Firefox, timeouts normales.
- DOCKER (Linux): Celery worker, solo Chromium y Firefox, timeouts mayores en headless.

No hay superposición: el entorno (IS_DOCKER) y las variables de entorno (BROWSER_ORDER)
definen qué config se usa. La misma base de código se ejecuta en ambos.
"""

import os
from pathlib import Path
from django.conf import settings

# Detectar si estamos en Docker (usualmente .dockerenv o variable de entorno)
IS_DOCKER = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

# --- Navegadores por entorno (una sola fuente de verdad) ---
# Docker/Linux: solo Chromium y Firefox (estables; Edge no instalado en la imagen)
BROWSER_ORDER_DOCKER = ['chrome', 'firefox']
# Local/Windows: Edge primero, luego Chrome, Firefox
BROWSER_ORDER_LOCAL = ['edge', 'chrome', 'firefox']

# --- Timeouts (segundos) ---
# En headless/Docker la página puede tardar más en renderizar; el dropdown "Acciones" necesita más margen
DOWNLOADER_ELEMENT_WAIT_TIMEOUT_DOCKER = 120
DOWNLOADER_ELEMENT_WAIT_TIMEOUT_LOCAL = 30

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

def get_reporter_browser_order():
    """
    Orden de navegadores para el reporter según entorno.
    Puede sobreescribirse con env BROWSER_ORDER (lista separada por comas).
    """
    order_env = os.environ.get('BROWSER_ORDER', '').strip()
    if order_env:
        return [b.strip().lower() for b in order_env.split(',') if b.strip()]
    return BROWSER_ORDER_DOCKER if IS_DOCKER else BROWSER_ORDER_LOCAL


def get_downloader_wait_timeout():
    """Timeout en segundos para esperar elementos en el downloader (dropdown, etc.)."""
    return DOWNLOADER_ELEMENT_WAIT_TIMEOUT_DOCKER if IS_DOCKER else DOWNLOADER_ELEMENT_WAIT_TIMEOUT_LOCAL


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
