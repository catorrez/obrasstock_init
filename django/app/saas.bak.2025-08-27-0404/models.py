from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from secrets import token_urlsafe

User = get_user_model()

class Project(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80, unique=True)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="owned_projects")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:80]
        super().save(*args, **kwargs)

    def __str__(self): return self.name

class ProjectRole(models.TextChoices):
    OWNER = "OWNER", "Dueño"
    ADMIN = "ADMIN", "Administrador"
    STAFF = "STAFF", "Operador"
    VIEW  = "VIEW",  "Consulta"

class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ProjectRole.choices, default=ProjectRole.STAFF)

    class Meta:
        unique_together = (("project","user"),)

    def __str__(self): return f"{self.user} @ {self.project} ({self.role})"

class Module(models.TextChoices):
    INVENTARIO = "INVENTARIO", "Inventario"
    NOTA_PEDIDO = "NOTA_PEDIDO", "Notas de Pedido"
    TRASPASOS   = "TRASPASOS",   "Traspasos"

class ProjectModule(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="modules")
    module  = models.CharField(max_length=20, choices=Module.choices)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = (("project","module"),)

class Invite(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    email   = models.EmailField()
    role    = models.CharField(max_length=10, choices=ProjectRole.choices, default=ProjectRole.STAFF)
    token   = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=14)
        super().save(*args, **kwargs)

    def __str__(self): return f"Invite {self.email} -> {self.project}"
