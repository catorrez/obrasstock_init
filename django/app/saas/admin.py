from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Project, Module, ProjectModule, Membership, ProjectRole

# ========= helpers de permisos (grupos) =========
ALLOWED_GROUPS = ("GodAdmin", "SuperAdmin")

def user_is_platform_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ALLOWED_GROUPS).exists()


# ========= INLINES =========

class ProjectModuleInline(admin.TabularInline):
    """
    Módulos asignados al proyecto (encender/apagar).
    """
    model = ProjectModule
    extra = 0
    autocomplete_fields = ["module"]
    fields = ("module", "enabled")
    show_change_link = True


class MembershipInlineFormSet(BaseInlineFormSet):
    """
    Valida que siempre quede al menos un OWNER.
    """
    def clean(self):
        super().clean()
        owners = 0
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data:
                continue
            role = form.cleaned_data.get("role")
            if role is None and form.instance.pk:
                role = form.instance.role
            if role == ProjectRole.OWNER:
                owners += 1
        if owners == 0:
            raise ValidationError("Debe existir al menos un OWNER en el proyecto.")


class MembershipInline(admin.TabularInline):
    """
    Miembros del proyecto y sus roles.
    Solo GodAdmin/SuperAdmin pueden cambiar roles/eliminar.
    """
    model = Membership
    formset = MembershipInlineFormSet
    extra = 0
    autocomplete_fields = ["user"]
    fields = ("user", "role", "created_at")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)


# ========= ADMINS =========

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Pantalla principal: Projects.
    - Lista proyectos sin repetir (uno por fila).
    - Inlines: módulos y miembros/roles.
    - Seguridad: sólo GodAdmin/SuperAdmin pueden cambiar.
    """
    inlines = [ProjectModuleInline, MembershipInline]

    list_display = ("name", "slug", "owners_display", "modules_enabled_display", "members_count")
    search_fields = ("name", "slug", "memberships__user__username", "memberships__user__email")
    ordering = ("name",)

    def members_count(self, obj):
        return obj.memberships.count()
    members_count.short_description = "Miembros"

    def owners_display(self, obj):
        owners = obj.memberships.filter(role=ProjectRole.OWNER).select_related("user")
        return ", ".join(m.user.username for m in owners)
    owners_display.short_description = "Owners"

    def modules_enabled_display(self, obj):
        qs = obj.project_modules.filter(enabled=True).select_related("module")
        return ", ".join(pm.module.name for pm in qs)
    modules_enabled_display.short_description = "Módulos ON"

    # --- permisos en admin ---
    def has_module_permission(self, request):
        # todos pueden VER el módulo Projects en el menú (para consultar)
        return request.user.is_authenticated

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated

    def has_add_permission(self, request):
        return user_is_platform_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """
    Catálogo de módulos del sistema (Inventario, Reportes, etc.)
    """
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    """
    Lo ocultamos del menú para evitar duplicar pantallas.
    Sigue accesible desde el inline dentro de Project.
    """
    list_display = ("project", "module", "enabled")
    autocomplete_fields = ["project", "module"]

    def has_module_permission(self, request):
        return False


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Lo ocultamos del menú. Gestión desde Project (inline).
    """
    list_display = ("project", "user", "role", "created_at")
    search_fields = ("project__name", "user__username", "user__email")
    autocomplete_fields = ["project", "user"]

    def has_module_permission(self, request):
        return False


# ========== USER/GROUP PROXIES EN SAAS ==========

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as _DefaultUserAdmin, GroupAdmin as _DefaultGroupAdmin
from .models import UserProxy, GroupProxy

# 1) Obtener el modelo User ACTIVO antes de usarlo en decorators
User = get_user_model()

# 2) Capturar las clases ModelAdmin actualmente registradas (antes de unregister)
#    Hacemos una copia porque vamos a modificar el registry.
_registry = admin.site._registry.copy()
UserAdminBase = _registry.get(User).__class__ if _registry.get(User) else _DefaultUserAdmin
GroupAdminBase = _registry.get(Group).__class__ if _registry.get(Group) else _DefaultGroupAdmin

# 3) Quitar los originales del admin (si estaban)
for model in (User, Group):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass

# 4) Registrar el User/Group reales con admin oculto (para que funcione autocomplete)
@admin.register(User)
class _HiddenUserAdmin(UserAdminBase):
    def has_module_permission(self, request):
        return False  # no aparece en el menú

@admin.register(Group)
class _HiddenGroupAdmin(GroupAdminBase):
    def has_module_permission(self, request):
        return False

# 5) Registrar los PROXIES bajo SAAS heredando las mismas clases Admin
@admin.register(UserProxy)
class UserProxyAdmin(UserAdminBase):
    pass

@admin.register(GroupProxy)
class GroupProxyAdmin(GroupAdminBase):
    pass
