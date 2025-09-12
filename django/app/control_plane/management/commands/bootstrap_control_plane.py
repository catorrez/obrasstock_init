from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from control_plane.models import (
    ModuleRegistry, RoleType
)


class Command(BaseCommand):
    help = '''Bootstrap Control Plane with initial data (roles and modules)
    
    NOTE: The roles created here are for project membership display/tracking only.
    Actual access control is handled by Django Groups and UserTypeService.'''
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing data before bootstrapping',
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting existing Control Plane data...'))
            self._reset_data()
        
        self.stdout.write('Bootstrapping Control Plane...')
        
        with transaction.atomic():
            self._create_roles()
            self._create_modules()
        
        self.stdout.write(self.style.SUCCESS('Control Plane bootstrap completed successfully!'))
    
    def _reset_data(self):
        """Reset existing data"""
        ModuleRegistry.objects.all().delete()
        RoleType.objects.all().delete()
    
    def _create_roles(self):
        """Create role types"""
        roles = [
            {
                'name': 'owner',
                'display_name': 'Owner',
                'description': 'Full system access, can manage all aspects of the platform',
                'level': 1
            },
            {
                'name': 'system_admin',
                'display_name': 'System Admin',
                'description': 'Administrative access across projects, can manage users and settings',
                'level': 2
            },
            {
                'name': 'project_admin',
                'display_name': 'Project Admin',
                'description': 'Full access within assigned projects, can manage project users and data',
                'level': 3
            },
            {
                'name': 'operator',
                'display_name': 'Operator',
                'description': 'Standard user access, can perform day-to-day operations within assigned projects',
                'level': 4
            }
        ]
        
        for role_data in roles:
            role, created = RoleType.objects.get_or_create(
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                self.stdout.write('Created role: {}'.format(role.display_name))
            else:
                self.stdout.write('Role already exists: {}'.format(role.display_name))
    
    def _create_modules(self):
        """Create module registry"""
        modules = [
            {
                'name': 'control_plane',
                'display_name': 'Control Plane',
                'description': 'Project and user management',
                'is_core': True
            },
            {
                'name': 'inventario',
                'display_name': 'Inventario',
                'description': 'Stock and inventory tracking system',
                'is_core': True
            },
            {
                'name': 'saas',
                'display_name': 'SaaS',
                'description': 'Multi-tenant project management',
                'is_core': True
            }
        ]
        
        for module_data in modules:
            module, created = ModuleRegistry.objects.get_or_create(
                name=module_data['name'],
                defaults=module_data
            )
            if created:
                self.stdout.write('Created module: {}'.format(module.display_name))
            else:
                self.stdout.write('Module already exists: {}'.format(module.display_name))
    
