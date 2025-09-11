# core/urls.py
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.http import HttpResponse
from saas.views import join_project

# Customize admin logout to redirect to login page
admin.site.logout_template = 'admin/logged_out.html'

def home(request):
    return HttpResponse("ObrasStock OK", content_type="text/plain")

urlpatterns = [
    path("", home, name="home"),

    # Admin dueño/operadores
    path("admin/", admin.site.urls),

    # Portal de clientes
    path("app/", include("portal.urls")),

    # Invitaciones (token)
    path("join/<str:token>/", join_project, name="join_project"),

    # Rutas SaaS (toggler de módulos, invites, project home)
    path("", include("saas.urls")),

    # Rutas de módulos por proyecto (inventario, etc.)
    path("p/<slug:project_slug>/", include(("inventario.urls", "inventario"), namespace="inventario")),
]
