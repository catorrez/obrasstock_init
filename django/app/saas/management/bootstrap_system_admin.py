from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

EXCLUDED_MODELS = [
    ("auth", "group"),       # admin de grupos
    ("saas", "module"),      # admin de módulos del sistema (ajusta si tu modelo difiere)
]

GROUP_NAME = "system_admin"

class Command(BaseCommand):
    help = "Crea el grupo 'system_admin' con todos los permisos excepto grupos y módulos"

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name=GROUP_NAME)

        # calcular content types excluidos
        excluded_cts = []
        for app_label, model in EXCLUDED_MODELS:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                excluded_cts.append(ct)
            except ContentType.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"[WARN] No existe ContentType para {app_label}.{model} (ok si aún no migraste esa app)"
                ))

        excluded_ct_ids = {ct.id for ct in excluded_cts}
        perms = Permission.objects.exclude(content_type_id__in=excluded_ct_ids)

        group.permissions.set(perms)
        group.save()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Grupo '{GROUP_NAME}' actualizado con {perms.count()} permisos (excluyendo grupos y módulos)."
        ))
        self.stdout.write(self.style.NOTICE(
            "Recuerda asignar usuarios al grupo 'system_admin'. El Dueño conserva todo por usuario propietario/superuser."
        ))
