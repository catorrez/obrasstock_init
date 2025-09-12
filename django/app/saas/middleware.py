from django.http import HttpResponseRedirect
from django.conf import settings
import logging
import re

logger = logging.getLogger(__name__)

class TenantContextMiddleware:
    """
    Middleware to set tenant context for multi-tenant database routing.
    Extracts project slug from URL and sets it in thread-local storage.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Regex to match project URLs like /p/project-slug/ or /p/project-slug/module/
        self.project_url_pattern = re.compile(r'/p/([a-z][a-z0-9_-]+)/')
        
    def __call__(self, request):
        # Initialize thread-local storage if not exists
        if not hasattr(settings, '_THREAD_LOCAL'):
            import threading
            settings._THREAD_LOCAL = threading.local()
        
        # Extract project slug from URL
        project_slug = None
        match = self.project_url_pattern.search(request.path)
        if match:
            project_slug = match.group(1)
            db_alias = f"project_{project_slug}"
            
            # Verify project database exists in settings
            if db_alias in settings.DATABASES:
                settings._THREAD_LOCAL.current_project_db = db_alias
                settings._THREAD_LOCAL.current_project_slug = project_slug
                logger.debug(f"Set tenant context: {db_alias}")
            else:
                logger.warning(f"Project database {db_alias} not found in DATABASES")
                settings._THREAD_LOCAL.current_project_db = 'default'
                settings._THREAD_LOCAL.current_project_slug = None
        else:
            # No project context - use default database
            settings._THREAD_LOCAL.current_project_db = 'default'
            settings._THREAD_LOCAL.current_project_slug = None
        
        response = self.get_response(request)
        
        # Clean up thread-local storage after request
        if hasattr(settings._THREAD_LOCAL, 'current_project_db'):
            delattr(settings._THREAD_LOCAL, 'current_project_db')
        if hasattr(settings._THREAD_LOCAL, 'current_project_slug'):
            delattr(settings._THREAD_LOCAL, 'current_project_slug')
            
        return response


class SubdomainBasedAccessMiddleware:
    """
    Subdomain-based access control:
    - obrasstock.etvholding.com → OWNER SYSTEM
    - adminos.etvholding.com → ADMIN SYSTEM  
    - appos.etvholding.com → PROJECT USERS
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def _get_user_type(self, user):
        """Determine user type based on permissions."""
        if not user or not user.is_authenticated:
            return None
            
        # OWNER SYSTEM: superusers
        if user.is_superuser:
            return 'owner'
            
        # ADMIN SYSTEM: users in AdminSystem group
        if user.groups.filter(name='AdminSystem').exists():
            return 'admin'
            
        # PROJECT users: everyone else
        return 'project'

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        path = request.path
        
        # For localhost/testing, allow all access
        if host in ("localhost", "127.0.0.1"):
            return self.get_response(request)
        
        # Allow access to login pages for unauthenticated users
        if path in ['/login/', '/admin/login/', '/app/login/']:
            return self.get_response(request)
            
        # Get user type if authenticated
        user = getattr(request, "user", None)
        user_type = self._get_user_type(user)
        
        # If user is not authenticated, allow them to proceed (they'll need to login)
        if not user_type:
            return self.get_response(request)
        
        # Strict subdomain separation - redirect users to their designated subdomain
        if host == "obrasstock.etvholding.com":
            # OWNER subdomain - only superusers allowed
            if user_type != 'owner':
                if user_type == 'admin':
                    return HttpResponseRedirect(f"https://adminos.etvholding.com{path}")
                else:  # project user
                    return HttpResponseRedirect(f"https://appos.etvholding.com{path}")
                    
        elif host == "adminos.etvholding.com":
            # ADMIN subdomain - only AdminSystem group members allowed
            if user_type != 'admin':
                if user_type == 'owner':
                    return HttpResponseRedirect(f"https://obrasstock.etvholding.com{path}")
                else:  # project user
                    return HttpResponseRedirect(f"https://appos.etvholding.com{path}")
                    
        elif host == "appos.etvholding.com":
            # PROJECT subdomain - only project users allowed
            if user_type != 'project':
                if user_type == 'owner':
                    return HttpResponseRedirect(f"https://obrasstock.etvholding.com{path}")
                else:  # admin user
                    return HttpResponseRedirect(f"https://adminos.etvholding.com{path}")

        return self.get_response(request)


class SubdomainRoutingMiddleware:
    """
    Routes URLs based on subdomain to provide different interfaces:
    - obrasstock.etvholding.com → OWNER SYSTEM interface
    - adminos.etvholding.com → ADMIN SYSTEM interface
    - appos.etvholding.com → PROJECT USERS interface
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        
        # For localhost/testing, use default routing
        if host in ("localhost", "127.0.0.1"):
            return self.get_response(request)
            
        # Set subdomain context for templates and views
        if host == "obrasstock.etvholding.com":
            request.subdomain = 'owner'
        elif host == "adminos.etvholding.com":
            request.subdomain = 'admin'
        elif host == "appos.etvholding.com":
            request.subdomain = 'project'
        else:
            request.subdomain = 'unknown'

        return self.get_response(request)


class UserTypeAccessControlMiddleware:
    """
    Controls access based on user types:
    - OWNER SYSTEM (superuser): /owner/ only
    - ADMIN SYSTEM (AdminSystem group): /admin/ only  
    - PROJECT users (everyone else): /app/ only
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def _get_user_type(self, user):
        """Determine user type based on permissions."""
        if not user or not user.is_authenticated:
            return None
            
        # OWNER SYSTEM: superusers
        if user.is_superuser:
            return 'owner'
            
        # ADMIN SYSTEM: users in AdminSystem group
        if user.groups.filter(name='AdminSystem').exists():
            return 'admin'
            
        # PROJECT users: everyone else (including regular staff)
        return 'project'

    def __call__(self, request):
        user = getattr(request, "user", None)
        user_type = self._get_user_type(user)
        
        host = request.get_host().split(":")[0]
        path = request.path
        
        # For localhost/testing, allow all access
        if host in ("localhost", "127.0.0.1"):
            return self.get_response(request)
        
        # Allow access to login pages for unauthenticated users
        if path in ['/login/', '/admin/login/', '/app/login/']:
            return self.get_response(request)
        
        # Skip access control for unauthenticated users
        if not user_type:
            return self.get_response(request)
        
        # Access control based on user type and path
        if path.startswith("/owner/"):
            if user_type != 'owner':
                # Redirect non-owners away from /owner/
                if user_type == 'admin':
                    return HttpResponseRedirect("https://adminos.etvholding.com/admin/")
                else:  # project user
                    return HttpResponseRedirect("https://appos.etvholding.com/app/")
                    
        elif path.startswith("/admin/"):
            if user_type == 'owner':
                # Redirect owners to /owner/
                return HttpResponseRedirect("https://obrasstock.etvholding.com/owner/")
            elif user_type == 'project':
                # Redirect project users to /app/
                return HttpResponseRedirect("https://appos.etvholding.com/app/")
            # Admin users are allowed to stay in /admin/ - no redirect needed
                
        elif path.startswith("/app/"):
            if user_type == 'owner':
                # Redirect owners to /owner/
                return HttpResponseRedirect("https://obrasstock.etvholding.com/owner/")
            elif user_type == 'admin':
                # Redirect admins to /admin/
                return HttpResponseRedirect("https://adminos.etvholding.com/admin/")
            # Project users are allowed to stay in /app/ - no redirect needed
        
        return self.get_response(request)
