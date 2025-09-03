# saas/admin.py
from django.contrib import admin
from .models import Project, Membership, ProjectModule, Module, Invite, ProjectRole

class ProjectModuleInline(admin.TabularInline):
    model = ProjectModule
    extra = 0
    autocomplete_fields = ("module",)

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user",)
    fields = ("user", "role", "created_at")
    readonly_fields = ("created_at",)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "user_limit", "created_at")
    search_fields = ("name", "slug", "owner__username", "owner__email")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProjectModuleInline, MembershipInline]

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")

@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    list_display = ("project", "module", "enabled")
    list_filter = ("enabled", "module")
    autocomplete_fields = ("project", "module")

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("project__name", "user__username", "user__email")

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("project", "email", "role", "created_by", "created_at", "expires_at", "accepted_at")
    list_filter = ("role",)
    search_fields = ("project__name", "email", "token")
