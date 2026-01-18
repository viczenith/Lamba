"""
Super Admin URL Configuration
"""
from django.urls import path
from . import views
from . import comprehensive_views as cv

app_name = 'superadmin'

urlpatterns = [
    # Authentication
    path('login/', views.SuperAdminLoginView.as_view(), name='login'),
    path('logout/', views.SuperAdminLogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', views.SuperAdminDashboardView.as_view(), name='dashboard'),
    path('dashboard/', views.SuperAdminDashboardView.as_view(), name='dashboard_alt'),
    
    # Companies
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/<int:pk>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('companies/<int:company_id>/suspend/', views.suspend_company, name='suspend_company'),
    path('companies/<int:company_id>/activate/', views.activate_company, name='activate_company'),
    
    # Analytics
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics'),
    
    # Subscriptions
    path('subscriptions/', cv.SubscriptionManagementView.as_view(), name='subscriptions'),
    
    # Billing
    path('billing/', cv.BillingManagementView.as_view(), name='billing'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoices'),
    
    # Audit Logs
    path('audit-logs/', views.AuditLogView.as_view(), name='audit_logs'),
    
    # Feature Flags
    path('feature-flags/', views.FeatureFlagManagementView.as_view(), name='feature_flags'),
    
    # Settings
    path('settings/', views.SystemSettingsView.as_view(), name='settings'),
    
    # Access Denied
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
    
    # Plan & Billing Management API
    path('api/plans/<int:plan_id>/', cv.get_plan_details, name='get_plan_details'),
    path('api/plans/create/', cv.create_plan, name='create_plan'),
    path('api/plans/<int:plan_id>/update/', cv.update_plan, name='update_plan'),
    path('api/plans/<int:plan_id>/toggle/', cv.toggle_plan_status, name='toggle_plan_status'),
    path('api/plans/<int:plan_id>/delete/', cv.delete_plan, name='delete_plan'),
    path('api/billing/settings/', cv.get_billing_settings, name='get_billing_settings'),
    path('api/billing/settings/save/', cv.save_billing_settings, name='save_billing_settings'),
]
