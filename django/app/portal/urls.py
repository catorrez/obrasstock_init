from django.urls import path
from django.contrib.auth.views import LoginView
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.app_home, name="home"),
    path("login/", LoginView.as_view(template_name="portal/login.html"), name="login"),
    path("logout/", views.app_logout, name="logout"),
    path("select-project/", views.select_project, name="select_project"),
]
