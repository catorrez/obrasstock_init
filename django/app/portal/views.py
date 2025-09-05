# portal/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from saas.forms import ClientAuthForm
from saas.models import Membership

class AppLoginView(LoginView):
    """
    Login del portal de clientes (/app/login/).
    Usa ClientAuthForm para bloquear staff/superuser aquí.
    Reutilizamos la plantilla del admin para evitar TemplateDoesNotExist.
    """
    template_name = "admin/login.html"
    authentication_form = ClientAuthForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("portal:home")

@login_required(login_url="/app/login/")
def app_home(request):
    """
    Home del portal de clientes: lista los proyectos del usuario.
    """
    memberships = (
        Membership.objects
        .select_related("project", "user")
        .filter(user=request.user)
        .order_by("project__name")
    )
    # Reutilizamos el template que ya tenías
    return render(request, "saas/app_home.html", {"memberships": memberships})

@login_required(login_url="/app/login/")
def select_project(request):
    """
    Pantalla para elegir proyecto (si quieres una lista explícita).
    """
    memberships = (
        Membership.objects
        .select_related("project", "user")
        .filter(user=request.user)
        .order_by("project__name")
    )
    # Si aún no tienes template, puedes reutilizar el mismo
    return render(request, "saas/app_home.html", {"memberships": memberships})

@login_required(login_url="/app/login/")
def app_logout(request):
    """
    Logout del portal de clientes; vuelve a /app/login/
    """
    auth_logout(request)
    return redirect("/app/login/")
