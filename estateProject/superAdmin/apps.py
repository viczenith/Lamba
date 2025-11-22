from django.apps import AppConfig


class SuperAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superAdmin'
    verbose_name = 'Super Admin - Master Tenant Management'
    
    def ready(self):
        """Import signals when app is ready"""
        try:
            import superAdmin.signals
        except ImportError:
            pass
