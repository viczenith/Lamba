from django.apps import AppConfig


class TenantadminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenantAdmin'
    verbose_name = 'Tenant Admin Management'
    
    def ready(self):
        """Import signals when app is ready"""
        try:
            import tenantAdmin.signals
        except ImportError:
            pass
