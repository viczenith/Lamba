from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
from django.utils import timezone
from django.db.models import Q


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
            if hasattr(qs, 'filter'):
                # Try to filter by company
                try:
                    return qs.filter(company=request.user.company_profile)
                except:
                    # If company field doesn't exist, try other patterns
                    try:
                        return qs.filter(estate__company=request.user.company_profile)
                    except:
                        return qs
            return qs
        
        return qs
    
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
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'company_name', 'subscription_tier', 'subscription_status',
        'is_trial_active_display', 'is_subscription_active_display',
        'max_plots', 'is_active', 'created_at'
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
            'fields': ('email', 'phone', 'billing_email', 'office_address')
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
        ('Cashier / Receipts', {
            'fields': ('cashier_name', 'cashier_signature', 'receipt_counter'),
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
    
    def is_trial_active_display(self, obj):
        return obj.is_trial_active()
    is_trial_active_display.short_description = 'Trial Active'
    is_trial_active_display.boolean = True
    
    def is_subscription_active_display(self, obj):
        return obj.is_subscription_active()
    is_subscription_active_display.short_description = 'Subscription Active'
    is_subscription_active_display.boolean = True
    
    def has_add_permission(self, request):
        """Only superusers can create companies"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete companies"""
        return request.user.is_superuser


@admin.register(CompanyCeo)
class CompanyCeoAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_primary', 'dob', 'created_at')
    list_filter = ('is_primary', 'company')
    search_fields = ('name', 'company__company_name')
    ordering = ('-is_primary', '-created_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('full_name', 'email', 'phone', 'role', 'date_registered', 'company', 'job', 'country')
    list_filter = ('role', 'date_registered', 'is_active', 'is_staff')
    search_fields = ('full_name', 'email', 'phone', 'company', 'job', 'country')
    ordering = ('date_registered',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'address', 'phone', 'date_of_birth', 'about', 'company', 'job', 'country', 'profile_image')}),
        ('Permissions and Role', {'fields': ('role', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_registered')}),
        # ('Marketer Info', {'fields': ('marketer',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'full_name', 'role')
        }),
    )


@admin.register(AdminUser)
class AdminUserAdmin(CustomUserAdmin):
    list_display = ('full_name', 'email', 'phone', 'date_registered')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'address', 'phone', 'date_of_birth', 'about', 'company', 'job', 'country', 'profile_image')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_registered')}),
    )


@admin.register(ClientUser)
class ClientUserAdmin(CustomUserAdmin):
    list_display = ('full_name', 'email', 'phone', 'assigned_marketer', 'date_registered', 'about', 'company', 'job', 'country', 'profile_image')

    def assigned_marketer(self, obj):
        return obj.marketer.full_name if obj.marketer else "Not Assigned"
    assigned_marketer.short_description = "Assigned Marketer"

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'address', 'phone', 'date_of_birth', 'about', 'company', 'job', 'country', 'profile_image')}),
        # ('Marketer Info', {'fields': ('marketer',)}),
        ('Marketer Info', {'fields': ('assigned_marketer',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_registered')}),
    )


@admin.register(MarketerUser)
class MarketerUserAdmin(CustomUserAdmin):
    list_display = ('full_name', 'email', 'phone', 'date_registered', 'about', 'company', 'job', 'country', 'profile_image')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'address', 'phone', 'date_of_birth', 'about', 'company', 'job', 'country', 'profile_image')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_registered')}),
    )


@admin.register(SupportUser)
class SupportUserAdmin(CustomUserAdmin):
    list_display = ('full_name', 'email', 'phone', 'date_registered', 'about', 'company', 'job', 'country', 'profile_image')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'address', 'phone', 'date_of_birth', 'about', 'company', 'job', 'country', 'profile_image')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_registered')}),
    )


class MessageAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'company', 'date_sent', 'is_read', 'status', 'is_encrypted']
    list_filter = ['is_read', 'status', 'company', 'date_sent', 'is_encrypted']
    search_fields = ['sender__username', 'recipient__username', 'content']
    readonly_fields = ['date_sent', 'is_encrypted']
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, status='read')
    mark_as_read.short_description = "Mark selected messages as read"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, status='unread')
    mark_as_unread.short_description = "Mark selected messages as unread"

admin.site.register(Message, MessageAdmin)



# ADD ESTATE

@admin.register(PlotSize)
class PlotSizeAdmin(admin.ModelAdmin):
    list_display = ("size",)
    search_fields = ("size",)

@admin.register(PlotNumber)
class PlotNumberAdmin(admin.ModelAdmin):
    list_display = ("number",)
    search_fields = ("number",)


# class EstatePlotInline(admin.TabularInline):
#     model = EstatePlot
#     extra = 1 
#     fields = ['estate', 'plot_numbers']
    # filter_horizontal = ('plot_sizes', 'plot_numbers')

@admin.register(Estate)
class EstateAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "estate_size", "title_deed", "date_added")
    search_fields = ("name", "location")
    list_filter = ("title_deed", "date_added")
    ordering = ("-date_added",)
    # inlines = [EstatePlotInline]

# @admin.register(EstatePlot)
# class EstatePlotAdmin(admin.ModelAdmin):
#     list_display = ("estate", "plot_sizes", "plot_numbers")
    # list_filter = ("estate",)
    # search_fields = ("estate__name",)
    # filter_horizontal = ( "plot_numbers")

# Register the intermediate model
@admin.register(PlotSizeUnits)
class PlotSizeUnitsAdmin(admin.ModelAdmin):
    list_display = ['estate_plot', 'plot_size', 'total_units', 'available_units']
    list_filter = ['estate_plot__estate', 'plot_size']
    search_fields = ['estate_plot__estate__name', 'plot_size__size']

class PlotSizeUnitsInline(admin.TabularInline):
    model = PlotSizeUnits
    extra = 1  # Number of empty forms to display

@admin.register(EstatePlot)
class EstatePlotAdmin(admin.ModelAdmin):
    inlines = [PlotSizeUnitsInline]
    list_display = ['estate', 'get_plot_sizes', 'get_plot_numbers']
    filter_horizontal = ('plot_numbers',)

    def get_plot_sizes(self, obj):
        return ", ".join([size.size for size in obj.plot_sizes.all()])
    get_plot_sizes.short_description = "Plot Sizes"

    def get_plot_numbers(self, obj):
        return ", ".join([num.number for num in obj.plot_numbers.all()])
    get_plot_numbers.short_description = "Plot Numbers"


# admin.site.register(PlotAllocation)
# @admin.register(PlotAllocation)
# class PlotAllocationAdmin(admin.ModelAdmin):
#     list_display = ('client', 'estate', 'plot_size', 'plot_number', 'payment_type', 'date_allocated')


class PlotSizeUnitsInline(admin.TabularInline):
    model = PlotSizeUnits
    extra = 1
    readonly_fields = ('available_units',)

class PlotAllocationAdmin(admin.ModelAdmin):
    list_display = ('client', 'get_plot_size', 'payment_type', 'date_allocated')
    list_filter = ('plot_size_unit__plot_size', 'payment_type')
    
    def get_plot_size(self, obj):
        return obj.plot_size_unit.plot_size.size
    get_plot_size.short_description = 'Plot Size'

admin.site.register(PlotAllocation, PlotAllocationAdmin)


admin.site.register(EstatePrototype)
admin.site.register(EstateAmenitie)
admin.site.register(EstateFloorPlan)


# MANAGEMENT DASHBOARD
# Land Plot Transactions
admin.site.register(Transaction)
admin.site.register(PaymentRecord)

# Sales Volume + Marketers Performance
admin.site.register(MarketerCommission)
admin.site.register(MarketerTarget)
admin.site.register(MarketerPerformanceRecord)

# VALUE EVALUATION
admin.site.register(PropertyPrice)
admin.site.register(PriceHistory)
admin.site.register(PromotionalOffer)


# MESSAGING AND BIRTHDAY.


# ============================================================================
# MULTI-TENANT SAAS ADMIN CLASSES
# ============================================================================

@admin.register(MarketerAffiliation)
class MarketerAffiliationAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    """Marketer affiliation management with multi-tenancy support"""
    
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


@admin.register(MarketerEarnedCommission)
class MarketerEarnedCommissionAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
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
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, status='unread')
    mark_as_unread.short_description = "Mark selected messages as unread"


@admin.register(ChatQueue)
class ChatQueueAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    list_display = ['company', 'client', 'first_message', 'status', 'priority', 'created_at', 'assigned_count']
    list_filter = ['status', 'priority', 'company', 'created_at']
    search_fields = ['company__name', 'client__username', 'first_message']
    readonly_fields = ['created_at', 'updated_at', 'assigned_count']
    
    def assigned_count(self, obj):
        return obj.assignments.count()
    assigned_count.short_description = "Assignments"


@admin.register(ChatAssignment)
class ChatAssignmentAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    list_display = ['chat_queue', 'assigned_to', 'status', 'sla_status', 'assigned_at', 'response_time', 'priority']
    list_filter = ['status', 'sla_status', 'priority', 'assigned_at']
    search_fields = ['chat_queue__company__name', 'assigned_to__username', 'chat_queue__client__username']
    readonly_fields = ['assigned_at', 'accepted_at', 'first_response_at', 'resolved_at', 'response_time', 'resolution_time']
    actions = ['accept_assignments', 'resolve_assignments', 'escalate_assignments']
    
    def accept_assignments(self, request, queryset):
        for assignment in queryset:
            assignment.accept_assignment(request.user)
    accept_assignments.short_description = "Accept selected assignments"
    
    def resolve_assignments(self, request, queryset):
        for assignment in queryset:
            assignment.resolve_assignment(request.user)
    resolve_assignments.short_description = "Resolve selected assignments"
    
    def escalate_assignments(self, request, queryset):
        for assignment in queryset:
            assignment.escalate_assignment(request.user, "Escalated via admin")
    escalate_assignments.short_description = "Escalate selected assignments"


@admin.register(ChatNotification)
class ChatNotificationAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    list_display = ['recipient', 'company', 'client', 'unread_count', 'is_urgent', 'last_message_at']
    list_filter = ['is_urgent', 'company', 'last_message_at']
    search_fields = ['recipient__username', 'company__name', 'client__username']
    readonly_fields = ['last_message_at', 'notified_at', 'dismissed_at']


@admin.register(ChatSLA)
class ChatSLAAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    list_display = ['company', 'priority', 'response_time_hours', 'resolution_time_hours', 'include_weekends']
    list_filter = ['priority', 'company', 'include_weekends']
    search_fields = ['company__name']


@admin.register(ChatResponseTracking)
class ChatResponseTrackingAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    list_display = ['company', 'date', 'total_chats', 'responded_chats', 'sla_compliance_rate', 'breached_chats']
    list_filter = ['company', 'date']
    search_fields = ['company__name']
    readonly_fields = ['total_chats', 'responded_chats', 'average_response_time', 'sla_compliance_rate', 'breached_chats']

