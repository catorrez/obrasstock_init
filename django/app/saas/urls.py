# saas/urls.py
from django.urls import path
from .views import (
    project_home, toggle_module,
    create_invite, join_project, project_gate
)

urlpatterns = [
    path("p/<slug:project_slug>/home/", project_home, name="project_home"),
    path("p/<slug:project_slug>/toggle/<slug:code>/", toggle_module, name="toggle_module"),
    path("p/<slug:project_slug>/invite/", create_invite, name="create_invite"),
    path("join/<str:token>/", join_project, name="join_project"),
    # fallback genérico
    path("p/<slug:project_slug>/", project_gate, name="project_gate"),
]
