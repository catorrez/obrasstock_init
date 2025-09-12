from django.apps import AppConfig


class ControlPlaneConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'control_plane'
    
    def ready(self):
        """
        Initialize audit logging signals when Django starts
        """
        import control_plane.signals  # This registers all the signal handlers
