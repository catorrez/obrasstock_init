# saas/views.py
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

from .models import Project, ProjectModule, Module, Invite, Membership, ProjectRole
from .forms import InviteForm

# ---------- Helpers ----------
def _require_member(project: Project, user):
    if not user.is_authenticated:
        return None
    try:
        return Membership.objects.get(project=project, user=user)
    except Membership.DoesNotExist:
        return None

def _require_admin_or_owner(project: Project, user) -> bool:
    m = _require_member(project, user)
    if not m:
        return False
    return m.role in (ProjectRole.OWNER, ProjectRole.ADMIN) or m.is_owner

# ---------- Mapeo de módulos -> URL ----------
MODULE_URL_BUILDERS = {
    "inventario": lambda slug: reverse("inventario:home", kwargs={"project_slug": slug}),
    # "reportes": lambda slug: reverse("reportes:home", kwargs={"project_slug": slug}),
}

def module_url(module_code: str, project_slug: str):
    build = MODULE_URL_BUILDERS.get(module_code)
    if not build:
        return None
    try:
        return build(project_slug)
    except NoReverseMatch:
        return None

# ---------- Vistas ----------
@login_required(login_url="/app/login/")
def project_home(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)

    m = _require_member(project, request.user)
    if not m:
        return HttpResponseForbidden("No eres miembro de este proyecto.")

    pms = (
        project.project_modules
        .select_related("module")
        .filter(enabled=True)
        .order_by("id")
    )
    items = [{"name": pm.module.name, "code": pm.module.code, "url": module_url(pm.module.code, project.slug)} for pm in pms]

    can_invite = _require_admin_or_owner(project, request.user)

    context = {
        "project": project,
        "items": items,
        "can_invite": can_invite,
        "invite_form": InviteForm(),
        "used_seats": project.memberships.count(),
    }
    return render(request, "saas/project_home.html", context)

@login_required(login_url="/app/login/")
def toggle_module(request, project_slug, code):
    project = get_object_or_404(Project, slug=project_slug)
    if not _require_admin_or_owner(project, request.user):
        return HttpResponseForbidden("Necesitas rol admin/owner.")

    module = get_object_or_404(Module, code=code)
    pm, _ = ProjectModule.objects.get_or_create(project=project, module=module)
    pm.enabled = not pm.enabled
    pm.save()
    messages.success(request, f"Módulo {module.name} ahora está {'ON' if pm.enabled else 'OFF'}.")
    return redirect("project_home", project_slug=project.slug)

@login_required(login_url="/app/login/")
def create_invite(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if not _require_admin_or_owner(project, request.user):
        return HttpResponseForbidden("Necesitas rol admin/owner.")

    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            if not project.can_add_more_users():
                messages.error(request, "Has alcanzado el límite de usuarios del proyecto.")
                return redirect("project_home", project_slug=project.slug)

            inv = Invite.objects.create(
                project=project,
                email=form.cleaned_data["email"] or "",
                role=form.cleaned_data["role"],
                created_by=request.user,
            )
            join_url = settings.SITE_BASE_URL + reverse("join_project", args=[inv.token])
            return render(request, "saas/invite_created.html", {
                "project": project, "invite": inv, "join_url": join_url
            })
    else:
        form = InviteForm()

    return render(request, "saas/create_invite.html", {"project": project, "form": form})

def join_project(request, token: str):
    inv = get_object_or_404(Invite, token=token)
    if inv.is_expired:
        raise Http404("Invitación expirada.")

    if not request.user.is_authenticated:
        return redirect(f"/app/login/?next={request.path}")

    project = inv.project
    if Membership.objects.filter(project=project, user=request.user).exists():
        messages.info(request, "Ya eres miembro de este proyecto.")
        return redirect("project_home", project_slug=project.slug)

    if not project.can_add_more_users():
        return HttpResponse("El proyecto alcanzó su límite de usuarios.", status=400)

    Membership.objects.create(project=project, user=request.user, role=inv.role)
    inv.accepted_at = timezone.now()
    inv.save(update_fields=["accepted_at"])
    messages.success(request, f"Te uniste a {project.name} como {inv.role}.")
    return redirect("project_home", project_slug=project.slug)

def project_gate(request, project_slug):
    return HttpResponse("Módulo no disponible para este proyecto.", content_type="text/plain")
