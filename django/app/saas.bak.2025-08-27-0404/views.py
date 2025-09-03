from datetime import timedelta
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Invite, Project, Membership, ProjectRole, ProjectModule

@login_required
def join_project(request, token):
    invite = get_object_or_404(Invite, token=token)
    if invite.expires_at < timezone.now():
        return HttpResponseForbidden("Invitación expirada")
    project = invite.project
    Membership.objects.get_or_create(project=project, user=request.user,
                                     defaults={"role": invite.role})
    if not invite.accepted_at:
        invite.accepted_at = timezone.now(); invite.save(update_fields=["accepted_at"])
    return redirect(f"/p/{project.slug}/")

@login_required
def project_gate(request, project_slug):
    # Punto de entrada genérico al proyecto (puede redirigir a la sección que quieras)
    project = get_object_or_404(Project, slug=project_slug)
    if not Membership.objects.filter(project=project, user=request.user).exists() and request.user != project.owner:
        return HttpResponseForbidden("No tienes acceso a este proyecto")
    # Redirige a algo útil (por ahora, admin del proyecto -> admin inventario)
    return redirect(f"/admin/")

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponseForbidden
from .models import Project, Invite, Membership, ProjectModule, ProjectRole  # ajusta si algún modelo cambia

def user_is_owner_or_admin(user, project):
    # dueñ@ directo
    if getattr(project, "owner_id", None) == user.id:
        return True
    # si Membership.role es FK a ProjectRole y ProjectRole tiene 'name'
    if Membership.objects.filter(project=project, user=user, role__name__in=["OWNER","ADMIN"]).exists():
        return True
    # si tu ProjectRole tiene otra bandera (p.ej. is_admin), descomenta:
    # if Membership.objects.filter(project=project, user=user, role__is_admin=True).exists():
    #     return True
    return False

@login_required
def project_home(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if not (request.user == project.owner or Membership.objects.filter(project=project, user=request.user).exists()):
        return HttpResponseForbidden("No tienes acceso a este proyecto")
    mods = ProjectModule.objects.filter(project=project).order_by("module")
    return render(request, "saas/project_home.html", {"project": project, "mods": mods})

@login_required
def create_invite(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if not (request.user == project.owner or Membership.objects.filter(project=project, user=request.user).exists()):
        return HttpResponseForbidden("No tienes acceso a este proyecto")

    # rol por defecto
    default_role = getattr(ProjectRole, "MEMBER", "MEMBER")
    role = request.GET.get("role") or default_role

    token = uuid.uuid4().hex
    expires_at = timezone.now() + timedelta(days=7)
    Invite.objects.create(project=project, token=token, role=role, expires_at=expires_at)

    invite_url = f"{settings.SITE_BASE_URL}/join/{token}/"
    messages.success(request, f"Invitación creada: {invite_url} (vence en 7 días)")
    return redirect("project_home", project_slug=project.slug)

@login_required
def toggle_module(request, project_slug, code):
    project = get_object_or_404(Project, slug=project_slug)
    if not (request.user == project.owner or Membership.objects.filter(project=project, user=request.user).exists()):
        return HttpResponseForbidden("No tienes acceso a este proyecto")
    pm, _ = ProjectModule.objects.get_or_create(project=project, module=code)
    pm.enabled = not pm.enabled
    pm.save(update_fields=["enabled"])
    return redirect("project_home", project_slug=project.slug)
