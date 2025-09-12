# control_plane/utils.py
"""
Utilities for multi-tenant database management and monitoring.
"""

import logging
import time
from django.conf import settings
from django.db import connections
from django.core.cache import cache
from .router import DatabaseManager

logger = logging.getLogger(__name__)


class TenantDatabaseUtils:
    """Utilities for managing tenant databases efficiently."""
    
    @staticmethod
    def ensure_project_database_exists(project_slug):
        """
        Ensure a project database exists and is configured.
        Returns the database alias.
        """
        db_alias = f"project_{project_slug}"
        
        # Check if already in settings
        if db_alias not in settings.DATABASES:
            logger.info(f"Adding database for project: {project_slug}")
            DatabaseManager.add_project_database(project_slug)
        
        return db_alias
    
    @staticmethod
    def get_database_status(db_alias):
        """
        Check the status and performance of a database connection.
        Returns dict with connection info.
        """
        try:
            connection = connections[db_alias]
            
            # Test connection
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            connection_time = time.time() - start_time
            
            # Get connection info
            status = {
                'alias': db_alias,
                'database': connection.settings_dict.get('NAME'),
                'host': connection.settings_dict.get('HOST'),
                'connection_time_ms': round(connection_time * 1000, 2),
                'is_connected': True,
                'queries_count': len(connection.queries),
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Database {db_alias} connection failed: {e}")
            return {
                'alias': db_alias,
                'is_connected': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_all_tenant_databases():
        """Get list of all configured tenant database aliases."""
        return [
            alias for alias in settings.DATABASES.keys() 
            if alias.startswith('project_')
        ]
    
    @staticmethod
    def clear_database_connections():
        """Close all database connections (useful for cleanup)."""
        connections.close_all()
        logger.info("Closed all database connections")


class PerformanceMonitor:
    """Monitor database performance and log slow queries."""
    
    SLOW_QUERY_THRESHOLD = 1.0  # seconds
    
    @staticmethod
    def log_slow_queries(db_alias):
        """Log slow queries for a specific database."""
        try:
            connection = connections[db_alias]
            
            for query in connection.queries:
                query_time = float(query['time'])
                if query_time > PerformanceMonitor.SLOW_QUERY_THRESHOLD:
                    logger.warning(
                        f"SLOW QUERY [{db_alias}] {query_time:.2f}s: {query['sql'][:200]}..."
                    )
        except Exception as e:
            logger.error(f"Error monitoring queries for {db_alias}: {e}")
    
    @staticmethod
    def get_database_metrics():
        """Get performance metrics for all databases."""
        metrics = {}
        
        for db_alias in settings.DATABASES.keys():
            try:
                connection = connections[db_alias]
                
                metrics[db_alias] = {
                    'queries_count': len(connection.queries),
                    'total_time': sum(float(q['time']) for q in connection.queries),
                    'avg_time': sum(float(q['time']) for q in connection.queries) / max(len(connection.queries), 1),
                    'slow_queries': len([
                        q for q in connection.queries 
                        if float(q['time']) > PerformanceMonitor.SLOW_QUERY_THRESHOLD
                    ])
                }
            except Exception as e:
                metrics[db_alias] = {'error': str(e)}
        
        return metrics


# Cache tenant database lookups
def get_cached_tenant_database(project_slug):
    """Get tenant database with caching to reduce lookup overhead."""
    cache_key = f"tenant_db:{project_slug}"
    db_alias = cache.get(cache_key)
    
    if not db_alias:
        db_alias = TenantDatabaseUtils.ensure_project_database_exists(project_slug)
        # Cache for 1 hour
        cache.set(cache_key, db_alias, 3600)
    
    return db_alias