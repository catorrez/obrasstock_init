"""
Optimized middleware combining tenant context, user type detection, and access control.
This replaces multiple middleware classes to eliminate duplicate database queries.
"""
from django.http import HttpResponseRedirect
from django.conf import settings
from .services import UserTypeService, TenantContextService
import logging

logger = logging.getLogger(__name__)


class OptimizedTenantMiddleware:
    """
    Single middleware handling:
    1. Tenant context extraction and database routing
    2. User type detection with caching
    3. Subdomain-based access control
    4. URL routing based on subdomain
    
    This replaces:
    - TenantContextMiddleware
    - SubdomainBasedAccessMiddleware  
    - SubdomainRoutingMiddleware
    - UserTypeAccessControlMiddleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Pre-compile patterns for efficiency
        import re
        self.project_url_pattern = re.compile(r'/p/([a-z][a-z0-9_-]+)/')
    
    def __call__(self, request):
        # 1. Extract tenant context from URL
        self._set_tenant_context(request)
        
        # 2. Extract subdomain context
        self._set_subdomain_context(request)
        
        # 3. Process request through Django
        response = self.get_response(request)
        
        # 4. Apply access control after authentication is available
        return self.process_response(request, response)
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Called after Django's authentication middleware has run.
        This is where we can safely access request.user and apply access control.
        """
        # Skip processing for static files and admin media
        if request.path.startswith(('/static/', '/media/')):
            return None
        
        # Get user type with caching (single DB query max per request)
        user = getattr(request, 'user', None)
        request.user_type = UserTypeService.get_user_type(user)
        
        # Apply subdomain-based access control
        redirect_response = self._check_subdomain_access(request)
        if redirect_response:
            return redirect_response
        
        # Apply path-based access control
        redirect_response = self._check_path_access(request)
        if redirect_response:
            return redirect_response
        
        return None
    
    def process_response(self, request, response):
        """
        Clean up any request-specific context.
        """
        # Clean up tenant context (no thread-local cleanup needed)
        return response
    
    def _set_tenant_context(self, request):
        """
        Extract and set tenant context in request object (not thread-local).
        """
        tenant_context = TenantContextService.extract_project_context(request)
        request.tenant_context = tenant_context
        
        # Set database routing context for compatibility with existing router
        if tenant_context['has_project_context']:
            # Store in request instead of thread-local for better memory management
            request._tenant_db = tenant_context['project_db']
            request._tenant_slug = tenant_context['project_slug']
            logger.debug(f"Set tenant context: {tenant_context['project_slug']} -> {tenant_context['project_db']}")
    
    def _set_subdomain_context(self, request):
        """
        Set subdomain context for template and view usage.
        """
        request.subdomain = TenantContextService.get_subdomain_context(request)
    
    def _check_subdomain_access(self, request):
        """
        Check subdomain-based access control with strict user separation.
        """
        host = request.get_host().split(":")[0]
        path = request.path
        user_type = getattr(request, 'user_type', None)
        
        # For localhost/testing, allow all access
        if host in ("localhost", "127.0.0.1"):
            return None
        
        # ONLY allow access to the three designated login pages
        allowed_login_paths = ['/login/']  # All subdomains use /login/
        if path in allowed_login_paths:
            return None
        
        # Block all other paths - redirect to appropriate login page based on subdomain
        if not user_type:  # Unauthenticated users
            if host == "obrasstock.etvholding.com":
                return HttpResponseRedirect("https://obrasstock.etvholding.com/login/")
            elif host == "adminos.etvholding.com":
                return HttpResponseRedirect("https://adminos.etvholding.com/login/")
            elif host == "appos.etvholding.com":
                return HttpResponseRedirect("https://appos.etvholding.com/login/")
            else:
                # Unknown subdomain - redirect to owner login
                return HttpResponseRedirect("https://obrasstock.etvholding.com/login/")
        
        # For authenticated users, redirect them to their appropriate login page
        # This ensures only login pages are accessible - no admin/app interfaces
        if user_type == 'owner':
            return HttpResponseRedirect("https://obrasstock.etvholding.com/login/")
        elif user_type == 'admin':
            return HttpResponseRedirect("https://adminos.etvholding.com/login/")
        else:  # project users (when they exist)
            return HttpResponseRedirect("https://appos.etvholding.com/login/")
        
        # This code should never be reached but keep for safety
        if host == "obrasstock.etvholding.com":
            # OWNER subdomain - only superusers allowed
            if user_type != 'owner':
                if user_type == 'admin':
                    # Redirect admin to their admin interface
                    redirect_path = '/admin/' if path.startswith(('/owner/', '/app/')) else path
                    return HttpResponseRedirect(f"https://adminos.etvholding.com{redirect_path}")
                else:  # project user
                    # Redirect project user to their app interface
                    redirect_path = '/app/' if path.startswith(('/owner/', '/admin/')) else path
                    return HttpResponseRedirect(f"https://appos.etvholding.com{redirect_path}")
                    
        elif host == "adminos.etvholding.com":
            # ADMIN subdomain - only AdminSystem group members allowed
            if user_type != 'admin':
                if user_type == 'owner':
                    # Redirect owner to their owner interface
                    redirect_path = '/owner/' if path.startswith(('/admin/', '/app/')) else path
                    return HttpResponseRedirect(f"https://obrasstock.etvholding.com{redirect_path}")
                else:  # project user
                    # Redirect project user to their app interface
                    redirect_path = '/app/' if path.startswith(('/owner/', '/admin/')) else path
                    return HttpResponseRedirect(f"https://appos.etvholding.com{redirect_path}")
                    
        elif host == "appos.etvholding.com":
            # PROJECT subdomain - only project users allowed
            if user_type != 'project':
                if user_type == 'owner':
                    # Redirect owner to their owner interface
                    redirect_path = '/owner/' if path.startswith(('/admin/', '/app/')) else path
                    return HttpResponseRedirect(f"https://obrasstock.etvholding.com{redirect_path}")
                else:  # admin user
                    # Redirect admin to their admin interface
                    redirect_path = '/admin/' if path.startswith(('/owner/', '/app/')) else path
                    return HttpResponseRedirect(f"https://adminos.etvholding.com{redirect_path}")
        
        return None
    
    def _check_path_access(self, request):
        """
        Check path-based access control for user type restrictions.
        """
        host = request.get_host().split(":")[0]
        path = request.path
        user_type = getattr(request, 'user_type', None)
        
        # For localhost/testing, allow all access
        if host in ("localhost", "127.0.0.1"):
            return None
        
        # Allow access to login pages
        if path in ['/login/', '/admin/login/', '/app/login/']:
            return None
        
        # Skip access control for unauthenticated users
        if not user_type:
            return None
        
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
                
        elif path.startswith("/app/"):
            if user_type == 'owner':
                # Redirect owners to /owner/
                return HttpResponseRedirect("https://obrasstock.etvholding.com/owner/")
            elif user_type == 'admin':
                # Redirect admins to /admin/
                return HttpResponseRedirect("https://adminos.etvholding.com/admin/")
        
        return None


class RequestTenantContextMiddleware:
    """
    Lightweight middleware to provide tenant context compatibility 
    for the existing database router without thread-local storage.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set up request-based tenant context for database router
        if hasattr(request, '_tenant_db') and hasattr(request, '_tenant_slug'):
            # Store in a way the router can access
            self._set_router_context(request._tenant_db, request._tenant_slug)
        
        response = self.get_response(request)
        
        # Clean up router context
        self._clear_router_context()
        
        return response
    
    def _set_router_context(self, db_alias, project_slug):
        """
        Set context for the database router.
        This maintains compatibility with the existing MultiTenantRouter.
        """
        # We'll still use thread-local for now for router compatibility
        # but only set it when actually needed and clean it up properly
        if not hasattr(settings, '_THREAD_LOCAL'):
            import threading
            settings._THREAD_LOCAL = threading.local()
        
        settings._THREAD_LOCAL.current_project_db = db_alias
        settings._THREAD_LOCAL.current_project_slug = project_slug
    
    def _clear_router_context(self):
        """
        Clean up router context after request.
        """
        if hasattr(settings, '_THREAD_LOCAL'):
            if hasattr(settings._THREAD_LOCAL, 'current_project_db'):
                delattr(settings._THREAD_LOCAL, 'current_project_db')
            if hasattr(settings._THREAD_LOCAL, 'current_project_slug'):
                delattr(settings._THREAD_LOCAL, 'current_project_slug')