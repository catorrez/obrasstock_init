"""
Django signals for automatic audit logging
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.admin.models import LogEntry
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import models
from django.core.serializers import serialize
import json
import threading
from .audit_service import AuditService
from .models import Project, ProjectMembership, RoleType, ModuleRegistry, ProjectModule

# Thread-local storage for request context
_thread_locals = threading.local()


def get_current_request():
    """Get the current request from thread-local storage"""
    return getattr(_thread_locals, 'request', None)


def set_current_request(request):
    """Set the current request in thread-local storage"""
    _thread_locals.request = request


def get_current_user():
    """Get the current user from thread-local storage"""
    request = get_current_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def get_model_fields(instance):
    """Get all fields and values from a model instance"""
    fields = {}
    for field in instance._meta.fields:
        field_name = field.name
        field_value = getattr(instance, field_name)
        
        # Convert non-serializable values
        if hasattr(field_value, 'pk'):  # ForeignKey
            fields[field_name] = str(field_value.pk)
            fields[f'{field_name}_repr'] = str(field_value)
        elif isinstance(field_value, (list, dict)):
            fields[field_name] = field_value
        else:
            fields[field_name] = str(field_value) if field_value is not None else None
    
    return fields


# Store previous values for updates
_pre_save_values = {}


@receiver(pre_save)
def capture_pre_save_values(sender, instance, **kwargs):
    """Capture values before save for comparison"""
    if instance.pk:  # Only for updates, not creates
        try:
            original = sender.objects.get(pk=instance.pk)
            _pre_save_values[f"{sender.__name__}_{instance.pk}"] = get_model_fields(original)
        except sender.DoesNotExist:
            pass


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """Log model creation and updates"""
    # Skip audit logs to avoid infinite recursion
    if sender.__name__ == 'AuditLog':
        return
    
    # Skip Django's built-in models we don't care about
    skip_models = ['Session', 'ContentType', 'Permission', 'LogEntry']
    if sender.__name__ in skip_models:
        return
    
    user = get_current_user()
    request = get_current_request()
    
    if created:
        action = 'create_record'
        old_values = None
        new_values = get_model_fields(instance)
    else:
        action = 'update_record'
        key = f"{sender.__name__}_{instance.pk}"
        old_values = _pre_save_values.pop(key, None)
        new_values = get_model_fields(instance)
    
    try:
        AuditService.log_model_change(
            action=action,
            instance=instance,
            user=user,
            old_values=old_values,
            new_values=new_values,
            request=request,
        )
    except Exception as e:
        # Don't let audit logging break the application
        import logging
        logging.getLogger(__name__).error(f"Failed to log model change: {e}")


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """Log model deletions"""
    # Skip audit logs to avoid issues
    if sender.__name__ == 'AuditLog':
        return
    
    skip_models = ['Session', 'ContentType', 'Permission', 'LogEntry']
    if sender.__name__ in skip_models:
        return
    
    user = get_current_user()
    request = get_current_request()
    
    try:
        AuditService.log_model_change(
            action='delete_record',
            instance=instance,
            user=user,
            old_values=get_model_fields(instance),
            new_values=None,
            request=request,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log model deletion: {e}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log successful user logins"""
    try:
        AuditService.log_authentication(
            action='user_login',
            user=user,
            request=request,
            success=True,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log user login: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logouts"""
    try:
        AuditService.log_authentication(
            action='user_logout',
            user=user,
            request=request,
            success=True,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log user logout: {e}")


@receiver(user_login_failed)
def log_login_failure(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    try:
        username = credentials.get('username', '')
        AuditService.log_authentication(
            action='login_failed',
            username=username,
            request=request,
            success=False,
            error_message='Invalid credentials',
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log login failure: {e}")


# Specific signals for important control plane operations
@receiver(post_save, sender=Project)
def log_project_changes(sender, instance, created, **kwargs):
    """Log project-specific changes with enhanced details"""
    user = get_current_user()
    request = get_current_request()
    
    if created:
        action = 'create_project'
    else:
        action = 'update_project'
    
    details = {
        'project_name': instance.name,
        'project_slug': instance.slug,
        'project_status': instance.status,
        'owner': instance.owner.username if instance.owner else None,
    }
    
    try:
        AuditService.log_action(
            action=action,
            user=user,
            project=instance,
            details=details,
            request=request,
            severity='high',
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log project change: {e}")


@receiver(post_save, sender=ProjectMembership)
def log_membership_changes(sender, instance, created, **kwargs):
    """Log project membership changes"""
    user = get_current_user()
    request = get_current_request()
    
    if created:
        action = 'add_user'
    else:
        action = 'change_role'
    
    details = {
        'project_name': instance.project.name,
        'target_username': instance.user.username,
        'role': instance.role.name,
        'is_active': instance.is_active,
    }
    
    try:
        AuditService.log_action(
            action=action,
            user=user,
            project=instance.project,
            target_user=instance.user,
            details=details,
            request=request,
            severity='high',
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log membership change: {e}")


@receiver(post_delete, sender=ProjectMembership)
def log_membership_removal(sender, instance, **kwargs):
    """Log project membership removal"""
    user = get_current_user()
    request = get_current_request()
    
    details = {
        'project_name': instance.project.name,
        'removed_username': instance.user.username,
        'role': instance.role.name,
    }
    
    try:
        AuditService.log_action(
            action='remove_user',
            user=user,
            project=instance.project,
            target_user=instance.user,
            details=details,
            request=request,
            severity='high',
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log membership removal: {e}")


@receiver(post_save, sender=LogEntry)
def log_admin_actions(sender, instance, created, **kwargs):
    """Log Django admin actions"""
    if not created:
        return
    
    try:
        # Get the admin user
        user = instance.user
        
        # Determine the action
        if instance.action_flag == 1:  # ADDITION
            action = 'create_record'
        elif instance.action_flag == 2:  # CHANGE
            action = 'update_record'
        elif instance.action_flag == 3:  # DELETION
            action = 'delete_record'
        else:
            action = 'admin_action'
        
        # Get the target object if it still exists
        target_object = None
        try:
            if instance.content_type and instance.object_id:
                model_class = instance.content_type.model_class()
                if model_class:
                    target_object = model_class.objects.get(pk=instance.object_id)
        except Exception:
            pass
        
        details = {
            'admin_action': True,
            'change_message': instance.change_message,
            'object_repr': instance.object_repr,
            'content_type': str(instance.content_type) if instance.content_type else None,
        }
        
        AuditService.log_action(
            action=action,
            user=user,
            target_object=target_object,
            details=details,
            severity='high',  # Admin actions are always high severity
        )
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to log admin action: {e}")