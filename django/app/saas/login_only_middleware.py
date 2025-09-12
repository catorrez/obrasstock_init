"""
Login-only middleware that blocks ALL access except designated login pages.
Only these URLs are allowed:
- https://obrasstock.etvholding.com/login/
- https://adminos.etvholding.com/login/
- https://appos.etvholding.com/login/
"""
from django.http import HttpResponseRedirect
from django.conf import settings
from .services import TenantContextService
import logging

logger = logging.getLogger(__name__)


class LoginOnlyMiddleware:
    """
    Middleware that blocks ALL access except the three designated login pages.
    All other requests are redirected to the appropriate login page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set tenant context for compatibility
        self._set_tenant_context(request)
        self._set_subdomain_context(request)
        
        # Process request through Django
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Process view to enforce login-only access.
        """
        host = request.get_host().split(":")[0]
        path = request.path
        
        # Allow localhost for development
        if host in ("localhost", "127.0.0.1"):
            return None
        
        # Allow static files and media
        if path.startswith(('/static/', '/media/')):
            return None
        
        # Allow login and logout pages
        if path in ['/login/', '/logout/'] and host in [
            'obrasstock.etvholding.com',
            'adminos.etvholding.com', 
            'appos.etvholding.com'
        ]:
            logger.debug(f"Allowing access to auth page: {host}{path}")
            return None
        
        # Allow authenticated users to access their designated portals
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            from .services import UserTypeService
            user_type = UserTypeService.get_user_type(user)
            
            # OWNER users can access /owner/ on obrasstock subdomain
            if (host == "obrasstock.etvholding.com" and 
                path.startswith('/owner/') and 
                user_type == 'owner'):
                logger.debug(f"Allowing OWNER access: {user.username} -> {host}{path}")
                return None
                
            # ADMIN users can access /admin/ on adminos subdomain  
            elif (host == "adminos.etvholding.com" and 
                  path.startswith('/admin/') and 
                  user_type == 'admin'):
                logger.debug(f"Allowing ADMIN access: {user.username} -> {host}{path}")
                return None
                
            # PROJECT users can access /app/ on appos subdomain
            elif (host == "appos.etvholding.com" and 
                  path.startswith('/app/') and 
                  user_type == 'project'):
                logger.debug(f"Allowing PROJECT access: {user.username} -> {host}{path}")
                return None
        
        # Block everything else - redirect to appropriate login page
        if host == "obrasstock.etvholding.com":
            redirect_url = "https://obrasstock.etvholding.com/login/"
        elif host == "adminos.etvholding.com":
            redirect_url = "https://adminos.etvholding.com/login/"
        elif host == "appos.etvholding.com":
            redirect_url = "https://appos.etvholding.com/login/"
        else:
            # Unknown subdomain - redirect to owner login
            redirect_url = "https://obrasstock.etvholding.com/login/"
        
        # Avoid redirect loops
        if request.build_absolute_uri() == redirect_url:
            logger.warning(f"Avoiding redirect loop for {request.build_absolute_uri()}")
            return None
        
        logger.info(f"Blocking access to {host}{path}, redirecting to {redirect_url}")
        return HttpResponseRedirect(redirect_url)
    
    def _set_tenant_context(self, request):
        """
        Set tenant context for database routing compatibility.
        """
        tenant_context = TenantContextService.extract_project_context(request)
        request.tenant_context = tenant_context
        
        if tenant_context['has_project_context']:
            request._tenant_db = tenant_context['project_db']
            request._tenant_slug = tenant_context['project_slug']
    
    def _set_subdomain_context(self, request):
        """
        Set subdomain context for template compatibility.
        """
        request.subdomain = TenantContextService.get_subdomain_context(request)


class RequestTenantContextMiddleware:
    """
    Lightweight middleware to provide tenant context compatibility 
    for the existing database router.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set up request-based tenant context for database router
        if hasattr(request, '_tenant_db') and hasattr(request, '_tenant_slug'):
            self._set_router_context(request._tenant_db, request._tenant_slug)
        
        response = self.get_response(request)
        
        # Clean up router context
        self._clear_router_context()
        
        return response
    
    def _set_router_context(self, db_alias, project_slug):
        """
        Set context for the database router.
        """
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