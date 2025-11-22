"""
Tenant Admin URL Configuration
"""
from django.urls import path, include
from . import views

app_name = 'tenant_admin'

urlpatterns = [
    # Authentication
    path('login/', views.TenantAdminLoginView.as_view(), name='login'),
    path('logout/', views.TenantAdminLogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', views.TenantAdminDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.TenantAdminDashboardView.as_view(), name='dashboard-alt'),
    
    # Access Denied
    path('access-denied/', views.AccessDeniedView.as_view(), name='access-denied'),
    
    # API endpoints
    path('api/', include('tenantAdmin.api.urls')),
]
