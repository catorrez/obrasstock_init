# portal/views.py
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from saas.models import Membership
from saas.forms import ClientAuthForm

class AppLoginView(LoginView):
    template_name = "portal/login.html"
    authentication_form = ClientAuthForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or "/app/projects/"

def app_index(request):
    if not request.user.is_authenticated:
        return redirect("app_login")
    return redirect("select_project")

def app_logout(request):
    logout(request)
    return redirect("app_login")

@login_required(login_url="/app/login/")
def select_project(request):
    memberships = (
        Membership.objects
        .select_related("project")
        .filter(user=request.user)
        .order_by("project__name")
    )
    return render(request, "portal/select_project.html", {"memberships": memberships})
