from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect, render

@login_required(login_url="/app/login/")
def app_home(request):
    return render(request, "saas/app_home.html")

def app_logout(request):
    logout(request)
    return redirect("/app/login/")

@login_required(login_url="/app/login/")
def select_project(request):
    # tu implementación actual
    return render(request, "portal/select_project.html")
