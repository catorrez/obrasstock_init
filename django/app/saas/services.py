"""
User management services for SAAS application
"""
from django.core.cache import cache
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class UserTypeService:
    """
    Optimized user type detection with caching to eliminate redundant database queries.
    
    User Types:
    - 'owner': Superusers (is_superuser=True)
    - 'admin': Users in AdminSystem group
    - 'project': All other authenticated users
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    CACHE_PREFIX = "user_type"
    
    @classmethod
    def get_user_type(cls, user):
        """
        Get user type with caching to avoid repeated database queries.
        
        Args:
            user: Django User instance or None
            
        Returns:
            str: 'owner', 'admin', 'project', or None if unauthenticated
        """
        if not user or not user.is_authenticated:
            return None
        
        # Try cache first
        cache_key = f"{cls.CACHE_PREFIX}_{user.id}"
        user_type = cache.get(cache_key)
        
        if user_type is not None:
            logger.debug(f"User type cache hit for user {user.id}: {user_type}")
            return user_type
        
        # Cache miss - determine user type with single query
        user_type = cls._determine_user_type(user)
        
        # Cache the result
        cache.set(cache_key, user_type, cls.CACHE_TIMEOUT)
        logger.debug(f"User type cached for user {user.id}: {user_type}")
        
        return user_type
    
    @classmethod
    def _determine_user_type(cls, user):
        """
        Determine user type from database (called only on cache miss).
        """
        # OWNER SYSTEM: superusers
        if user.is_superuser:
            return 'owner'
        
        # ADMIN SYSTEM: users in AdminSystem group
        # Use exists() for efficiency - we only need to know if membership exists
        if user.groups.filter(name='AdminSystem').exists():
            return 'admin'
        
        # PROJECT users: everyone else
        return 'project'
    
    @classmethod
    def invalidate_user_type_cache(cls, user):
        """
        Invalidate user type cache when user permissions change.
        Call this when user groups are modified or superuser status changes.
        """
        cache_key = f"{cls.CACHE_PREFIX}_{user.id}"
        cache.delete(cache_key)
        logger.info(f"User type cache invalidated for user {user.id}")
    
    @classmethod
    def warm_cache_for_users(cls, user_ids):
        """
        Pre-warm cache for a list of users to optimize bulk operations.
        """
        users = User.objects.select_related().prefetch_related('groups').filter(id__in=user_ids)
        
        for user in users:
            user_type = cls._determine_user_type(user)
            cache_key = f"{cls.CACHE_PREFIX}_{user.id}"
            cache.set(cache_key, user_type, cls.CACHE_TIMEOUT)
        
        logger.info(f"User type cache warmed for {len(user_ids)} users")


class TenantContextService:
    """
    Service for managing tenant context without thread-local storage.
    """
    
    @staticmethod
    def extract_project_context(request):
        """
        Extract project context from request path and store in request object.
        
        Returns:
            dict: Project context with slug and database alias
        """
        import re
        
        # Match project URLs like /p/project-slug/
        project_pattern = re.compile(r'/p/([a-z][a-z0-9_-]+)/')
        match = project_pattern.search(request.path)
        
        if match:
            project_slug = match.group(1)
            db_alias = f"project_{project_slug}"
            
            # Verify database exists in settings
            from django.conf import settings
            if db_alias in settings.DATABASES:
                return {
                    'project_slug': project_slug,
                    'project_db': db_alias,
                    'has_project_context': True
                }
            else:
                logger.warning(f"Project database {db_alias} not found in DATABASES")
        
        return {
            'project_slug': None,
            'project_db': 'default',
            'has_project_context': False
        }
    
    @staticmethod
    def get_subdomain_context(request):
        """
        Extract subdomain context from request.
        
        Returns:
            str: 'owner', 'admin', 'project', or 'unknown'
        """
        host = request.get_host().split(":")[0]
        
        if host == "obrasstock.etvholding.com":
            return 'owner'
        elif host == "adminos.etvholding.com":
            return 'admin'
        elif host == "appos.etvholding.com":
            return 'project'
        else:
            return 'unknown'