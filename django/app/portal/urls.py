# portal/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from saas import views as saas_views
from saas.forms import ClientAuthForm

app_name = "portal"

urlpatterns = [
    path("", saas_views.app_home, name="home"),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="saas/app_login.html",
            authentication_form=ClientAuthForm,
            redirect_authenticated_user=True,
            extra_context={"title": "ObrasStock · Acceso clientes"},
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="/app/login/"),
        name="logout",
    ),
]
