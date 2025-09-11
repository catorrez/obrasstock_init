from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps


@receiver(post_migrate)
def bootstrap_saas(sender, **kwargs):
    """
    - Crea (si no existen) los módulos base del sistema.
    - Asegura la existencia del singleton AdminPolicy.
    Se ejecuta después de cada migrate y es idempotente.
    """
    # 1) Módulos base
    try:
        Module = apps.get_model("saas", "Module")  # evita import temprano
    except LookupError:
        Module = None

    if Module is not None:
        base = [
            ("inventario", "Inventario"),
            ("reportes", "Reportes"),
        ]
        for code, name in base:
            Module.objects.get_or_create(code=code, defaults={"name": name})

    # 2) Singleton de política de administración
    # (puede no existir en migraciones iniciales; manejamos eso)
    try:
        AdminPolicy = apps.get_model("saas", "AdminPolicy")
    except LookupError:
        AdminPolicy = None

    if AdminPolicy is not None:
        AdminPolicy.get()  # crea/obtiene pk=1
