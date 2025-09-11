from django.core.management.base import BaseCommand
from saas.roles import assign_system_admin_perms

class Command(BaseCommand):
    help = "Crea/actualiza el grupo 'system_admin' con permisos correctos"

    def handle(self, *args, **options):
        g = assign_system_admin_perms()
        self.stdout.write(self.style.SUCCESS(
            f"Grupo '{g.name}' listo con {g.permissions.count()} permisos."
        ))
