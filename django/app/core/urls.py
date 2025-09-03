from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from saas.views import join_project, project_gate

def home(request):
    return HttpResponse("ObrasStock OK", content_type="text/plain")

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),

    # Portal de clientes (/app)
    path("app/", include("portal.urls")),

    # Invitaciones existentes
    path("join/<str:token>/", join_project, name="join_project"),

    # SAAS e Inventario
    path("", include("saas.urls")),
    path("p/<slug:project_slug>/", include("inventario.urls")),
    path("p/<slug:project_slug>/", project_gate, name="project_gate"),
]
