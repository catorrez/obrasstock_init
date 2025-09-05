# saas/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("p/<slug:project_slug>/", views.project_home, name="project_home"),
    path("p/<slug:project_slug>/modules/<slug:code>/toggle/", views.toggle_module, name="toggle_module"),
    path("p/<slug:project_slug>/invites/new/", views.create_invite, name="create_invite"),
]
