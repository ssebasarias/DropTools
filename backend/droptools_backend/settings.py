"""
Django settings for droptools_backend project.
"""
from pathlib import Path
import os
import environ

# Initialise environment variables
env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent

# .env loading pivot
try:
    env_path = os.path.join(BASE_DIR.parent, '.env')
    print(f"DEBUG: Loading .env from {env_path}")
    environ.Env.read_env(env_path) # Let django-environ handle opening
except Exception as e:
    print(f"DEBUG: Error loading .env: {e}")

# SECURITY: Do not keep a production SECRET_KEY in source control.
# Require `SECRET_KEY` via env in non-debug environments.
DEBUG = env.bool('DEBUG', default=False)

# --- Entorno: desarrollo vs producción (una sola fuente de verdad) ---
# Acepta DROPTOOLS_ENV o legacy DAHELL_ENV
DROPTOOLS_ENV = env('DROPTOOLS_ENV', default=env('DAHELL_ENV', default='production')).lower().strip()
if DROPTOOLS_ENV not in ('development', 'production'):
    DROPTOOLS_ENV = 'production'
IS_DEVELOPMENT = DROPTOOLS_ENV == 'development'
IS_DOCKER = os.path.exists('/.dockerenv') or env.bool('DOCKER_CONTAINER', default=False)
if DEBUG:
    # In debug mode allow a local insecure default to make development easier.
    SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-placeholder')
else:
    # In production require SECRET_KEY to be provided explicitly.
    SECRET_KEY = env('SECRET_KEY')

# Google OAuth Configuration (mismo Client ID que el frontend para verificar el ID token)
GOOGLE_CLIENT_ID = os.getenv(
    'GOOGLE_CLIENT_ID',
    '873344941573-7oqihc52h8mtp8gk80ebjakamtd81gi0.apps.googleusercontent.com'
)
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
# En producción usar GOOGLE_REDIRECT_URI=https://droptools.cloud (o la URL de callback) en .env.production
GOOGLE_REDIRECT_URI = os.getenv(
    'GOOGLE_REDIRECT_URI',
    'http://localhost:5173/auth/google/callback' if DEBUG else 'https://droptools.cloud/'
)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', 'testserver', 'droptools.cloud', 'www.droptools.cloud'])

# Orígenes permitidos para CSRF (formularios Django admin, etc.) cuando la petición viene de HTTPS
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=['https://droptools.cloud', 'https://www.droptools.cloud']
)



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres', # Required for ArrayField & VectorField
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'core',
]

# Configurar modelo de usuario personalizado
AUTH_USER_MODEL = 'core.User'


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'droptools_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'droptools_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', default='droptools_db'),
        'USER': env('POSTGRES_USER', default='droptools_admin'),
        'PASSWORD': env('POSTGRES_PASSWORD', default='secure_password_123'),
        # When running under docker-compose the DB service hostname is usually 'db'
        'HOST': env('POSTGRES_HOST', default='db'),
        # The DB container listens on 5432 internally; host mapping may vary.
        'PORT': env('POSTGRES_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            # Workaround para SQL_ASCII encoding (temporal hasta migrar a UTF8)
            'client_encoding': 'LATIN1',
        }
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "https://droptools.cloud",
    "https://www.droptools.cloud",
]
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Basic security headers (safe for local; tighten further in production).
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# DRF: por ahora dejamos endpoints públicos por defecto (AllowAny)
# y aplicamos IsAuthenticated solo a los endpoints que lo requieren.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Secure-by-default: require auth unless explicitly opened.
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Bogota'
CELERY_ENABLE_UTC = True
CELERY_WORKER_CONCURRENCY = 3  # Número de tareas simultáneas por worker
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Tomar 1 tarea a la vez
CELERY_TASK_TIME_LIMIT = 3600  # 1 hora máximo por tarea
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # Advertencia a los 55 minutos
CELERY_RESULT_EXPIRES = 3600  # Resultados expiran en 1 hora

# Reporter: en proceso solo cuando desarrollo Y no Docker (Windows local). En Docker siempre Celery.
REPORTER_USE_CELERY = (DROPTOOLS_ENV == 'production') or IS_DOCKER

# Reporter slot system: límite Selenium y estimación de carga
MAX_ACTIVE_SELENIUM = int(os.getenv('MAX_ACTIVE_SELENIUM', '6'))
REPORTER_ESTIMATED_PENDING_FACTOR = float(os.getenv('REPORTER_ESTIMATED_PENDING_FACTOR', '0.08'))
REPORTER_RANGE_SIZE = int(os.getenv('REPORTER_RANGE_SIZE', '100'))
REPORTER_SELENIUM_SEMAPHORE_TTL = int(os.getenv('REPORTER_SELENIUM_SEMAPHORE_TTL', '3300'))  # 55 min

# Etiqueta para UI/logs: development | development_docker | production
REPORTER_RUN_MODE = 'development_docker' if (IS_DEVELOPMENT and IS_DOCKER) else ('development' if IS_DEVELOPMENT else 'production')

# Confirmación en consola al cargar settings (para certeza de modo activo)
def _log_droptools_env():
    if IS_DEVELOPMENT and IS_DOCKER:
        rep = "Celery (desarrollo Docker)"
    elif REPORTER_USE_CELERY:
        rep = "Celery (producción)"
    else:
        rep = "en proceso (desarrollo local)"
    print(f"[DropTools] DROPTOOLS_ENV={DROPTOOLS_ENV} | Reporter: {rep}")
_log_droptools_env()
