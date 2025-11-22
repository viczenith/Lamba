"""
Tenant Admin API URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .auth_views import TenantAdminAuthViewSet

app_name = 'tenant_admin_api'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'auth', TenantAdminAuthViewSet, basename='auth')

urlpatterns = [
    # Function-based views
    path('dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
    path('recent-activity/', views.recent_activity, name='recent-activity'),
    path('system-health/', views.system_health, name='system-health'),
    
    # ViewSet routes
    path('', include(router.urls)),
]
