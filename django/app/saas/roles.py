from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

SYSTEM_ADMIN = "system_admin"

ALLOWED_OWNER_GROUPS = ("GodAdmin", "SuperAdmin")  # dueños/plataforma

def get_or_create_system_admin_group():
    g, _ = Group.objects.get_or_create(name=SYSTEM_ADMIN)
    return g

def assign_system_admin_perms():
    """
    Da 'casi todo' al system_admin, EXCEPTO:
    - auth.Group (administración de grupos)
    - saas.Module (administración de módulos del sistema)
    """
    g = get_or_create_system_admin_group()

    excluded = []
    # Excluir auth.Group
    try:
        excluded.append(ContentType.objects.get(app_label="auth", model="group"))
    except ContentType.DoesNotExist:
        pass

    # Excluir saas.Module si existe
    try:
        excluded.append(ContentType.objects.get(app_label="saas", model="module"))
    except ContentType.DoesNotExist:
        pass

    all_perms = Permission.objects.all()
    keep = [p for p in all_perms if p.content_type not in excluded]
    g.permissions.set(keep)
    g.save()
    return g

def user_is_owner(user):
    """
    Consideramos 'Owner' a superuser o miembros de GodAdmin/SuperAdmin.
    (Ajusta si luego defines un modelo Owner real.)
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ALLOWED_OWNER_GROUPS).exists()

def user_is_system_admin(user):
    return user.is_authenticated and user.groups.filter(name=SYSTEM_ADMIN).exists()
