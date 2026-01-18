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
    get_plan_details,
    create_plan,
    update_plan,
    toggle_plan_status,
    delete_plan,
    get_billing_settings,
    save_billing_settings,
    get_promo_codes,
    get_promo_code_detail,
    create_promo_code,
    update_promo_code,
    toggle_promo_status,
    delete_promo_code,
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
    
    # Plan Management API
    path('api/plans/<int:plan_id>/', get_plan_details, name='get_plan_details'),
    path('api/plans/create/', create_plan, name='create_plan'),
    path('api/plans/<int:plan_id>/update/', update_plan, name='update_plan'),
    path('api/plans/<int:plan_id>/toggle/', toggle_plan_status, name='toggle_plan_status'),
    path('api/plans/<int:plan_id>/delete/', delete_plan, name='delete_plan'),
    
    # Promo Code Management API
    path('api/promo-codes/', get_promo_codes, name='get_promo_codes'),
    path('api/promo-codes/<int:code_id>/', get_promo_code_detail, name='get_promo_code_detail'),
    path('api/promo-codes/create/', create_promo_code, name='create_promo_code'),
    path('api/promo-codes/<int:code_id>/update/', update_promo_code, name='update_promo_code'),
    path('api/promo-codes/<int:code_id>/toggle/', toggle_promo_status, name='toggle_promo_status'),
    path('api/promo-codes/<int:code_id>/delete/', delete_promo_code, name='delete_promo_code'),
    
    # Billing Settings API
    path('api/billing/settings/', get_billing_settings, name='get_billing_settings'),
    path('api/billing/settings/save/', save_billing_settings, name='save_billing_settings'),
]
