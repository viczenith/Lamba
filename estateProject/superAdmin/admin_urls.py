"""
SuperAdmin URL Configuration
All routes for the comprehensive management dashboard
"""

from django.urls import path
from .comprehensive_views import (
    SuperAdminDashboardView,
    CompanyManagementView,
    CompanyDetailView,
    UserManagementView,
    UserDetailView,
    SubscriptionManagementView,
    BillingManagementView,
    AnalyticsView,
    company_action,
    subscription_action,
    get_platform_stats,
)
from .views import SuperAdminLoginView, SuperAdminLogoutView

app_name = 'superadmin'

urlpatterns = [
    # Authentication
    path('login/', SuperAdminLoginView.as_view(), name='login'),
    path('logout/', SuperAdminLogoutView.as_view(), name='logout'),
    
    # Main Dashboard
    path('', SuperAdminDashboardView.as_view(), name='dashboard'),
    
    # Company Management
    path('companies/', CompanyManagementView.as_view(), name='company_management'),
    path('companies/<slug:slug>/', CompanyDetailView.as_view(), name='company_detail'),
    path('api/companies/action/', company_action, name='company_action'),
    
    # User Management
    path('users/', UserManagementView.as_view(), name='user_management'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    
    # Subscription Management
    path('subscriptions/', SubscriptionManagementView.as_view(), name='subscription_management'),
    path('api/subscriptions/action/', subscription_action, name='subscription_action'),
    
    # Billing Management
    path('billing/', BillingManagementView.as_view(), name='billing_management'),
    
    # Analytics
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    
    # API Endpoints
    path('api/stats/', get_platform_stats, name='platform_stats'),
]
