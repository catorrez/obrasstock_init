# portal/urls.py
from django.urls import path
from .views import AppLoginView, app_home, app_logout, select_project

app_name = "portal"

urlpatterns = [
    path("", app_home, name="home"),
    path("login/", AppLoginView.as_view(), name="login"),
    path("logout/", app_logout, name="logout"),
    path("select-project/", select_project, name="select_project"),
]
