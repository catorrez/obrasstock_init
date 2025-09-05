# saas/apps.py
from django.apps import AppConfig

class SaasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "saas"
    verbose_name = "SAAS"

    def ready(self):
        # Registrar los receivers de señales
        from . import signals  # noqa: F401
