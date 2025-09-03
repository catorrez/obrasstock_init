# portal/views.py
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from saas.models import Membership

@login_required(login_url="/app/login/")
def home(request):
    """Portal del cliente: lista los proyectos en los que el usuario es miembro."""
    memberships = (
        Membership.objects
        .filter(user=request.user)
        .select_related("project")
        .order_by("project__name")
    )
    return render(request, "portal/home.html", {"memberships": memberships})

def app_logout(request):
    """Logout por GET y redirección al formulario de login del portal."""
    logout(request)
    return redirect("/app/login/")
