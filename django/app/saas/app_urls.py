# saas/app_urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="saas/app_login.html",
        redirect_authenticated_user=True
    ), name="app_login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/app/login/"), name="app_logout"),
    path("", views.app_home, name="app_home"),
]
