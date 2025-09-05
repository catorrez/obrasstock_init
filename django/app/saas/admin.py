# saas/admin.py

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Project, Module, ProjectModule, Membership, ProjectRole

# ====== Permisos de plataforma (por grupos) ======
ALLOWED_GROUPS = ("GodAdmin", "SuperAdmin")

def user_is_platform_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ALLOWED_GROUPS).exists()


# ====== INLINES ======

class ProjectModuleInline(admin.TabularInline):
    """
    Módulos asignados al proyecto (encender/apagar).
    """
    model = ProjectModule
    extra = 0
    autocomplete_fields = ["module"]
    fields = ("module", "enabled")
    show_change_link = True

    # Sólo God/SuperAdmin modifican
    def has_add_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return user_is_platform_admin(request.user)

    # Si quieres que usuarios sin permisos lo vean en solo lectura, descomenta:
    # def get_readonly_fields(self, request, obj=None):
    #     return () if user_is_platform_admin(request.user) else ("module", "enabled")


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
    Sólo GodAdmin/SuperAdmin pueden agregar/cambiar/eliminar.
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


# ====== ADMINS ======

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Pantalla principal: Projects.
    - Lista proyectos sin repetir (uno por fila).
    - Inlines: módulos y miembros/roles.
    - Seguridad: sólo GodAdmin/SuperAdmin pueden cambiar.
    """
    inlines = [ProjectModuleInline, MembershipInline]

    list_display = (
        "name",
        "slug",
        "owners_display",
        "modules_enabled_display",
        "members_count",
    )
    search_fields = (
        "name",
        "slug",
        "memberships__user__username",
        "memberships__user__email",
    )
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

    # Permisos de módulo Project en admin
    def has_module_permission(self, request):
        # Todos los autenticados lo pueden ver en el menú
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
    """Catálogo de módulos del sistema (Inventario, Reportes, etc.)."""
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    """
    Oculto del menú (se gestiona vía inline en Project).
    """
    list_display = ("project", "module", "enabled")
    autocomplete_fields = ["project", "module"]

    def has_module_permission(self, request):
        return False


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Oculto del menú (se gestiona vía inline en Project).
    """
    list_display = ("project", "user", "role", "created_at")
    search_fields = ("project__name", "user__username", "user__email")
    autocomplete_fields = ["project", "user"]

    def has_module_permission(self, request):
        return False


# ====== Overrides para Usuarios/Grupos del admin ======
# Renombramos y filtramos usuarios admin (is_staff=True) en el listado.

from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group

# Cambiamos etiquetas visibles en el menú del admin
User._meta.verbose_name = "Usuario Admin"
User._meta.verbose_name_plural = "Usuarios Admin"
Group._meta.verbose_name = "Grupo Admin"
Group._meta.verbose_name_plural = "Grupos Admin"

# Re-registramos User para filtrar sólo staff/superusers
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class StaffOnlyUserAdmin(UserAdmin):
    """En el listado aparecen sólo cuentas de administración (is_staff=True)."""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_staff=True)

    # Si quisieras restringir totalmente el acceso al módulo de usuarios admin
    # sólo a GodAdmin / SuperAdmin / superuser, descomenta:
    #
    # def _is_platform_admin(self, user):
    #     return user.is_superuser or user.groups.filter(name__in=ALLOWED_GROUPS).exists()
    # def has_module_permission(self, request): return self._is_platform_admin(request.user)
    # def has_view_permission(self, request, obj=None): return self._is_platform_admin(request.user)
    # def has_add_permission(self, request): return self._is_platform_admin(request.user)
    # def has_change_permission(self, request, obj=None): return self._is_platform_admin(request.user)
    # def has_delete_permission(self, request, obj=None): return self._is_platform_admin(request.user)


# Re-registramos Group (para renombrar en el menú)
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class AdminGroupAdmin(GroupAdmin):
    pass
