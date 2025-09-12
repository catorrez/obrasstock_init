# core/settings.py
from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad / Debug desde ENV ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-" + get_random_secret_key())
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [
    h for h in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        # default seguro si no pasas variable en compose:
        ".etvholding.com,obrasstock.etvholding.com,adminos.etvholding.com,appos.etvholding.com,"
        "65.21.91.59,127.0.0.1,localhost,web"
    ).split(",") if h
]

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps del proyecto
    "saas.apps.SaaSConfig",
    "control_plane",
    "inventario",
    "portal",
]

# --- Templates (requerido por admin y vistas) ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # LOGIN-ONLY: Block all access except designated login pages
    "saas.login_only_middleware.LoginOnlyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # AUDIT LOGGING: Comprehensive audit trail for all requests
    "control_plane.audit_middleware.AuditLoggingMiddleware",
    "control_plane.audit_middleware.SecurityAuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Router compatibility for tenant database routing
    "saas.login_only_middleware.RequestTenantContextMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"

# --- Base de datos (MySQL/MariaDB) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "read_timeout": 30,
            "write_timeout": 30,
        },
        "CONN_MAX_AGE": 300,  # Increased from 60 for better connection reuse
        "CONN_HEALTH_CHECKS": True,
    }
}

# Database performance and pooling configuration with connection limits
DATABASE_POOL_CONFIG = {
    "CONN_MAX_AGE": 300,  # Keep connections alive for 5 minutes
    "CONN_HEALTH_CHECKS": True,
    "OPTIONS": {
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        "read_timeout": 30,
        "write_timeout": 30,
        # Connection limits to prevent pool exhaustion
        "max_connections": 20,  # Limit connections per database
    }
}

# Per-project database connection limits (for multi-tenant scalability)
PROJECT_DB_CONNECTION_LIMIT = 10  # Max connections per project database
TOTAL_DB_CONNECTION_LIMIT = 200   # Total connection limit across all databases

# --- Caching Configuration ---
# Using Django's built-in cache for user type caching
# For production, consider Redis or Memcached for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# --- Validadores de password ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N / TZ ---
LANGUAGE_CODE = "es"
TIME_ZONE = os.getenv("TZ", "America/La_Paz")
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos / media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Proxy / CSRF / Login ---
USE_X_FORWARDED_HOST = True

# CSRF trusted origins for SSL/HTTPS setup
CSRF_TRUSTED_ORIGINS = [
    o for o in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        # incluye tus subdominios con HTTPS (sin puerto para 443)
        "https://obrasstock.etvholding.com,https://adminos.etvholding.com,https://appos.etvholding.com,"
        "http://obrasstock.etvholding.com,http://adminos.etvholding.com,http://appos.etvholding.com,"
        "https://localhost,https://127.0.0.1,http://localhost,http://127.0.0.1"
    ).split(",") if o
]

# El admin usa su propio login en /admin/login/
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"

# Para admin logout personalizado
ADMIN_LOGOUT_URL = "/admin/login/"

# --- Ajustes del proyecto ---
# Para construir enlaces (invites, etc) hacia el portal de clientes:
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://appos.etvholding.com")

# Negativos en stock opcional
ALLOW_STOCK_NEGATIVE = os.getenv("ALLOW_STOCK_NEGATIVE", "false").lower() == "true"

# Si luego pones HTTPS en el proxy, descomenta:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# NOTA: No definas SESSION_COOKIE_DOMAIN ni CSRF_COOKIE_DOMAIN,
# así cada subdominio maneja sus cookies de forma aislada.

# --- Multi-Tenant Database Configuration ---
DATABASE_ROUTERS = ['control_plane.router.MultiTenantRouter']

# Thread-local storage for tenant context
import threading
_THREAD_LOCAL = threading.local()

# --- Database Performance Monitoring ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO' if not DEBUG else 'DEBUG',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'control_plane.router': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'saas.middleware': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not logs_dir.exists():
    logs_dir.mkdir(exist_ok=True)
