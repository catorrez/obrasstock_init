from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from control_plane.models import Project
from control_plane.provisioning import ProjectProvisioningService


class Command(BaseCommand):
    help = 'Manage project users and modules'
    
    def add_arguments(self, parser):
        parser.add_argument('project_slug', type=str, help='Project slug')
        
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # Add user
        add_user_parser = subparsers.add_parser('add-user', help='Add user to project')
        add_user_parser.add_argument('username', type=str, help='Username to add')
        add_user_parser.add_argument('role', type=str, choices=['system_admin', 'project_admin', 'operator'], help='User role')
        add_user_parser.add_argument('--added-by', type=str, default='admin', help='Username of user performing action')
        
        # Remove user
        remove_user_parser = subparsers.add_parser('remove-user', help='Remove user from project')
        remove_user_parser.add_argument('username', type=str, help='Username to remove')
        remove_user_parser.add_argument('--removed-by', type=str, default='admin', help='Username of user performing action')
        
        # Change role
        change_role_parser = subparsers.add_parser('change-role', help='Change user role')
        change_role_parser.add_argument('username', type=str, help='Username')
        change_role_parser.add_argument('role', type=str, choices=['system_admin', 'project_admin', 'operator'], help='New role')
        change_role_parser.add_argument('--changed-by', type=str, default='admin', help='Username of user performing action')
        
        # Enable module
        enable_module_parser = subparsers.add_parser('enable-module', help='Enable module for project')
        enable_module_parser.add_argument('module', type=str, help='Module name')
        enable_module_parser.add_argument('--enabled-by', type=str, default='admin', help='Username of user performing action')
        
        # Disable module
        disable_module_parser = subparsers.add_parser('disable-module', help='Disable module for project')
        disable_module_parser.add_argument('module', type=str, help='Module name')
        disable_module_parser.add_argument('--disabled-by', type=str, default='admin', help='Username of user performing action')
        
        # List users
        subparsers.add_parser('list-users', help='List project users')
        
        # List modules
        subparsers.add_parser('list-modules', help='List project modules')
    
    def handle(self, *args, **options):
        project_slug = options['project_slug']
        action = options['action']
        
        # Get project
        try:
            project = Project.objects.get(slug=project_slug)
        except Project.DoesNotExist:
            raise CommandError(f'Project "{project_slug}" does not exist')
        
        # Execute action
        if action == 'add-user':
            self._add_user(project, options)
        elif action == 'remove-user':
            self._remove_user(project, options)
        elif action == 'change-role':
            self._change_role(project, options)
        elif action == 'enable-module':
            self._enable_module(project, options)
        elif action == 'disable-module':
            self._disable_module(project, options)
        elif action == 'list-users':
            self._list_users(project)
        elif action == 'list-modules':
            self._list_modules(project)
        else:
            raise CommandError(f'Unknown action: {action}')
    
    def _add_user(self, project, options):
        """Add user to project"""
        username = options['username']
        role = options['role']
        added_by_username = options['added_by']
        
        try:
            user = User.objects.get(username=username)
            added_by = User.objects.get(username=added_by_username)
            
            ProjectProvisioningService.add_user_to_project(
                project=project,
                user=user,
                role_name=role,
                added_by=added_by
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully added user "{username}" to project "{project.name}" with role "{role}"'
                )
            )
            
        except User.DoesNotExist as e:
            raise CommandError(f'User not found: {e}')
        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error adding user: {e}')
    
    def _remove_user(self, project, options):
        """Remove user from project"""
        username = options['username']
        removed_by_username = options['removed_by']
        
        try:
            user = User.objects.get(username=username)
            removed_by = User.objects.get(username=removed_by_username)
            
            ProjectProvisioningService.remove_user_from_project(
                project=project,
                user=user,
                removed_by=removed_by
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully removed user "{username}" from project "{project.name}"'
                )
            )
            
        except User.DoesNotExist as e:
            raise CommandError(f'User not found: {e}')
        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error removing user: {e}')
    
    def _change_role(self, project, options):
        """Change user role"""
        username = options['username']
        role = options['role']
        changed_by_username = options['changed_by']
        
        try:
            user = User.objects.get(username=username)
            changed_by = User.objects.get(username=changed_by_username)
            
            ProjectProvisioningService.change_user_role(
                project=project,
                user=user,
                new_role_name=role,
                changed_by=changed_by
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully changed role for user "{username}" to "{role}" in project "{project.name}"'
                )
            )
            
        except User.DoesNotExist as e:
            raise CommandError(f'User not found: {e}')
        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error changing role: {e}')
    
    def _enable_module(self, project, options):
        """Enable module for project"""
        module_name = options['module']
        enabled_by_username = options['enabled_by']
        
        try:
            enabled_by = User.objects.get(username=enabled_by_username)
            
            ProjectProvisioningService.enable_module(
                project=project,
                module_name=module_name,
                enabled_by=enabled_by
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully enabled module "{module_name}" for project "{project.name}"'
                )
            )
            
        except User.DoesNotExist as e:
            raise CommandError(f'User not found: {e}')
        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error enabling module: {e}')
    
    def _disable_module(self, project, options):
        """Disable module for project"""
        module_name = options['module']
        disabled_by_username = options['disabled_by']
        
        try:
            disabled_by = User.objects.get(username=disabled_by_username)
            
            ProjectProvisioningService.disable_module(
                project=project,
                module_name=module_name,
                disabled_by=disabled_by
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully disabled module "{module_name}" for project "{project.name}"'
                )
            )
            
        except User.DoesNotExist as e:
            raise CommandError(f'User not found: {e}')
        except ValidationError as e:
            raise CommandError(f'Validation error: {e}')
        except Exception as e:
            raise CommandError(f'Error disabling module: {e}')
    
    def _list_users(self, project):
        """List project users"""
        self.stdout.write(f'Users in project "{project.name}":')
        self.stdout.write(f'Owner: {project.owner.username} (owner)')
        
        memberships = project.memberships.select_related('user', 'role').filter(is_active=True)
        for membership in memberships:
            self.stdout.write(f'  {membership.user.username} ({membership.role.display_name})')
    
    def _list_modules(self, project):
        """List project modules"""
        self.stdout.write(f'Modules in project "{project.name}":')
        
        enabled_modules = project.enabled_modules.select_related('module').filter(is_enabled=True)
        for pm in enabled_modules:
            module_type = "core" if pm.module.is_core else "optional"
            self.stdout.write(f'  {pm.module.name} - {pm.module.display_name} ({module_type})')