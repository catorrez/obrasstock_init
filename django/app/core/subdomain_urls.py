# core/subdomain_urls.py
"""
Subdomain-specific URL configurations
"""
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
# from saas.views import join_project  # REMOVED
from control_plane.admin import owner_admin_site, system_admin_site

def owner_home(request):
    """Home page for OWNER SYSTEM users"""
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/')
    if not request.user.is_superuser:
        return HttpResponse("Access Denied: OWNER SYSTEM access required", status=403)
    
    return render(request, 'owner/home.html', {
        'title': 'ObrasStock Owner Console',
        'user': request.user
    })

def admin_home(request):
    """Home page for ADMIN SYSTEM users"""
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/')
    if not request.user.groups.filter(name='AdminSystem').exists():
        return HttpResponse("Access Denied: ADMIN SYSTEM access required", status=403)
    
    return render(request, 'admin_system/home.html', {
        'title': 'ObrasStock Admin Console',
        'user': request.user
    })

# OWNER SYSTEM URLs (obrasstock.etvholding.com)
owner_patterns = [
    path("", owner_home, name="owner_home"),
    path("login/", auth_views.LoginView.as_view(
        template_name='owner/login.html',
        extra_context={
            'title': 'OWNER SYSTEM Login',
            'site_header': 'ObrasStock Owner Console',
            'subdomain': 'owner'
        }
    ), name="owner_login"),
    path("logout/", auth_views.LogoutView.as_view(
        next_page='/login/'
    ), name="owner_logout"),
    path("console/", owner_admin_site.urls),
]

# ADMIN SYSTEM URLs (adminos.etvholding.com) 
admin_patterns = [
    path("", admin_home, name="admin_home"),
    path("login/", auth_views.LoginView.as_view(
        template_name='admin_system/login.html',
        extra_context={
            'title': 'ADMIN SYSTEM Login', 
            'site_header': 'ObrasStock Admin Console',
            'subdomain': 'admin'
        }
    ), name="admin_login"),
    path("logout/", auth_views.LogoutView.as_view(
        next_page='/login/'
    ), name="admin_logout"),
    path("admin/", system_admin_site.urls),
]

# PROJECT USERS URLs (appos.etvholding.com)
project_patterns = [
    path("", include("portal.urls")),  # Main app portal
    # path("p/<slug:project_slug>/", include("saas.urls")),  # Project home - REMOVED
    path("p/<slug:project_slug>/", include(("inventario.urls", "inventario"), namespace="inventario")),
]

# Common URLs (available on all subdomains)
common_patterns = [
    # path("join/<str:token>/", join_project, name="join_project"),  # REMOVED
]