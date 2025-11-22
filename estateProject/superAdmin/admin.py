"""
Super Admin Django Admin Configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from .models import (
    PlatformConfiguration, SuperAdminUser, SubscriptionPlan, 
    CompanySubscription, PlatformInvoice, PlatformAnalytics, SystemAuditLog,
    CompanyOnboarding, FeatureFlag, SystemNotification
)


@admin.register(PlatformConfiguration)
class PlatformConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Platform Identity', {
            'fields': ('platform_name', 'platform_tagline', 'platform_logo', 'platform_email', 'platform_phone')
        }),
        ('Financial Configuration', {
            'fields': ('default_currency', 'commission_rate', 'starter_price', 'professional_price', 'enterprise_price')
        }),
        ('Trial Configuration', {
            'fields': ('trial_days', 'trial_max_plots', 'trial_max_agents')
        }),
        ('System Limits', {
            'fields': ('max_api_calls_per_hour', 'max_companies', 'maintenance_mode')
        }),
        ('Feature Flags', {
            'fields': ('enable_marketplace', 'enable_co_buying', 'enable_blockchain_verification', 
                      'enable_ai_matching', 'enable_rental_automation')
        }),
        ('Notifications', {
            'fields': ('admin_notification_email', 'slack_webhook_url')
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one configuration
        return not PlatformConfiguration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SuperAdminUser)
class SuperAdminUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'admin_level', 'can_access_all_companies', 'can_modify_subscriptions', 
                   'login_count', 'last_login_at', 'created_at')
    list_filter = ('admin_level', 'can_access_all_companies', 'can_modify_subscriptions')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('login_count', 'last_login_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'admin_level')
        }),
        ('Permissions', {
            'fields': ('can_access_all_companies', 'can_modify_subscriptions', 
                      'can_view_financials', 'can_manage_users')
        }),
        ('Activity', {
            'fields': ('login_count', 'last_login_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'monthly_price_display', 'annual_price_display', 
                   'max_plots', 'max_agents', 'is_active', 'is_visible')
    list_filter = ('tier', 'is_active', 'is_visible')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'tier', 'description')
        }),
        ('Pricing', {
            'fields': ('monthly_price', 'annual_price', 'setup_fee')
        }),
        ('Limits', {
            'fields': ('max_plots', 'max_agents', 'max_admins', 'max_api_calls_daily', 'max_storage_gb')
        }),
        ('Features', {
            'fields': ('features',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_visible', 'created_at', 'updated_at')
        }),
    )
    
    def monthly_price_display(self, obj):
        return f"₦{obj.monthly_price:,.0f}"
    monthly_price_display.short_description = "Monthly Price"
    
    def annual_price_display(self, obj):
        return f"₦{obj.annual_price:,.0f}"
    annual_price_display.short_description = "Annual Price"


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('company', 'plan', 'billing_cycle', 'payment_status', 
                   'current_period_end', 'auto_renew', 'days_until_renewal')
    list_filter = ('billing_cycle', 'payment_status', 'auto_renew', 'plan')
    search_fields = ('company__company_name', 'stripe_subscription_id', 'paystack_subscription_code')
    readonly_fields = ('started_at', 'created_at', 'updated_at', 'days_until_renewal')
    date_hierarchy = 'current_period_end'
    
    fieldsets = (
        ('Company & Plan', {
            'fields': ('company', 'plan', 'billing_cycle', 'payment_status')
        }),
        ('Dates', {
            'fields': ('started_at', 'current_period_start', 'current_period_end', 
                      'trial_ends_at', 'cancelled_at')
        }),
        ('Payment Integration', {
            'fields': ('stripe_subscription_id', 'paystack_subscription_code')
        }),
        ('Billing', {
            'fields': ('auto_renew', 'last_payment_at', 'next_billing_at', 
                      'amount_paid', 'amount_due')
        }),
    )
    
    def company_link(self, obj):
        url = reverse('admin:estateApp_company_change', args=[obj.company.id])
        return format_html('<a href="{}">{}</a>', url, obj.company.company_name)
    company_link.short_description = "Company"


@admin.register(PlatformInvoice)
class PlatformInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'company', 'total_amount_display', 'status', 
                   'issue_date', 'due_date', 'paid_date')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'company__company_name', 'payment_reference')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('Invoice Details', {
            'fields': ('invoice_number', 'company', 'subscription', 'description', 'notes')
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_amount', 'total_amount', 'amount_paid')
        }),
        ('Status & Dates', {
            'fields': ('status', 'issue_date', 'due_date', 'paid_date')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_reference')
        }),
    )
    
    def total_amount_display(self, obj):
        return f"₦{obj.total_amount:,.2f}"
    total_amount_display.short_description = "Total Amount"
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        for invoice in queryset:
            if invoice.status != 'paid':
                invoice.mark_as_paid()
        self.message_user(request, f"{queryset.count()} invoice(s) marked as paid.")
    mark_as_paid.short_description = "Mark selected invoices as paid"


@admin.register(PlatformAnalytics)
class PlatformAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_companies', 'active_companies', 'new_companies_today',
                   'total_users', 'revenue_today_display', 'mrr_display')
    list_filter = ('date',)
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Company Metrics', {
            'fields': ('total_companies', 'active_companies', 'trial_companies', 
                      'suspended_companies', 'new_companies_today')
        }),
        ('User Metrics', {
            'fields': ('total_users', 'total_clients', 'total_marketers', 'total_admins', 'new_users_today')
        }),
        ('Property Metrics', {
            'fields': ('total_properties', 'properties_sold_today', 'total_plots_allocated')
        }),
        ('Financial Metrics', {
            'fields': ('total_revenue', 'revenue_today', 'mrr', 'arr', 
                      'platform_commission_earned', 'marketer_commission_paid')
        }),
        ('System Metrics', {
            'fields': ('api_calls_today', 'storage_used_gb')
        }),
    )
    
    def revenue_today_display(self, obj):
        return f"₦{obj.revenue_today:,.2f}"
    revenue_today_display.short_description = "Revenue Today"
    
    def mrr_display(self, obj):
        return f"₦{obj.mrr:,.2f}"
    mrr_display.short_description = "MRR"
    
    def has_add_permission(self, request):
        return False


@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'admin_user', 'action_type', 'target_company', 'ip_address')
    list_filter = ('action_type', 'created_at')
    search_fields = ('description', 'admin_user__user__email', 'target_company__company_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Action', {
            'fields': ('admin_user', 'action_type', 'target_company', 'description')
        }),
        ('Context', {
            'fields': ('ip_address', 'user_agent', 'changes', 'metadata')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CompanyOnboarding)
class CompanyOnboardingAdmin(admin.ModelAdmin):
    list_display = ('company', 'completion_percentage', 'current_step', 'is_completed', 
                   'needs_help', 'assigned_support_admin')
    list_filter = ('is_completed', 'needs_help', 'current_step')
    search_fields = ('company__company_name',)
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    
    fieldsets = (
        ('Company', {
            'fields': ('company',)
        }),
        ('Progress', {
            'fields': ('current_step', 'steps_completed', 'completion_percentage', 
                      'is_completed', 'completed_at')
        }),
        ('Support', {
            'fields': ('needs_help', 'help_requested_at', 'assigned_support_admin')
        }),
    )


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_enabled_globally', 'rollout_percentage', 'created_at')
    list_filter = ('is_enabled_globally',)
    search_fields = ('name', 'description')
    filter_horizontal = ('enabled_for_companies',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Feature', {
            'fields': ('name', 'description')
        }),
        ('Status', {
            'fields': ('is_enabled_globally', 'rollout_percentage')
        }),
        ('Targeted Rollout', {
            'fields': ('enabled_for_companies',)
        }),
    )


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'priority', 'is_sent', 
                   'send_to_all_companies', 'scheduled_at', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_sent', 'is_active')
    search_fields = ('title', 'message')
    filter_horizontal = ('target_companies',)
    readonly_fields = ('sent_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Notification', {
            'fields': ('title', 'message', 'notification_type', 'priority')
        }),
        ('Targeting', {
            'fields': ('send_to_all_companies', 'target_companies')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'sent_at')
        }),
        ('Status', {
            'fields': ('is_active', 'is_sent', 'created_by')
        }),
    )
