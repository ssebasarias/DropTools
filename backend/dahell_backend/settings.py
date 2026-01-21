"""
Django settings for dahell_backend project.
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
if DEBUG:
    # In debug mode allow a local insecure default to make development easier.
    SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-placeholder')
else:
    # In production require SECRET_KEY to be provided explicitly.
    SECRET_KEY = env('SECRET_KEY')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', 'testserver'])



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

ROOT_URLCONF = 'dahell_backend.urls'

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

WSGI_APPLICATION = 'dahell_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', default='dahell_db'),
        'USER': env('POSTGRES_USER', default='dahell_admin'),
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
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Secure-by-default: require auth unless explicitly opened.
        "rest_framework.permissions.IsAuthenticated",
    ],
}
