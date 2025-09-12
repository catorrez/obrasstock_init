"""
Minimal services for SAAS middleware functionality
"""
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class TenantContextService:
    """Service for extracting tenant context from requests"""
    
    @staticmethod
    def extract_project_context(request):
        """Extract project context from URL path"""
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'p':
            return {
                'project_slug': path_parts[1],
                'has_project_context': True
            }
        return {
            'project_slug': None,
            'has_project_context': False
        }
    
    @staticmethod
    def get_subdomain_context(request):
        """Extract subdomain from request"""
        host = request.get_host().split(':')[0]  # Remove port if present
        if '.' in host:
            subdomain = host.split('.')[0]
        else:
            subdomain = host
        return {
            'subdomain': subdomain,
            'is_subdomain': '.' in host
        }


class UserTypeService:
    """Service for determining user types and permissions"""
    
    @staticmethod
    def get_user_type(user):
        """Determine user type based on user properties"""
        if not user or not user.is_authenticated:
            return 'anonymous'
        
        if user.is_superuser:
            return 'owner'
        
        # Check if user is in system_admin group
        if user.groups.filter(name='system_admin').exists():
            return 'system_admin'
        
        return 'project_user'
    
    @staticmethod
    def can_access_control_plane(user):
        """Check if user can access control plane"""
        user_type = UserTypeService.get_user_type(user)
        return user_type in ['owner', 'system_admin']