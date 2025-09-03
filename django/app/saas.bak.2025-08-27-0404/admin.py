from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from .models import Project, Membership, ProjectModule, Invite

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name","slug","owner","project_link")
    search_fields = ("name","slug","owner__username")
    def project_link(self, obj):
        base = getattr(settings, "SITE_BASE_URL", "http://65.21.91.59:8181")
        return format_html('<a href="{}/p/{}/" target="_blank">abrir</a>', base, obj.slug)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("project","user","role")
    list_filter  = ("project","role")
    search_fields = ("project__name","user__username","user__email")

@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    list_display = ("project","module","enabled")
    list_filter  = ("project","module","enabled")

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("project","email","role","expires_at","accepted_at","invite_url")
    list_filter  = ("project","role","accepted_at")
    search_fields = ("email","project__name")
    def invite_url(self, obj):
        base = getattr(settings, "SITE_BASE_URL", "http://65.21.91.59:8181")
        return format_html('<input style="width:340px" value="{}/join/{}" readonly>', base, obj.token)
    invite_url.short_description = "Link"
