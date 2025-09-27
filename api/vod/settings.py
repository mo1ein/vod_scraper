from pathlib import Path
import os
from urllib.parse import urlparse

# --- load .env ---
BASE_DIR = Path(__file__).resolve().parent.parent   # currently points to `api/`
PROJECT_ROOT = BASE_DIR.parent                       # project root (where .env lives)
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    # lazy import to avoid failing if package not installed in some envs
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

# --- basic settings ---
SECRET_KEY = os.environ.get('DJANGO_SECRET', 'dev-secret')
DEBUG = str(os.environ.get('DEBUG', 'True')).lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
# ALLOWED_HOSTS = ['*']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'api.catalog'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'api.vod.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = 'api.vod.wsgi.application'

# Database: use DATABASE_URL env var; default points to docker-compose `db` service
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://voduser:vodpass@localhost:5433/vod')
url = urlparse(DATABASE_URL)
if url.scheme.startswith('postgres'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:] or 'vod',
            'USER': url.username or '',
            'PASSWORD': url.password or '',
            'HOST': url.hostname or 'localhost',
            'PORT': url.port or 5432,
        }
    }

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redis configuration: prefer REDIS_URL, fallback to REDIS_HOST/PORT/DB
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    r = urlparse(REDIS_URL)
    REDIS_HOST = r.hostname or 'localhost'
    REDIS_PORT = int(r.port or 6379)
    REDIS_DB = int(r.path.lstrip('/') or 0)
else:
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
