from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# Ajusta si tu modelo de módulos tiene otro nombre o app_label
EXCLUDED_MODELS = [
    ("auth", "group"),   # administración de grupos
    ("saas", "module"),  # administración de módulos (si tu modelo difiere, cámbialo)
]

GROUP_NAME = "system_admin"

class Command(BaseCommand):
    help = "Crea/actualiza el grupo system_admin con todos los permisos excepto grupos y módulos"

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name=GROUP_NAME)

        excluded_cts = []
        for app_label, model in EXCLUDED_MODELS:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                excluded_cts.append(ct)
            except ContentType.DoesNotExist:
                self.stdout.write("[WARN] No existe ContentType para %s.%s (ok si aún no migraste esa app/modelo)" % (app_label, model))

        excluded_ids = {ct.id for ct in excluded_cts}
        perms_qs = Permission.objects.all()
        if excluded_ids:
            perms_qs = perms_qs.exclude(content_type_id__in=excluded_ids)

        group.permissions.set(perms_qs)
        group.save()

        self.stdout.write("OK: Grupo %s actualizado con %d permisos (excluyendo grupos y módulos)." % (GROUP_NAME, perms_qs.count()))
        self.stdout.write("Recuerda: asigna usuarios al grupo system_admin.")
