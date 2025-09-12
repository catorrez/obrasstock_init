"""
Audit Logging Middleware for comprehensive request tracking
"""
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from django.urls import resolve
from django.http import HttpRequest, HttpResponse
from .audit_service import AuditService
from .signals import set_current_request
import logging
import time
import json

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to capture all HTTP requests for audit logging.
    Provides comprehensive request tracking for Owner visibility.
    """
    
    # Sensitive paths that should always be logged
    SENSITIVE_PATHS = [
        '/admin/',
        '/owner-console/',
        '/api/',
        '/control-plane/',
    ]
    
    # Paths to skip logging (to avoid noise)
    SKIP_PATHS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/health/',
        '/ping/',
    ]
    
    # HTTP methods that indicate data modification
    MODIFICATION_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_request(self, request):
        """Process incoming request"""
        # Set request in thread-local storage for signals
        set_current_request(request)
        
        # Add start time for performance tracking
        request._audit_start_time = time.time()
        
        return None
    
    def process_response(self, request, response):
        """Process response and create audit logs"""
        try:
            self._create_audit_log(request, response)
        except Exception as e:
            # Don't let audit logging break the application
            logger.error(f"Audit middleware error: {e}")
        
        return response
    
    def _should_log_request(self, request):
        """Determine if this request should be audit logged"""
        path = request.path
        
        # Skip certain paths
        for skip_path in self.SKIP_PATHS:
            if path.startswith(skip_path):
                return False
        
        # Always log sensitive paths
        for sensitive_path in self.SENSITIVE_PATHS:
            if path.startswith(sensitive_path):
                return True
        
        # Log all modification requests
        if request.method in self.MODIFICATION_METHODS:
            return True
        
        # Log authenticated user requests to important areas
        if request.user.is_authenticated:
            # Log project access
            if '/p/' in path:  # Project URLs
                return True
            
            # Log admin area access
            if '/admin' in path or 'console' in path:
                return True
        
        return False
    
    def _get_request_details(self, request):
        """Extract detailed request information"""
        details = {
            'path': request.path,
            'method': request.method,
            'query_params': dict(request.GET) if request.GET else {},
        }
        
        # Add resolved URL info
        try:
            resolver_match = resolve(request.path)
            details.update({
                'view_name': resolver_match.view_name,
                'url_name': resolver_match.url_name,
                'namespace': resolver_match.namespace,
                'app_name': resolver_match.app_name,
            })
        except Exception:
            pass
        
        # Add POST data for sensitive operations (but sanitize passwords)
        if request.method == 'POST' and hasattr(request, 'POST'):
            post_data = dict(request.POST)
            # Sanitize sensitive fields
            for sensitive_field in ['password', 'password1', 'password2', 'token', 'secret']:
                if sensitive_field in post_data:
                    post_data[sensitive_field] = '[REDACTED]'
            details['post_data'] = post_data
        
        return details
    
    def _determine_severity(self, request, response):
        """Determine the severity level of the request"""
        path = request.path
        method = request.method
        status_code = response.status_code
        
        # Critical severity
        if status_code >= 500:
            return 'critical'
        
        if '/admin/' in path and method in self.MODIFICATION_METHODS:
            return 'critical'
        
        # High severity
        if status_code == 403 or status_code == 401:
            return 'high'
        
        if any(sensitive in path for sensitive in ['/api/', '/control-plane/', '/owner-console/']):
            if method in self.MODIFICATION_METHODS:
                return 'high'
        
        # Medium severity
        if method in self.MODIFICATION_METHODS:
            return 'medium'
        
        if '/p/' in path:  # Project access
            return 'medium'
        
        # Low severity
        return 'low'
    
    def _get_project_from_request(self, request):
        """Extract project context from request if available"""
        try:
            # Check for project in URL path (e.g., /p/project-slug/)
            path_parts = request.path.split('/')
            if 'p' in path_parts:
                project_index = path_parts.index('p')
                if len(path_parts) > project_index + 1:
                    project_slug = path_parts[project_index + 1]
                    from .models import Project
                    return Project.objects.get(slug=project_slug)
            
            # Check for project in session
            if hasattr(request, 'session') and 'current_project_slug' in request.session:
                from .models import Project
                return Project.objects.get(slug=request.session['current_project_slug'])
                
        except Exception:
            pass
        
        return None
    
    def _create_audit_log(self, request, response):
        """Create audit log entry for the request"""
        if not self._should_log_request(request):
            return
        
        # Calculate request duration
        duration = None
        if hasattr(request, '_audit_start_time'):
            duration = time.time() - request._audit_start_time
        
        # Determine action type based on request
        action = self._get_action_from_request(request, response)
        
        # Get request details
        details = self._get_request_details(request)
        details['response_status'] = response.status_code
        details['response_size'] = len(response.content) if hasattr(response, 'content') else 0
        
        if duration:
            details['duration_ms'] = round(duration * 1000, 2)
        
        # Determine success
        success = 200 <= response.status_code < 400
        error_message = ''
        if not success:
            if response.status_code == 403:
                error_message = 'Access forbidden'
            elif response.status_code == 401:
                error_message = 'Authentication required'
            elif response.status_code == 404:
                error_message = 'Resource not found'
            elif response.status_code >= 500:
                error_message = 'Server error'
            else:
                error_message = f'HTTP {response.status_code}'
        
        # Get project context
        project = self._get_project_from_request(request)
        
        # Determine severity
        severity = self._determine_severity(request, response)
        
        # Create audit log
        AuditService.log_action(
            action=action,
            user=request.user if request.user.is_authenticated else None,
            project=project,
            details=details,
            request=request,
            severity=severity,
            success=success,
            error_message=error_message,
        )
    
    def _get_action_from_request(self, request, response):
        """Determine the action type from the request"""
        path = request.path
        method = request.method
        
        # Admin actions
        if '/admin/' in path:
            return 'admin_login' if 'login' in path else 'system_config_change'
        
        # API actions
        if '/api/' in path:
            return 'api_access'
        
        # Project access
        if '/p/' in path:
            if method in self.MODIFICATION_METHODS:
                if method == 'POST':
                    return 'create_record'
                elif method in ['PUT', 'PATCH']:
                    return 'update_record'
                elif method == 'DELETE':
                    return 'delete_record'
            return 'project_access'
        
        # Authentication
        if 'login' in path:
            if response.status_code == 200:
                return 'user_login'
            else:
                return 'login_failed'
        
        if 'logout' in path:
            return 'user_logout'
        
        # Default based on method
        if method == 'POST':
            return 'create_record'
        elif method in ['PUT', 'PATCH']:
            return 'update_record'
        elif method == 'DELETE':
            return 'delete_record'
        else:
            return 'view_record'


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    Additional middleware focused on security events
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_response(self, request, response):
        """Check for security-relevant events"""
        try:
            # Log unauthorized access attempts
            if response.status_code == 403:
                AuditService.log_unauthorized_access(
                    user=request.user if request.user.is_authenticated else None,
                    attempted_resource=request.path,
                    request=request,
                )
            
            # Log suspicious activity patterns
            self._check_suspicious_activity(request, response)
            
        except Exception as e:
            logger.error(f"Security audit middleware error: {e}")
        
        return response
    
    def _check_suspicious_activity(self, request, response):
        """Check for patterns that might indicate malicious activity"""
        path = request.path
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        suspicious_patterns = [
            # Common attack patterns in URLs
            '../', '..\\', '/etc/passwd', '/proc/', '\\x',
            'union select', 'drop table', '<script', 'javascript:',
            # Common bot user agents
            'bot', 'crawler', 'spider',
        ]
        
        is_suspicious = any(pattern in path.lower() or pattern in user_agent.lower() 
                           for pattern in suspicious_patterns)
        
        if is_suspicious:
            AuditService.log_action(
                action='unauthorized_access_attempt',
                user=request.user if request.user.is_authenticated else None,
                details={
                    'suspicious_pattern': True,
                    'path': path,
                    'user_agent': user_agent[:500],  # Limit length
                },
                request=request,
                severity='high',
                success=False,
            )