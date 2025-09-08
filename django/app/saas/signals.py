from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Module


@receiver(post_migrate)
def ensure_base_modules(sender, **kwargs):
    """
    Crea (si no existen) los módulos base del sistema.
    """
    base = [
        ("inventario", "Inventario"),
        ("reportes", "Reportes"),
    ]
    for code, name in base:
        Module.objects.get_or_create(code=code, defaults={"name": name})
