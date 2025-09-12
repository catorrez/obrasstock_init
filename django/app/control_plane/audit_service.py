"""
Comprehensive Audit Logging Service for Owner-level visibility
"""
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpRequest
from django.utils import timezone
from .models import AuditLog, Project
import logging
import json
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class AuditService:
    """
    Centralized service for creating comprehensive audit logs.
    Provides Owner-level visibility into all system operations.
    """
    
    @staticmethod
    def get_request_context(request: Optional[HttpRequest] = None) -> Dict[str, Any]:
        """Extract request context for audit logging"""
        if not request:
            return {}
            
        return {
            'ip_address': AuditService.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'request_path': request.path,
            'request_method': request.method,
            'referer': request.META.get('HTTP_REFERER', ''),
            'session_key': request.session.session_key or '',
        }
    
    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    @staticmethod
    def get_user_context(user: Optional[User]) -> Dict[str, Any]:
        """Extract user context for audit logging"""
        if not user or not user.is_authenticated:
            return {}
            
        return {
            'username': user.username,
            'user_email': user.email,
        }
    
    @staticmethod
    def log_action(
        action: str,
        user: Optional[User] = None,
        project: Optional[Project] = None,
        target_user: Optional[User] = None,
        target_object: Optional[models.Model] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        details: Optional[Dict] = None,
        request: Optional[HttpRequest] = None,
        severity: str = 'low',
        success: bool = True,
        error_message: str = '',
    ) -> AuditLog:
        """
        Create a comprehensive audit log entry.
        
        Args:
            action: The action being performed (must be in ACTION_CHOICES)
            user: User performing the action
            project: Project context (if applicable)
            target_user: User being acted upon (if applicable)
            target_object: Object being acted upon (if applicable)
            old_values: Previous values (for updates)
            new_values: New values (for updates)
            details: Additional context information
            request: HTTP request object
            severity: Severity level (low, medium, high, critical)
            success: Whether the operation succeeded
            error_message: Error message if operation failed
        """
        # Prepare audit log data
        audit_data = {
            'action': action,
            'severity': severity,
            'success': success,
            'error_message': error_message,
            'timestamp': timezone.now(),
        }
        
        # Add user context
        if user:
            audit_data['user'] = user
            audit_data.update(AuditService.get_user_context(user))
        
        # Add project context
        if project:
            audit_data['project'] = project
            audit_data['project_slug'] = project.slug
        
        # Add target user context
        if target_user:
            audit_data['target_user'] = target_user
        
        # Add target object context
        if target_object:
            audit_data.update({
                'target_object_type': target_object.__class__.__name__,
                'target_object_id': str(target_object.pk),
                'target_object_repr': str(target_object)[:500],  # Limit length
            })
        
        # Add request context
        if request:
            audit_data.update(AuditService.get_request_context(request))
        
        # Add change tracking
        if old_values:
            audit_data['old_values'] = old_values
        if new_values:
            audit_data['new_values'] = new_values
        
        # Add additional details
        if details:
            audit_data['details'] = details
        else:
            audit_data['details'] = {}
        
        try:
            # Create audit log entry
            audit_log = AuditLog.objects.create(**audit_data)
            
            # Log to standard logging as well for real-time monitoring
            log_message = f"AUDIT: {action} by {user} on {target_object or project or 'system'}"
            if severity == 'critical':
                logger.critical(log_message)
            elif severity == 'high':
                logger.error(log_message)
            elif severity == 'medium':
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            return audit_log
            
        except Exception as e:
            # Ensure audit logging never breaks the application
            logger.error(f"Failed to create audit log: {e}")
            logger.error(f"Audit data: {audit_data}")
            raise
    
    @staticmethod
    def log_authentication(action: str, user: Optional[User] = None, username: str = '', 
                         request: Optional[HttpRequest] = None, success: bool = True, 
                         error_message: str = '') -> AuditLog:
        """Log authentication events"""
        severity = 'high' if action == 'login_failed' else 'medium'
        
        details = {}
        if username and not user:
            details['attempted_username'] = username
        
        return AuditService.log_action(
            action=action,
            user=user,
            details=details,
            request=request,
            severity=severity,
            success=success,
            error_message=error_message,
        )
    
    @staticmethod
    def log_model_change(action: str, instance: models.Model, user: Optional[User] = None,
                        old_values: Optional[Dict] = None, new_values: Optional[Dict] = None,
                        request: Optional[HttpRequest] = None) -> AuditLog:
        """Log model CRUD operations"""
        # Determine project context if available
        project = None
        if hasattr(instance, 'project'):
            project = instance.project
        elif hasattr(instance, 'get_project'):
            project = instance.get_project()
        
        # Determine severity based on model type and action
        severity = 'low'
        if instance.__class__.__name__ in ['User', 'Project', 'ProjectMembership']:
            severity = 'high'
        elif action == 'delete_record':
            severity = 'medium'
        
        return AuditService.log_action(
            action=action,
            user=user,
            project=project,
            target_object=instance,
            old_values=old_values,
            new_values=new_values,
            request=request,
            severity=severity,
        )
    
    @staticmethod
    def log_admin_action(action: str, user: User, target_object: models.Model,
                        change_message: str = '', request: Optional[HttpRequest] = None) -> AuditLog:
        """Log Django admin actions"""
        return AuditService.log_action(
            action='system_config_change' if 'config' in action.lower() else action,
            user=user,
            target_object=target_object,
            details={'change_message': change_message, 'admin_action': True},
            request=request,
            severity='high',  # Admin actions are always high severity
        )
    
    @staticmethod
    def log_project_access(user: User, project: Project, request: HttpRequest) -> AuditLog:
        """Log when users access projects"""
        return AuditService.log_action(
            action='project_access',
            user=user,
            project=project,
            request=request,
            details={'access_type': 'web_interface'},
            severity='low',
        )
    
    @staticmethod
    def log_unauthorized_access(user: Optional[User] = None, username: str = '',
                              attempted_resource: str = '', request: Optional[HttpRequest] = None) -> AuditLog:
        """Log unauthorized access attempts"""
        details = {
            'attempted_resource': attempted_resource,
            'attempted_username': username,
        }
        
        return AuditService.log_action(
            action='unauthorized_access_attempt',
            user=user,
            details=details,
            request=request,
            severity='critical',
            success=False,
        )
    
    @staticmethod
    def log_data_export(user: User, export_type: str, record_count: int = 0,
                       project: Optional[Project] = None, request: Optional[HttpRequest] = None) -> AuditLog:
        """Log data export operations"""
        return AuditService.log_action(
            action='export_data',
            user=user,
            project=project,
            details={
                'export_type': export_type,
                'record_count': record_count,
            },
            request=request,
            severity='medium',
        )
    
    @staticmethod
    def log_bulk_operation(user: User, operation_type: str, affected_count: int,
                          project: Optional[Project] = None, request: Optional[HttpRequest] = None) -> AuditLog:
        """Log bulk operations"""
        return AuditService.log_action(
            action='bulk_operation',
            user=user,
            project=project,
            details={
                'operation_type': operation_type,
                'affected_count': affected_count,
            },
            request=request,
            severity='medium' if affected_count < 100 else 'high',
        )


class AuditQueryHelper:
    """Helper class for querying audit logs with owner-level visibility"""
    
    @staticmethod
    def get_all_logs_for_owner(user: User, limit: int = 1000):
        """Get all audit logs visible to an owner"""
        if not user.is_superuser:
            # Non-owners can only see logs for their projects
            owned_projects = Project.objects.filter(owner=user)
            return AuditLog.objects.filter(
                models.Q(project__in=owned_projects) | models.Q(user=user)
            ).order_by('-timestamp')[:limit]
        else:
            # Owners can see everything
            return AuditLog.objects.all().order_by('-timestamp')[:limit]
    
    @staticmethod
    def get_security_logs(user: User, days: int = 30):
        """Get security-related audit logs"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        
        security_actions = [
            'user_login', 'user_logout', 'login_failed', 'admin_login',
            'unauthorized_access_attempt', 'account_locked', 'account_unlocked',
            'password_change', 'password_reset'
        ]
        
        base_query = AuditLog.objects.filter(
            action__in=security_actions,
            timestamp__gte=cutoff_date
        )
        
        if user.is_superuser:
            return base_query.order_by('-timestamp')
        else:
            owned_projects = Project.objects.filter(owner=user)
            return base_query.filter(
                models.Q(project__in=owned_projects) | models.Q(user=user)
            ).order_by('-timestamp')
    
    @staticmethod
    def get_high_severity_logs(user: User, days: int = 7):
        """Get high and critical severity logs"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        
        base_query = AuditLog.objects.filter(
            severity__in=['high', 'critical'],
            timestamp__gte=cutoff_date
        )
        
        if user.is_superuser:
            return base_query.order_by('-timestamp')
        else:
            owned_projects = Project.objects.filter(owner=user)
            return base_query.filter(
                models.Q(project__in=owned_projects) | models.Q(user=user)
            ).order_by('-timestamp')