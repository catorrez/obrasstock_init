from django.contrib import admin
from django.contrib.auth.models import User


class SystemAdminSite(admin.AdminSite):
    """
    Custom admin site for ADMIN SYSTEM users (non-superusers).
    """
    site_header = 'ObrasStock System Admin'
    site_title = 'System Admin'
    index_title = 'System Administration'
    
    def has_permission(self, request):
        """Allow staff users but NOT superusers"""
        if not request.user.is_active:
            return False
        
        # If user is authenticated but is a superuser, force logout
        if request.user.is_authenticated and request.user.is_superuser:
            return False
        
        # Allow staff users but exclude superusers (they use /owner/)
        return request.user.is_staff and not request.user.is_superuser
    
    def login(self, request, extra_context=None):
        """Override login to provide clear messaging for wrong interface access"""
        
        # If user is already authenticated as superuser, show helpful message
        if request.user.is_authenticated and request.user.is_superuser:
            from django.contrib import messages
            from django.contrib.auth import logout
            logout(request)
            messages.info(request, f'Owner "{request.user.username}" was logged out. Owners should use /owner/ console. Please login with a system admin account.')
        
        if request.method == 'POST':
            # Get the username from the login form
            username = request.POST.get('username')
            if username:
                try:
                    from django.contrib.auth.models import User
                    user = User.objects.get(username=username)
                    if user.is_superuser:
                        from django.contrib import messages
                        messages.error(request, f'User "{username}" is an Owner and should use /owner/ console. This interface is for system administrators only.')
                        return self.login_form(request, extra_context)
                except User.DoesNotExist:
                    pass
        
        return super().login(request, extra_context)


# Create system admin site instance  
system_admin_site = SystemAdminSite(name='system_admin')

# Register only specific models for system admins
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from .models import Project, ProjectMembership
from .admin import ProjectAdmin, ProjectMembershipAdmin

# Basic user/group management
system_admin_site.register(User, UserAdmin)
system_admin_site.register(Group, GroupAdmin)

# Project management (but not Control Plane configuration)
system_admin_site.register(Project, ProjectAdmin)
system_admin_site.register(ProjectMembership, ProjectMembershipAdmin)