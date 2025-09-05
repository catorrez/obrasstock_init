# saas/admin.py
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Project, Module, ProjectModule, Membership, ProjectRole


# ========= helpers de permisos (grupos) =========
ALLOWED_GROUPS = ("GodAdmin", "SuperAdmin")

def user_is_platform_admin(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ALLOWED_GROUPS).exists()


# ========= Admin oculto para User (necesario para autocomplete) =========
User = get_user_model()

@admin.register(User)
class HiddenUserAdmin(DjangoUserAdmin):
    """
    Registramos el admin de User para habilitar autocomplete_fields,
    pero lo ocultamos del menú del admin.
    """
    # El DjangoUserAdmin ya define search_fields adecuados.
    def has_module_permission(self, request):
        return False


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
        # que todos puedan VER el módulo Projects en el menú del admin
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
    Si quieres ocultarlo del menú, descomenta has_module_permission().
    """
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)

    # Para ocultar del menú pero seguir registrado (autocomplete):
    # def has_module_permission(self, request):
    #     return False


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
