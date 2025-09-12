# core/urls.py
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
# from saas.views import join_project  # Removed with SAAS system
from control_plane.admin import owner_admin_site
from control_plane.system_admin import system_admin_site
from .views import SubdomainLoginView

# Customize admin logout to redirect to login page
admin.site.logout_template = 'admin/logged_out.html'

def home(request):
    """Home page that redirects based on subdomain"""
    host = request.get_host().split(":")[0]
    
    if host == "obrasstock.etvholding.com":
        # OWNER SYSTEM home
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/login/')
        if not request.user.is_superuser:
            return HttpResponse("Access Denied: OWNER SYSTEM access required", status=403)
        return render(request, 'owner/home.html', {'title': 'Owner Console'})
        
    elif host == "adminos.etvholding.com":
        # ADMIN SYSTEM home
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/login/')
        if not request.user.groups.filter(name='AdminSystem').exists():
            return HttpResponse("Access Denied: ADMIN SYSTEM access required", status=403)
        return HttpResponseRedirect('/admin/')
        
    elif host == "appos.etvholding.com":
        # PROJECT USERS home
        return HttpResponseRedirect('/app/')
    
    # Default response
    return HttpResponse("ObrasStock OK", content_type="text/plain")

urlpatterns = [
    path("", home, name="home"),
    
    # Subdomain-specific login pages
    path("login/", SubdomainLoginView.as_view(), name="login"),
    
    # Logout functionality  
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),

    # OWNER SYSTEM - obrasstock.etvholding.com only
    path("owner/", owner_admin_site.urls),
    
    # AUDIT SYSTEM - accessible to owners and admin system users
    path("audit/", include("control_plane.audit_urls")),
    
    # ADMIN SYSTEM - adminos.etvholding.com only
    path("admin/", system_admin_site.urls),

    # PROJECT USERS - appos.etvholding.com only
    path("app/", include("portal.urls")),

    # Common URLs - available on all subdomains  
    # path("join/<str:token>/", join_project, name="join_project"),  # Removed with SAAS system

    # SaaS project URLs - Removed with SAAS system
    # path("", include("saas.urls")),

    # Module URLs
    path("p/<slug:project_slug>/", include(("inventario.urls", "inventario"), namespace="inventario")),
]
