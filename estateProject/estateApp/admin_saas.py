"""
Multi-tenant aware Django Admin Configuration
Ensures users only see and modify data from their company
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from .models import (
    Company, CustomUser, AdminUser, ClientUser, MarketerUser, SupportUser,
    MarketerAffiliation, MarketerCommission, ClientDashboard, ClientPropertyView
)
from django.utils import timezone


class TenantAwareAdminMixin:
    """
    Mixin to make Django admin respect multi-tenancy
    Only show objects belonging to user's company
    """
    
    def get_queryset(self, request):
        """Filter queryset based on user's company"""
        qs = super().get_queryset(request)
        
        # Superusers see everything
        if request.user.is_superuser:
            return qs
        
        # Non-admin users see nothing
        if request.user.role not in ['admin', 'support']:
            return qs.none()
        
        # Admin/Support: filter by their company
        if hasattr(request.user, 'company_profile') and request.user.company_profile:
            return qs.filter(company=request.user.company_profile)
        
        return qs.none()
    
    def has_add_permission(self, request):
        """Only admins from active companies can add"""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.user.role == 'admin' and hasattr(request.user, 'company_profile'):
            return request.user.company_profile.is_active
        return False
    
    def has_change_permission(self, request, obj=None):
        """Only allow changes within own company"""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        
        # Check company ownership
        if hasattr(obj, 'company') and hasattr(request.user, 'company_profile'):
            return obj.company == request.user.company_profile
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion within own company"""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        
        if hasattr(obj, 'company') and hasattr(request.user, 'company_profile'):
            return obj.company == request.user.company_profile
        
        return False


@admin.register(Company)
class CompanyAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    """Company administration with SaaS fields"""
    
    list_display = (
        'company_name', 'subscription_tier', 'subscription_status',
        'is_trial_active', 'is_subscription_active', 'max_plots', 'is_active', 'created_at'
    )
    list_filter = ('subscription_status', 'subscription_tier', 'is_active', 'created_at')
    search_fields = ('company_name', 'registration_number', 'email', 'ceo_name')
    ordering = ('-created_at',)
    readonly_fields = ('api_key', 'stripe_customer_id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'registration_number', 'registration_date', 'location', 'logo')
        }),
        ('CEO Information', {
            'fields': ('ceo_name', 'ceo_dob')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'billing_email')
        }),
        ('Subscription & Billing', {
            'fields': (
                'subscription_tier', 'subscription_status', 'trial_ends_at',
                'subscription_ends_at', 'max_plots', 'max_agents', 'max_api_calls_daily',
                'stripe_customer_id'
            ),
            'classes': ('wide',)
        }),
        ('Customization', {
            'fields': ('custom_domain', 'theme_color', 'api_key'),
            'classes': ('wide',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_trial_active(self, obj):
        return obj.is_trial_active()
    is_trial_active.short_description = 'Trial Active'
    is_trial_active.boolean = True
    
    def is_subscription_active(self, obj):
        return obj.is_subscription_active()
    is_subscription_active.short_description = 'Subscription Active'
    is_subscription_active.boolean = True
    
    def has_add_permission(self, request):
        """Only superusers can create companies"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete companies"""
        return request.user.is_superuser


@admin.register(CustomUser)
class CustomUserAdmin(TenantAwareAdminMixin, UserAdmin):
    """User administration with multi-tenancy support"""
    
    list_display = ('full_name', 'email', 'phone', 'role', 'company_profile', 'is_active', 'date_registered')
    list_filter = ('role', 'is_active', 'is_staff', 'date_registered')
    search_fields = ('full_name', 'email', 'phone')
    ordering = ('-date_registered',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': ('full_name', 'address', 'phone', 'date_of_birth', 'profile_image')
        }),
        ('Company & Work', {
            'fields': ('company_profile', 'role', 'job', 'company', 'about', 'country')
        }),
        ('Permissions and Status', {
            'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_registered'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'full_name', 'phone', 'role', 'company_profile')
        }),
    )
    
    def get_queryset(self, request):
        """Limit to company users for non-superusers"""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        if hasattr(request.user, 'company_profile') and request.user.company_profile:
            return qs.filter(company_profile=request.user.company_profile)
        
        return qs.none()


@admin.register(MarketerAffiliation)
class MarketerAffiliationAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    """Marketer affiliation management"""
    
    list_display = (
        'marketer', 'company', 'commission_tier', 'status',
        'properties_sold', 'total_commissions_earned', 'date_affiliated'
    )
    list_filter = ('status', 'commission_tier', 'date_affiliated')
    search_fields = ('marketer__full_name', 'company__company_name')
    readonly_fields = ('date_affiliated', 'approval_date', 'suspension_date', 'termination_date')
    
    fieldsets = (
        ('Affiliation Details', {
            'fields': ('marketer', 'company', 'status')
        }),
        ('Commission Setup', {
            'fields': ('commission_tier', 'commission_rate')
        }),
        ('Performance', {
            'fields': ('properties_sold', 'total_sales_value', 'total_commissions_earned', 'total_commissions_paid')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_name', 'account_number'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_affiliated', 'approval_date', 'suspension_date', 'termination_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('marketer', 'company')


@admin.register(MarketerCommission)
class MarketerCommissionAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    """Commission tracking and management"""
    
    list_display = (
        'affiliation', 'commission_amount', 'status',
        'created_at', 'paid_at'
    )
    list_filter = ('status', 'created_at', 'paid_at')
    search_fields = ('affiliation__marketer__full_name', 'affiliation__company__company_name')
    readonly_fields = ('created_at', 'approved_at', 'paid_at', 'disputed_at')
    
    fieldsets = (
        ('Commission Details', {
            'fields': ('affiliation', 'plot_allocation', 'sale_amount', 'commission_rate', 'commission_amount')
        }),
        ('Status', {
            'fields': ('status', 'payment_reference')
        }),
        ('Dispute', {
            'fields': ('dispute_reason', 'disputed_at'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'approved_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('affiliation__company', 'affiliation__marketer')
    
    def get_readonly_fields(self, request, obj=None):
        """More fields readonly after creation"""
        if obj:  # Editing existing object
            return self.readonly_fields + ['affiliation', 'plot_allocation', 'sale_amount', 'commission_rate']
        return self.readonly_fields


@admin.register(ClientDashboard)
class ClientDashboardAdmin(admin.ModelAdmin):
    """Client dashboard monitoring"""
    
    list_display = (
        'client', 'total_properties_owned', 'total_invested',
        'portfolio_value', 'roi_percentage', 'updated_at'
    )
    list_filter = ('updated_at',)
    search_fields = ('client__full_name', 'client__email')
    readonly_fields = (
        'total_properties_owned', 'total_invested', 'portfolio_value',
        'roi_percentage', 'month_over_month_growth', 'projected_value_1yr',
        'projected_value_5yr', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        ('Client Info', {
            'fields': ('client',)
        }),
        ('Portfolio Summary', {
            'fields': (
                'total_properties_owned', 'total_invested', 'portfolio_value',
                'roi_percentage', 'month_over_month_growth'
            )
        }),
        ('Projections', {
            'fields': ('projected_value_1yr', 'projected_value_5yr')
        }),
        ('Preferences', {
            'fields': ('preferred_currency', 'notification_preferences')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Dashboards are created automatically"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Don't allow manual deletion"""
        return request.user.is_superuser


@admin.register(ClientPropertyView)
class ClientPropertyViewAdmin(admin.ModelAdmin):
    """Client property viewing analytics"""
    
    list_display = (
        'client', 'plot', 'view_count', 'is_interested',
        'is_favorited', 'last_viewed_at'
    )
    list_filter = ('is_interested', 'is_favorited', 'last_viewed_at')
    search_fields = ('client__full_name', 'plot__plot_number', 'plot__estate__name')
    readonly_fields = ('first_viewed_at', 'last_viewed_at', 'view_count')
    
    fieldsets = (
        ('View Info', {
            'fields': ('client', 'plot', 'view_count')
        }),
        ('Interest Tracking', {
            'fields': ('is_interested', 'is_favorited')
        }),
        ('Notes', {
            'fields': ('client_notes',)
        }),
        ('Dates', {
            'fields': ('first_viewed_at', 'last_viewed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Views are created via API"""
        return False
