from django.apps import AppConfig


class SaaSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "saas"
    verbose_name = "SaaS"

    def ready(self):
        # Conectar señales (post_migrate para crear módulos base, etc.)
        from . import signals  # noqa: F401
