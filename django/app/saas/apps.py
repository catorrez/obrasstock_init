from django.apps import AppConfig

class SaaSConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Usa el path de tu app real (carpeta "app/saas" dentro de "django")
    name = "saas"
    verbose_name = "SAAS"   # Así saldrá el bloque en /admin
