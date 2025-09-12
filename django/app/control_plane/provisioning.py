from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import (
    Project, ProjectMembership, RoleType, ModuleRegistry, 
    ProjectModule, AuditLog
)
from .router import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class ProjectProvisioningService:
    """
    Service for creating and managing projects with complete provisioning.
    """
    
    @staticmethod
    @transaction.atomic
    def create_project(name, slug, owner, description="", enabled_modules=None):
        """
        Create a new project with complete provisioning.
        
        Args:
            name (str): Project display name
            slug (str): Project slug (must be unique)
            owner (User): Project owner
            description (str): Project description
            enabled_modules (list): List of module names to enable
            
        Returns:
            Project: Created project instance
        """
        # Validate inputs
        if not name or not slug or not owner:
            raise ValidationError("Name, slug, and owner are required")
        
        if Project.objects.filter(slug=slug).exists():
            raise ValidationError(f"Project with slug '{slug}' already exists")
        
        try:
            # 1. Create project record
            project = Project.objects.create(
                name=name,
                slug=slug,
                owner=owner,
                description=description,
                status='active'
            )
            
            # 2. Create project database
            if not DatabaseManager.create_project_database(slug):
                raise Exception(f"Failed to create database for project {slug}")
            
            # 3. Set up owner membership
            owner_role = RoleType.objects.get(name='owner')
            ProjectMembership.objects.create(
                project=project,
                user=owner,
                role=owner_role,
                added_by=owner
            )
            
            # 4. Enable core modules
            core_modules = ModuleRegistry.objects.filter(is_core=True)
            for module in core_modules:
                ProjectModule.objects.create(
                    project=project,
                    module=module,
                    is_enabled=True,
                    enabled_by=owner
                )
            
            # 5. Enable additional modules if specified
            if enabled_modules:
                additional_modules = ModuleRegistry.objects.filter(
                    name__in=enabled_modules,
                    is_core=False
                )
                for module in additional_modules:
                    ProjectModule.objects.create(
                        project=project,
                        module=module,
                        is_enabled=True,
                        enabled_by=owner
                    )
            
            # 6. Log the creation
            AuditLog.objects.create(
                action='create_project',
                user=owner,
                project=project,
                details={
                    'project_name': name,
                    'project_slug': slug,
                    'enabled_modules': list(project.enabled_modules.values_list('module__name', flat=True))
                }
            )
            
            logger.info(f"Successfully created project '{name}' (slug: {slug}) for user {owner.username}")
            
            return project
            
        except Exception as e:
            logger.error(f"Failed to create project '{name}': {str(e)}")
            
            # Cleanup: Remove database if project creation failed
            try:
                if 'project' in locals():
                    DatabaseManager.delete_project_database(slug)
            except:
                pass
            
            raise e
    
    @staticmethod
    @transaction.atomic
    def delete_project(project, deleted_by):
        """
        Delete a project and all associated resources.
        
        Args:
            project (Project): Project to delete
            deleted_by (User): User performing the deletion
        """
        try:
            project_name = project.name
            project_slug = project.slug
            
            # 1. Log the deletion
            AuditLog.objects.create(
                action='delete_project',
                user=deleted_by,
                project=project,
                details={
                    'project_name': project_name,
                    'project_slug': project_slug
                }
            )
            
            # 2. Delete project database
            DatabaseManager.delete_project_database(project_slug)
            
            # 3. Delete project record (cascade will handle related objects)
            project.delete()
            
            logger.info(f"Successfully deleted project '{project_name}' (slug: {project_slug})")
            
        except Exception as e:
            logger.error(f"Failed to delete project '{project.name}': {str(e)}")
            raise e
    
    @staticmethod
    @transaction.atomic
    def add_user_to_project(project, user, role_name, added_by):
        """
        Add a user to a project with specified role.
        
        Args:
            project (Project): Target project
            user (User): User to add
            role_name (str): Role name (owner, system_admin, project_admin, operator)
            added_by (User): User performing the action
        """
        try:
            # Check if user is already a member
            if ProjectMembership.objects.filter(project=project, user=user).exists():
                raise ValidationError(f"User {user.username} is already a member of {project.name}")
            
            # Get role
            role = RoleType.objects.get(name=role_name)
            
            # Create membership
            membership = ProjectMembership.objects.create(
                project=project,
                user=user,
                role=role,
                added_by=added_by
            )
            
            # Log the action
            AuditLog.objects.create(
                action='add_user',
                user=added_by,
                project=project,
                target_user=user,
                details={
                    'role': role_name,
                    'username': user.username
                }
            )
            
            logger.info(f"Added user {user.username} to project {project.name} with role {role_name}")
            
            return membership
            
        except Exception as e:
            logger.error(f"Failed to add user {user.username} to project {project.name}: {str(e)}")
            raise e
    
    @staticmethod
    @transaction.atomic
    def remove_user_from_project(project, user, removed_by):
        """
        Remove a user from a project.
        
        Args:
            project (Project): Target project
            user (User): User to remove
            removed_by (User): User performing the action
        """
        try:
            # Cannot remove the project owner
            if project.owner == user:
                raise ValidationError("Cannot remove the project owner")
            
            # Get membership
            membership = ProjectMembership.objects.get(project=project, user=user)
            
            # Log the action
            AuditLog.objects.create(
                action='remove_user',
                user=removed_by,
                project=project,
                target_user=user,
                details={
                    'role': membership.role.name,
                    'username': user.username
                }
            )
            
            # Remove membership
            membership.delete()
            
            logger.info(f"Removed user {user.username} from project {project.name}")
            
        except ProjectMembership.DoesNotExist:
            raise ValidationError(f"User {user.username} is not a member of {project.name}")
        except Exception as e:
            logger.error(f"Failed to remove user {user.username} from project {project.name}: {str(e)}")
            raise e
    
    @staticmethod
    @transaction.atomic
    def change_user_role(project, user, new_role_name, changed_by):
        """
        Change a user's role in a project.
        
        Args:
            project (Project): Target project
            user (User): User whose role to change
            new_role_name (str): New role name
            changed_by (User): User performing the action
        """
        try:
            # Cannot change the project owner's role
            if project.owner == user:
                raise ValidationError("Cannot change the project owner's role")
            
            # Get membership and new role
            membership = ProjectMembership.objects.get(project=project, user=user)
            old_role = membership.role.name
            new_role = RoleType.objects.get(name=new_role_name)
            
            # Update role
            membership.role = new_role
            membership.save()
            
            # Log the action
            AuditLog.objects.create(
                action='change_role',
                user=changed_by,
                project=project,
                target_user=user,
                details={
                    'old_role': old_role,
                    'new_role': new_role_name,
                    'username': user.username
                }
            )
            
            logger.info(f"Changed role for user {user.username} in project {project.name} from {old_role} to {new_role_name}")
            
            return membership
            
        except ProjectMembership.DoesNotExist:
            raise ValidationError(f"User {user.username} is not a member of {project.name}")
        except Exception as e:
            logger.error(f"Failed to change role for user {user.username} in project {project.name}: {str(e)}")
            raise e
    
    @staticmethod
    @transaction.atomic
    def enable_module(project, module_name, enabled_by):
        """
        Enable a module for a project.
        
        Args:
            project (Project): Target project
            module_name (str): Module name to enable
            enabled_by (User): User performing the action
        """
        try:
            # Get module
            module = ModuleRegistry.objects.get(name=module_name)
            
            # Check if already enabled
            project_module, created = ProjectModule.objects.get_or_create(
                project=project,
                module=module,
                defaults={
                    'is_enabled': True,
                    'enabled_by': enabled_by
                }
            )
            
            if not created and project_module.is_enabled:
                raise ValidationError(f"Module {module_name} is already enabled for project {project.name}")
            
            if not created:
                project_module.is_enabled = True
                project_module.enabled_by = enabled_by
                project_module.save()
            
            # Log the action
            AuditLog.objects.create(
                action='enable_module',
                user=enabled_by,
                project=project,
                details={
                    'module_name': module_name
                }
            )
            
            logger.info(f"Enabled module {module_name} for project {project.name}")
            
            return project_module
            
        except ModuleRegistry.DoesNotExist:
            raise ValidationError(f"Module {module_name} does not exist")
        except Exception as e:
            logger.error(f"Failed to enable module {module_name} for project {project.name}: {str(e)}")
            raise e
    
    @staticmethod
    @transaction.atomic
    def disable_module(project, module_name, disabled_by):
        """
        Disable a module for a project.
        
        Args:
            project (Project): Target project
            module_name (str): Module name to disable
            disabled_by (User): User performing the action
        """
        try:
            # Get module
            module = ModuleRegistry.objects.get(name=module_name)
            
            # Cannot disable core modules
            if module.is_core:
                raise ValidationError(f"Cannot disable core module {module_name}")
            
            # Get project module
            project_module = ProjectModule.objects.get(project=project, module=module)
            
            if not project_module.is_enabled:
                raise ValidationError(f"Module {module_name} is already disabled for project {project.name}")
            
            # Disable module
            project_module.is_enabled = False
            project_module.save()
            
            # Log the action
            AuditLog.objects.create(
                action='disable_module',
                user=disabled_by,
                project=project,
                details={
                    'module_name': module_name
                }
            )
            
            logger.info(f"Disabled module {module_name} for project {project.name}")
            
            return project_module
            
        except (ModuleRegistry.DoesNotExist, ProjectModule.DoesNotExist):
            raise ValidationError(f"Module {module_name} is not enabled for project {project.name}")
        except Exception as e:
            logger.error(f"Failed to disable module {module_name} for project {project.name}: {str(e)}")
            raise e