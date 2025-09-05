# saas/signals.py
from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

def ensure_base_modules():
    """
    Crea/asegura los módulos base del sistema.
    """
    Module = apps.get_model("saas", "Module")
    base = [
        ("inventario", "Inventario"),
        ("reportes", "Reportes"),
    ]
    for code, name in base:
        Module.objects.get_or_create(code=code, defaults={"name": name})

@receiver(post_migrate)
def _ensure_modules_after_migrate(sender, **kwargs):
    # Sólo cuando migra la app 'saas'
    if getattr(sender, "name", "") != "saas":
        return
    ensure_base_modules()
