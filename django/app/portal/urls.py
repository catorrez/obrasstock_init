# portal/urls.py
from django.urls import path
from .views import AppLoginView, app_index, app_logout, select_project

urlpatterns = [
    path("", app_index, name="portal_home"),
    path("login/", AppLoginView.as_view(), name="app_login"),
    path("logout/", app_logout, name="app_logout"),
    path("projects/", select_project, name="select_project"),
]
