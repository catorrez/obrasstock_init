from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Project, ProjectMembership, RoleType, ModuleRegistry
from .provisioning import ProjectProvisioningService
import logging

logger = logging.getLogger(__name__)


def is_admin_system_user(user):
    """Check if user is OWNER or ADMIN SYSTEM"""
    if not user.is_authenticated:
        return False
    if user.is_superuser:  # OWNER
        return True
    return user.groups.filter(name="AdminSystem").exists()


@user_passes_test(is_admin_system_user)
def admin_dashboard(request):
    """
    Dashboard for ADMIN SYSTEM users showing system-wide overview.
    """
    projects = Project.objects.filter(status='active').select_related('owner')
    total_users = User.objects.filter(is_active=True).count()
    total_projects = projects.count()
    
    return render(request, 'control_plane/admin_dashboard.html', {
        'projects': projects,
        'total_users': total_users,
        'total_projects': total_projects,
        'title': 'System Dashboard'
    })


def _get_user_role_in_project(user, project):
    """Get user's role in a specific project"""
    if not user.is_authenticated:
        return None
    
    # Check if owner
    if project.owner == user:
        return 'owner'
    
    # Check if ADMIN SYSTEM (can manage any project)
    if user.is_superuser or user.groups.filter(name="AdminSystem").exists():
        return 'admin_system'
    
    # Check membership
    try:
        membership = ProjectMembership.objects.get(
            project=project,
            user=user,
            is_active=True
        )
        return membership.role.name
    except ProjectMembership.DoesNotExist:
        return None
