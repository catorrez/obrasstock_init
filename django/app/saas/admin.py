from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Project, Module, ProjectModule, Membership, ProjectRole, AdminPolicy, UserProxy, GroupProxy, Invite

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


# ======== MIXIN DE ACCESO CONFIGURABLE (Owner o SysAdmin si toggle ON) ========
from .roles import user_is_owner, user_is_system_admin
from .policy import can_manage_groups, can_manage_modules

class OwnerOrSysAdminIfEnabledMixin:
    """
    Owner siempre puede; system_admin sólo si el toggle correspondiente está activado.
    Define 'perm_flag' en la subclase: "groups" o "modules".
    """
    perm_flag = None  # "groups" | "modules"

    def _allowed(self, user):
        if self.perm_flag == "groups":
            return can_manage_groups(user)
        elif self.perm_flag == "modules":
            return can_manage_modules(user)
        # Fallback estricto: sólo Owner
        return user_is_owner(user)

    def has_module_permission(self, request):
        return self._allowed(request.user)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request.user)

    def has_add_permission(self, request):
        return self._allowed(request.user)

    def has_change_permission(self, request, obj=None):
        return self._allowed(request.user)

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request.user)


@admin.register(Module)
class ModuleAdmin(OwnerOrSysAdminIfEnabledMixin, admin.ModelAdmin):
    """
    Catálogo de módulos del sistema (Inventario, Reportes, etc.)
    Owner siempre; system_admin sólo si 'allow_system_admin_modules' está ON.
    """
    perm_flag = "modules"
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    """
    Relación proyecto-módulo (visible solo para OWNER y SYSTEM ADMIN habilitados)
    """
    list_display = ("project", "module", "enabled")
    list_filter = ("enabled", "module")
    search_fields = ("project__name", "project__slug", "module__name", "module__code")
    autocomplete_fields = ["project", "module"]

    def has_module_permission(self, request):
        return user_is_platform_admin(request.user)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Membresías de proyecto (visible solo para OWNER y SYSTEM ADMIN habilitados)
    """
    list_display = ("project", "user", "role", "created_at", "is_owner")
    list_filter = ("role", "created_at")
    search_fields = ("project__name", "project__slug", "user__username", "user__email")
    autocomplete_fields = ["project", "user"]
    readonly_fields = ("created_at", "is_owner")

    def has_module_permission(self, request):
        return user_is_platform_admin(request.user)


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    """
    Invitaciones a proyectos (visible solo para OWNER y SYSTEM ADMIN habilitados)
    """
    list_display = ("project", "email", "role", "created_by", "created_at", "expires_at", "is_expired", "accepted_at")
    list_filter = ("role", "created_at", "expires_at", "accepted_at")
    search_fields = ("project__name", "project__slug", "email", "created_by__username")
    autocomplete_fields = ["project", "created_by"]
    readonly_fields = ("created_at", "is_expired", "token")
    
    def has_module_permission(self, request):
        return user_is_platform_admin(request.user)


# ========== USER/GROUP PROXIES EN SAAS ==========

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as _DefaultUserAdmin, GroupAdmin as _DefaultGroupAdmin

# 1) Obtener el modelo User ACTIVO antes de usarlo en decorators
User = get_user_model()

# 2) Capturar las clases ModelAdmin actualmente registradas (antes de unregister)
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
        return False  # no aparece en el menú


# 5) Registrar los PROXIES bajo SAAS
@admin.register(UserProxy)
class UserProxyAdmin(UserAdminBase):
    """Gestión de usuarios bajo SAAS."""
    pass

@admin.register(GroupProxy)
class GroupProxyAdmin(OwnerOrSysAdminIfEnabledMixin, GroupAdminBase):
    """
    Grupos bajo SAAS: Owner siempre; system_admin sólo si 'allow_system_admin_groups' está ON.
    """
    perm_flag = "groups"
    pass


# ======== Admin de la Política (toggles) ========

@admin.register(AdminPolicy)
class AdminPolicyAdmin(admin.ModelAdmin):
    list_display = ("allow_system_admin_groups", "allow_system_admin_modules", "updated_at")
    fields = ("allow_system_admin_groups", "allow_system_admin_modules")
    readonly_fields = ()

    # Sólo Owner puede ver/editar la política
    def has_module_permission(self, request):
        return user_is_owner(request.user)

    def has_view_permission(self, request, obj=None):
        return user_is_owner(request.user)

    def has_add_permission(self, request):
        return False  # singleton

    def has_change_permission(self, request, obj=None):
        return user_is_owner(request.user)

    def has_delete_permission(self, request, obj=None):
        return False


# ======== REGISTER SAAS MODELS IN OWNER ADMIN SITE FOR COMPARISON ========

# Import the owner admin site
from control_plane.admin import owner_admin_site

# Register SAAS models in the owner admin site so OWNER can see both systems
owner_admin_site.register(Project, ProjectAdmin)
owner_admin_site.register(Module, ModuleAdmin)
owner_admin_site.register(ProjectModule, ProjectModuleAdmin)
owner_admin_site.register(Membership, MembershipAdmin)
owner_admin_site.register(Invite, InviteAdmin)
owner_admin_site.register(AdminPolicy, AdminPolicyAdmin)
owner_admin_site.register(UserProxy, UserProxyAdmin)
owner_admin_site.register(GroupProxy, GroupProxyAdmin)
