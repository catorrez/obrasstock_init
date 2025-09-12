from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from control_plane.provisioning import ProjectProvisioningService
from control_plane.models import ModuleRegistry


class Command(BaseCommand):
    help = 'Create a new project with complete provisioning'
    
    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Project name')
        parser.add_argument('slug', type=str, help='Project slug (unique identifier)')
        parser.add_argument('owner_username', type=str, help='Username of project owner')
        
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Project description'
        )
        
        parser.add_argument(
            '--modules',
            type=str,
            nargs='*',
            help='Additional modules to enable (beyond core modules)'
        )
        
        parser.add_argument(
            '--list-modules',
            action='store_true',
            help='List available modules'
        )
    
    def handle(self, *args, **options):
        if options['list_modules']:
            self._list_modules()
            return
        
        name = options['name']
        slug = options['slug']
        owner_username = options['owner_username']
        description = options['description']
        modules = options['modules'] or []
        
        # Validate owner
        try:
            owner = User.objects.get(username=owner_username)
        except User.DoesNotExist:
            raise CommandError(f'User "{owner_username}" does not exist')
        
        # Create project
        try:
            project = ProjectProvisioningService.create_project(
                name=name,
                slug=slug,
                owner=owner,
                description=description,
                enabled_modules=modules
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created project "{project.name}" (slug: {project.slug})'
                )
            )
            
            # Show enabled modules
            enabled_modules = project.enabled_modules.select_related('module')
            self.stdout.write('\nEnabled modules:')
            for pm in enabled_modules:
                module_type = "core" if pm.module.is_core else "optional"
                self.stdout.write(f'  - {pm.module.display_name} ({module_type})')
            
            # Show database info
            self.stdout.write(f'\nDatabase: {project.database_name}')
            self.stdout.write(f'Owner: {project.owner.username}')
            
        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error creating project: {e}')
    
    def _list_modules(self):
        """List available modules"""
        self.stdout.write('Available modules:\n')
        
        core_modules = ModuleRegistry.objects.filter(is_core=True)
        optional_modules = ModuleRegistry.objects.filter(is_core=False)
        
        self.stdout.write(self.style.SUCCESS('Core modules (automatically enabled):'))
        for module in core_modules:
            self.stdout.write(f'  {module.name} - {module.display_name}')
            self.stdout.write(f'    {module.description}')
        
        self.stdout.write(self.style.WARNING('\nOptional modules:'))
        for module in optional_modules:
            self.stdout.write(f'  {module.name} - {module.display_name}')
            self.stdout.write(f'    {module.description}')