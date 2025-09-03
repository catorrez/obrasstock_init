# saas/urls.py
from django.urls import path
from .views import project_home, create_invite, toggle_module, join_project, project_gate

urlpatterns = [
    path("p/<slug:project_slug>/home/", project_home, name="project_home"),
    path("p/<slug:project_slug>/toggle/<slug:code>/", toggle_module, name="toggle_module"),
    path("p/<slug:project_slug>/invites/new/", create_invite, name="create_invite"),
    path("join/<slug:token>/", join_project, name="join_project"),   # usamos slug para tokens tipo UUID string
    path("p/<slug:project_slug>/", project_gate, name="project_gate"),
]
