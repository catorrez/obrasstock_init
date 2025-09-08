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
        ".etvholding.com,adminos.etvholding.com,appos.etvholding.com,"
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
    # Fuerza dominios correctos: /admin en adminos.* y /app en appos.*
    "saas.middleware.ForceDomainPerAreaMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Bloquea staff/superuser en /app
    "saas.middleware.NoStaffOnAppMiddleware",
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
        "OPTIONS": {"charset": "utf8mb4"},
        "CONN_MAX_AGE": 60,
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

# ¡IMPORTANTE!: Como hoy exponés Nginx en el puerto 8181 del host, incluye los orígenes con :8181.
# (Si luego sirves en 80/443 sin puerto, puedes quitar los :8181)
CSRF_TRUSTED_ORIGINS = [
    o for o in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        # incluye tus subdominios con esquema y puerto
        "http://adminos.etvholding.com:8181,http://appos.etvholding.com:8181,"
        "https://adminos.etvholding.com:8181,https://appos.etvholding.com:8181,"
        "http://65.21.91.59:8181,http://127.0.0.1:8181,http://localhost:8181"
    ).split(",") if o
]

# El admin usa su propio login en /admin/login/
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# --- Ajustes del proyecto ---
# Para construir enlaces (invites, etc) hacia el portal de clientes:
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://appos.etvholding.com:8181")

# Negativos en stock opcional
ALLOW_STOCK_NEGATIVE = os.getenv("ALLOW_STOCK_NEGATIVE", "false").lower() == "true"

# Si luego pones HTTPS en el proxy, descomenta:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# NOTA: No definas SESSION_COOKIE_DOMAIN ni CSRF_COOKIE_DOMAIN,
# así cada subdominio maneja sus cookies de forma aislada.
