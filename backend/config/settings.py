import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name):
    """Read a comma-separated environment variable into a list."""
    return [item.strip() for item in os.environ.get(name, '').split(',') if item.strip()]


def load_dotenv(path):
    """Load KEY=value lines from a .env file without overwriting real env vars.

    Keeps the backend dependency-free (no django-environ/python-dotenv needed):
    docker compose passes the same keys as real environment, which always win.
    """
    try:
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key, value = key.strip(), value.strip().strip('\'"')
        if key and key not in os.environ:
            os.environ[key] = value


# backend/.env holds local secrets (GEMINI_API_KEY). A real environment variable
# - for example from docker-compose.yml - always takes precedence.
load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# docker-compose.yml passes DJANGO_SECRET_KEY; replace the fallback before deploying.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-zw+d!1n2q66v&es(p#d#tze4(&87r=prxm@fp(m$jyqrwf@t-!',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')

# Host names only, no ports: DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,api
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Local
    'todo_list',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serves files from STATIC_ROOT (admin CSS/JS). Must sit right after the
    # security middleware; no separate static-file service needed.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Must be listed before CommonMiddleware so CORS headers reach the browser.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # SQLITE_PATH lets the Docker image keep the file on a volume, for example
        # SQLITE_PATH=/app/data/db.sqlite3 (see docker-compose.yml).
        'NAME': os.environ.get('SQLITE_PATH', BASE_DIR / 'db.sqlite3'),
    }
}


# Cache
# Set REDIS_URL (for example redis://redis:6379/0, see docker-compose.yml) to use
# Redis. Without it - a plain local `runserver` - Django keeps the cache in memory,
# so development does not depend on a running Redis.
REDIS_URL = os.environ.get('REDIS_URL')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                # A cache outage must never take the API down: if Redis is
                # unreachable the endpoints fall back to the database. The
                # timeouts keep that fallback fast instead of hanging on a
                # dead connection (verified by stopping the redis service).
                'IGNORE_EXCEPTIONS': True,
                'SOCKET_CONNECT_TIMEOUT': 2,
                'SOCKET_TIMEOUT': 2,
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'todolist-local',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
# Directory collectstatic gathers everything into (run by docker-entrypoint.sh).
# WhiteNoise serves these files, which is what makes the admin CSS/JS work in
# Docker - gunicorn alone cannot serve static files.
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ---------------------------------------------------------------------------
# Django REST Framework / CORS (the React app in ../frontend is the only client)
# ---------------------------------------------------------------------------

# Development defaults: the Vite dev server proxies /api/* (frontend/vite.config.js)
# so it does not need CORS, but these origins cover calling the API from :5173
# directly. Add more (for example the nginx origin used by docker compose) with
# CORS_ALLOWED_ORIGINS / CSRF_TRUSTED_ORIGINS, as done in docker-compose.yml.
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
] + env_list('CORS_ALLOWED_ORIGINS')

# Write requests (POST/PATCH/DELETE) send an Origin header, which Django checks
# against this list - through the Vite proxy the browser's Origin is the Vite URL.
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
] + env_list('CSRF_TRUSTED_ORIGINS')


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# AI assistant (Gemini). The key lives server-side only: backend/.env locally
# (git-ignored, see backend/.env.example) or GEMINI_API_KEY in docker-compose.
# The browser talks to /api/chat/ and never sees the key.
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
