from django.conf import settings
from django.db import connection
from .models import Project


class MultiTenantRouter:
    """
    Database router for multi-tenant architecture.
    Routes project-specific apps to their respective databases.
    """
    
    # Apps that are project-specific and should use project databases
    PROJECT_APPS = [
        'inventario',
        'project_reports', 
        'project_accounting',
        # Add more project-specific apps here as needed
    ]
    
    # Apps that should always use the control plane database
    CONTROL_PLANE_APPS = [
        'auth',
        'contenttypes',
        'sessions',
        'admin',
        'control_plane',
        'saas',  # Keep existing SAAS for backwards compatibility
    ]
    
    def db_for_read(self, model, **hints):
        """Determine which database to read from."""
        app_label = model._meta.app_label
        
        # Control plane apps always use default database
        if app_label in self.CONTROL_PLANE_APPS:
            return 'default'
        
        # Project-specific apps use project database
        if app_label in self.PROJECT_APPS:
            return self._get_project_database()
        
        # Default to control plane for unknown apps
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Determine which database to write to."""
        app_label = model._meta.app_label
        
        # Control plane apps always use default database
        if app_label in self.CONTROL_PLANE_APPS:
            return 'default'
        
        # Project-specific apps use project database
        if app_label in self.PROJECT_APPS:
            return self._get_project_database()
        
        # Default to control plane for unknown apps
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same database."""
        db_set = {'default'}
        
        # Add project database if available
        project_db = self._get_project_database()
        if project_db:
            db_set.add(project_db)
        
        # Allow relations within the same database
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Determine if migration should run on this database."""
        
        # Control plane apps only migrate on default database
        if app_label in self.CONTROL_PLANE_APPS:
            return db == 'default'
        
        # Project-specific apps only migrate on project databases
        if app_label in self.PROJECT_APPS:
            return db != 'default' and db.startswith('project_')
        
        # Default behavior for other apps
        return db == 'default'
    
    def _get_project_database(self):
        """Get the current project database from thread-local storage."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get thread-local storage from settings
        thread_local = getattr(settings, '_THREAD_LOCAL', None)
        
        if thread_local and hasattr(thread_local, 'current_project_db'):
            db_alias = thread_local.current_project_db
            
            # Verify database exists in settings
            if db_alias in settings.DATABASES:
                logger.debug(f"Router using database: {db_alias}")
                return db_alias
            else:
                logger.error(f"Database {db_alias} not found in DATABASES settings")
                return 'default'
        
        # Log when falling back to default (helps debugging)
        logger.debug("No tenant context found, using default database")
        return 'default'


class DatabaseManager:
    """
    Utility class for managing project databases.
    """
    
    @staticmethod
    def get_project_database_config(project_slug):
        """Get database configuration for a project."""
        database_name = f"obras_proj_{project_slug}"
        
        # Get default database settings
        default_db = settings.DATABASES['default'].copy()
        
        # Update with project-specific database name
        default_db['NAME'] = database_name
        
        return default_db
    
    @staticmethod
    def add_project_database(project_slug):
        """Dynamically add a project database to Django settings."""
        db_alias = f"project_{project_slug}"
        db_config = DatabaseManager.get_project_database_config(project_slug)
        
        # Apply performance configuration
        if hasattr(settings, 'DATABASE_POOL_CONFIG'):
            db_config.update(settings.DATABASE_POOL_CONFIG)
        
        # Add to DATABASES if not already present
        if db_alias not in settings.DATABASES:
            settings.DATABASES[db_alias] = db_config
            
            # Log database addition for monitoring
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Added project database: {db_alias} -> {db_config['NAME']}")
        
        return db_alias
    
    @staticmethod
    def create_project_database(project_slug):
        """Create the physical database for a project."""
        from django.db import connections
        from django.core.management import call_command
        from django.db import connection
        
        # Get database configuration
        db_config = DatabaseManager.get_project_database_config(project_slug)
        database_name = db_config['NAME']
        
        try:
            # Use Django's database connection to create the database
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            # Add database to Django settings
            db_alias = DatabaseManager.add_project_database(project_slug)
            
            # Run migrations on the new database
            call_command('migrate', database=db_alias, verbosity=0)
            
            return True
            
        except Exception as e:
            print(f"Error creating database {database_name}: {e}")
            return False
    
    @staticmethod
    def delete_project_database(project_slug):
        """Delete the physical database for a project."""
        from django.db import connection
        
        # Get database configuration
        db_config = DatabaseManager.get_project_database_config(project_slug)
        database_name = db_config['NAME']
        
        try:
            # Use Django's database connection to drop the database
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{database_name}`")
            
            # Remove from Django settings
            db_alias = f"project_{project_slug}"
            if db_alias in settings.DATABASES:
                del settings.DATABASES[db_alias]
            
            return True
            
        except Exception as e:
            print(f"Error deleting database {database_name}: {e}")
            return False