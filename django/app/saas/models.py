# saas/models.py
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

import secrets

def default_invite_expires_at():
    # Ej: vence a 7 días
    return timezone.now() + timedelta(days=7)

def default_invite_token():
    # Token seguro para invitaciones
    return secrets.token_urlsafe(32)

User = get_user_model()


class Project(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_projects")
    user_limit = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    def can_add_more_users(self) -> bool:
        return self.memberships.count() < self.user_limit


class ProjectRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    OPERATOR = "operator", "Operator"
    VIEWER = "viewer", "Viewer"


class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=ProjectRole.choices, default=ProjectRole.OPERATOR)

    # permitir nulos para migrar sin “default”
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = [("project", "user")]
        ordering = ["id"]

    def __str__(self):
        return f"{self.user} → {self.project} ({self.role})"

    @property
    def is_owner(self) -> bool:
        return self.role == ProjectRole.OWNER or self.user_id == self.project.owner_id


class Module(models.Model):
    code = models.SlugField(unique=True, max_length=50)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class ProjectModule(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_modules")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="project_modules")
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "module"], name="uniq_project_module")
        ]
        ordering = ["id"]

    def __str__(self):
        return f"{self.project} · {self.module} ({'on' if self.enabled else 'off'})"


class Invite(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="invites")
    email = models.EmailField(blank=True)
    token = models.CharField(max_length=52, unique=True, db_index=True, default=default_invite_token)
    role = models.CharField(max_length=20, choices=ProjectRole.choices, default=ProjectRole.OPERATOR)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_invites")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    expires_at = models.DateTimeField(default=default_invite_expires_at)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite {self.project} · {self.email or 'link'}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
