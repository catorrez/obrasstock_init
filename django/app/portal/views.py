from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.conf import settings
from control_plane.models import ProjectMembership, ProjectModule

@login_required(login_url="/app/login/")
def app_home(request):
    """
    App home for regular users - shows their available projects.
    """
    # Get user's project memberships
    memberships = ProjectMembership.objects.filter(
        user=request.user
    ).select_related('project').order_by('project__name')
    
    # Build project data with enabled modules
    user_projects = []
    for membership in memberships:
        project = membership.project
        
        # Get enabled modules for this project
        enabled_modules = ProjectModule.objects.filter(
            project=project, 
            enabled=True
        ).select_related('module')
        
        # Build project URLs for VPS environment
        base_url = "https://appos.etvholding.com"
        project_data = {
            'project': project,
            'membership': membership,
            'enabled_modules': enabled_modules,
            'project_url': f"{base_url}/p/{project.slug}/",
            'module_count': enabled_modules.count(),
        }
        
        user_projects.append(project_data)
    
    context = {
        'user_projects': user_projects,
        'has_projects': len(user_projects) > 0,
        'base_url': settings.SITE_BASE_URL,
    }
    
    return render(request, "portal/app_home.html", context)

def app_logout(request):
    logout(request)
    return redirect("/app/login/")

@login_required(login_url="/app/login/")
def select_project(request):
    """
    Project selection view - redirects to app_home for now
    """
    return redirect('portal:home')
