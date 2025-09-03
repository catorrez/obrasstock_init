# core/settings.py
from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad / Debug desde ENV ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-" + get_random_secret_key())
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,web").split(",") if h]

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Apps del proyecto:
    "saas",
    "inventario",
    "portal",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # <- Debe ir ANTES de SessionMiddleware
    "saas.middleware.DualSessionCookieMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "saas.middleware.NoStaffOnAppMiddleware",
    "saas.middleware.RedirectClientsFromAdminMiddleware",
]

ROOT_URLCONF = "core.urls"

# --- TEMPLATES (requerido por admin) ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # opcional: carpeta de templates globales
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
        "OPTIONS": {"charset": "utf8mb4"},
        "CONN_MAX_AGE": 60,  # pool simple
    }
}

# --- Auth / Password validators ---
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

# --- Static / Media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Proxy / CSRF / Login ---
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = [
    o for o in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://127.0.0.1:8181,http://localhost:8181,http://65.21.91.59:8181"
    ).split(",") if o
]

# Para /admin
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# --- Ajustes de la app ---
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://127.0.0.1:8181")
ALLOW_STOCK_NEGATIVE = os.getenv("ALLOW_STOCK_NEGATIVE", "false").lower() == "true"

# Si más adelante usas HTTPS detrás de Nginx:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
