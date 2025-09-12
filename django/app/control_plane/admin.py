from django.contrib import admin
from django.contrib.auth.models import User
from .models import (
    ModuleRegistry, Project, ProjectModule, RoleType,
    ProjectMembership, AuditLog
)




class ProjectModuleInline(admin.TabularInline):
    model = ProjectModule
    extra = 0


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0


# Privilege inlines removed - privilege system not enforced
# Use Django Groups for actual access control


@admin.register(ModuleRegistry)
class ModuleRegistryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_core', 'created_at']
    list_filter = ['is_core', 'created_at']
    search_fields = ['name', 'display_name']




# RoleType admin removed - roles are managed through bootstrap command
# Only used for project membership tracking


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'status', 'owner', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'slug', 'owner__username']
    readonly_fields = ['database_name', 'created_at', 'updated_at']
    inlines = [ProjectModuleInline, ProjectMembershipInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'owner')
        }),
        ('Status & Database', {
            'fields': ('status', 'database_name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save to use ProjectProvisioningService for audit logging"""
        from .provisioning import ProjectProvisioningService
        from .audit_service import AuditService
        
        if not change:  # New project
            # For new projects, we should use the provisioning service
            # But since we're in admin, we'll log the manual creation
            super().save_model(request, obj, form, change)
            
            AuditService.log_action(
                action='create_project',
                user=request.user,
                project=obj,
                details={
                    'created_via': 'admin_interface',
                    'project_name': obj.name,
                    'project_slug': obj.slug,
                },
                request=request,
                severity='high',
            )
        else:
            # For updates, track changes
            old_values = {}
            if obj.pk:
                try:
                    original = Project.objects.get(pk=obj.pk)
                    old_values = {
                        'name': original.name,
                        'slug': original.slug,
                        'status': original.status,
                        'description': original.description,
                        'owner': original.owner.username if original.owner else None,
                    }
                except Project.DoesNotExist:
                    pass
            
            super().save_model(request, obj, form, change)
            
            new_values = {
                'name': obj.name,
                'slug': obj.slug,
                'status': obj.status,
                'description': obj.description,
                'owner': obj.owner.username if obj.owner else None,
            }
            
            AuditService.log_action(
                action='update_project',
                user=request.user,
                project=obj,
                old_values=old_values,
                new_values=new_values,
                details={'updated_via': 'admin_interface'},
                request=request,
                severity='high',
            )
    
    def delete_model(self, request, obj):
        """Override delete to log deletion"""
        from .audit_service import AuditService
        
        # Log before deletion
        AuditService.log_action(
            action='delete_project',
            user=request.user,
            project=obj,
            details={
                'deleted_via': 'admin_interface',
                'project_name': obj.name,
                'project_slug': obj.slug,
            },
            request=request,
            severity='critical',
        )
        
        super().delete_model(request, obj)


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'role', 'is_active', 'added_at']
    list_filter = ['role', 'is_active', 'added_at']
    search_fields = ['user__username', 'project__name']




@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'project', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'project__name']
    readonly_fields = ['id', 'timestamp', 'details']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# Owner Console - Custom admin site for Control Plane management
class OwnerAdminSite(admin.AdminSite):
    """
    Custom admin site for Owner console with Control Plane management.
    """
    site_header = 'ObrasStock Owner Console'
    site_title = 'Owner Console'
    index_title = 'Control Plane Management'
    
    def has_permission(self, request):
        """Only allow OWNERS (superusers) - not regular staff"""
        if not request.user.is_active:
            return False
        
        # Only superusers (OWNERS) can access the Owner Console
        return request.user.is_superuser
    
    def login(self, request, extra_context=None):
        """Override login to check user permissions before allowing access"""
        if request.method == 'POST':
            # Get the username from the login form
            username = request.POST.get('username')
            if username:
                try:
                    from django.contrib.auth.models import User
                    user = User.objects.get(username=username)
                    if not user.is_superuser:
                        from django.contrib import messages
                        messages.error(request, 'Only owners can access the Owner Console. Use /admin/ for system administration.')
                        return self.login_form(request, extra_context)
                except User.DoesNotExist:
                    pass
        
        return super().login(request, extra_context)


# Create owner admin site instance
owner_admin_site = OwnerAdminSite(name='owner_admin')

# Register Control Plane models with owner admin
owner_admin_site.register(ModuleRegistry, ModuleRegistryAdmin)
# RoleType admin removed - only used for project membership, managed via bootstrap
owner_admin_site.register(Project, ProjectAdmin)
owner_admin_site.register(ProjectMembership, ProjectMembershipAdmin)
owner_admin_site.register(AuditLog, AuditLogAdmin)

# Ensure RoleType is not registered in default admin site
try:
    admin.site.unregister(RoleType)
except admin.sites.NotRegistered:
    pass  # Already not registered

# Also register User and Group models for user management
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
owner_admin_site.register(User, UserAdmin)
owner_admin_site.register(Group, GroupAdmin)
