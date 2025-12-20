"""
URL Configuration for Subscription & Billing Management
Integrated into company admin interface (company_profile.html)
"""

from django.urls import path
from . import subscription_views

urlpatterns = [
    # ===== SUBSCRIPTION PLANS =====
    path('api/plans/', 
         subscription_views.get_subscription_plans, 
         name='get_subscription_plans'),
    
    path('api/subscription/status/', 
         subscription_views.get_subscription_status, 
         name='get_subscription_status'),
    
    # ===== SUBSCRIPTION MANAGEMENT =====
    path('subscription/dashboard/', 
         subscription_views.subscription_dashboard, 
         name='subscription_dashboard'),
    
    path('subscription/renew/', 
         subscription_views.renew_subscription, 
         name='renew_subscription'),
    
    path('subscription/upgrade/', 
         subscription_views.upgrade_subscription, 
         name='upgrade_subscription'),
    
    # ===== PAYMENT PROCESSING =====
    path('subscription/payment/process/', 
         subscription_views.process_payment, 
         name='process_payment'),
    
    path('subscription/payment/stripe/confirm/', 
         subscription_views.confirm_stripe_payment, 
         name='confirm_stripe_payment'),
    
    path('subscription/payment/paystack/confirm/', 
         subscription_views.confirm_paystack_payment, 
         name='confirm_paystack_payment'),
    
    # ===== BILLING & INVOICES =====
    path('api/billing/history/', 
         subscription_views.get_billing_history, 
         name='get_billing_history'),
    
    path('subscription/billing/invoice/<int:invoice_id>/download/', 
         subscription_views.download_invoice, 
         name='download_invoice'),
    
    # ===== SUBSCRIPTION RECEIPTS =====
    path('subscription/receipt/<int:transaction_id>/', 
         subscription_views.generate_subscription_receipt, 
         name='subscription-receipt'),

    # Backward-compatible alias used by some admin templates
    path('admin/subscription/receipt/<int:transaction_id>/',
         subscription_views.generate_subscription_receipt,
         name='admin-subscription-receipt'),
]
