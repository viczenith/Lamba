"""
Super Admin Models - Master Tenant Management
Controls all companies, subscriptions, billing, analytics, and platform-wide settings
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

User = get_user_model()


class PlatformConfiguration(models.Model):
    """
    Global platform settings that affect all tenants
    """
    # Platform Identity
    platform_name = models.CharField(max_length=255, default="Real Estate SaaS Platform")
    platform_tagline = models.CharField(max_length=500, blank=True)
    platform_logo = models.ImageField(upload_to='platform/', blank=True, null=True)
    platform_email = models.EmailField(default="admin@platform.com")
    platform_phone = models.CharField(max_length=20, blank=True)
    
    # Financial Configuration
    default_currency = models.CharField(max_length=3, default='NGN')
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=2.0,
        help_text="Platform commission on all transactions (%)"
    )
    
    # Subscription Pricing (Monthly in Naira)
    starter_price = models.DecimalField(max_digits=10, decimal_places=2, default=15000)
    professional_price = models.DecimalField(max_digits=10, decimal_places=2, default=35000)
    enterprise_price = models.DecimalField(max_digits=10, decimal_places=2, default=75000)
    
    # Trial Configuration
    trial_days = models.PositiveIntegerField(default=14)
    trial_max_plots = models.PositiveIntegerField(default=10)
    trial_max_agents = models.PositiveIntegerField(default=2)
    
    # System Limits
    max_api_calls_per_hour = models.PositiveIntegerField(default=1000)
    max_companies = models.PositiveIntegerField(default=10000, help_text="Max companies on platform")
    maintenance_mode = models.BooleanField(default=False)
    
    # Feature Flags
    enable_marketplace = models.BooleanField(default=True)
    enable_co_buying = models.BooleanField(default=True)
    enable_blockchain_verification = models.BooleanField(default=False)
    enable_ai_matching = models.BooleanField(default=False)
    enable_rental_automation = models.BooleanField(default=True)
    
    # Notifications
    admin_notification_email = models.EmailField()
    slack_webhook_url = models.URLField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Platform Configuration"
        verbose_name_plural = "Platform Configuration"
    
    def __str__(self):
        return self.platform_name
    
    def save(self, *args, **kwargs):
        # Ensure only one configuration exists
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Get or create the singleton configuration"""
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class SuperAdminUser(models.Model):
    """
    Platform super admins who can manage all tenants
    """
    ADMIN_LEVELS = [
        ('super', 'Super Admin - Full Access'),
        ('billing', 'Billing Admin'),
        ('support', 'Support Admin'),
        ('analytics', 'Analytics Admin'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='super_admin_profile'
    )
    admin_level = models.CharField(max_length=20, choices=ADMIN_LEVELS, default='support')
    can_access_all_companies = models.BooleanField(default=True)
    can_modify_subscriptions = models.BooleanField(default=False)
    can_view_financials = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    
    # Activity tracking
    last_login_at = models.DateTimeField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Super Admin User"
        verbose_name_plural = "Super Admin Users"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_admin_level_display()}"


class SubscriptionPlan(models.Model):
    """
    Defines subscription tiers with features and limits
    """
    PLAN_TIERS = [
        ('trial', 'Trial'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    tier = models.CharField(max_length=20, choices=PLAN_TIERS, unique=True)
    description = models.TextField()
    
    # Pricing
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    annual_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Annual price (usually 2 months free)")
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Limits
    max_plots = models.PositiveIntegerField(help_text="0 = unlimited")
    max_agents = models.PositiveIntegerField(help_text="0 = unlimited")
    max_admins = models.PositiveIntegerField(default=5)
    max_api_calls_daily = models.PositiveIntegerField(default=10000)
    max_storage_gb = models.PositiveIntegerField(default=10)
    
    # Features
    features = models.JSONField(default=dict, help_text="JSON of enabled features")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True, help_text="Show on pricing page")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
        ordering = ['monthly_price']
    
    def __str__(self):
        return f"{self.name} - ₦{self.monthly_price:,.0f}/month"


class CompanySubscription(models.Model):
    """
    Tracks subscription details for each company
    """
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
        ('trial', 'Trial'),
    ]
    
    PAYMENT_STATUS = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending'),
    ]
    
    company = models.OneToOneField(
        'estateApp.Company',
        on_delete=models.CASCADE,
        related_name='subscription_details'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Billing
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Dates
    started_at = models.DateTimeField(auto_now_add=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Payment Integration
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    paystack_subscription_code = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # Tracking
    auto_renew = models.BooleanField(default=True)
    last_payment_at = models.DateTimeField(null=True, blank=True)
    next_billing_at = models.DateTimeField(null=True, blank=True)
    
    # Financial
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Subscription"
        verbose_name_plural = "Company Subscriptions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_status', 'next_billing_at']),
            models.Index(fields=['company', 'payment_status']),
        ]
    
    def __str__(self):
        return f"{self.company.company_name} - {self.plan.name}"
    
    def is_active(self):
        """Check if subscription is active"""
        return self.payment_status == 'active' and self.current_period_end > timezone.now()
    
    def is_trial(self):
        """Check if in trial period"""
        return self.billing_cycle == 'trial' and self.trial_ends_at and self.trial_ends_at > timezone.now()
    
    def days_until_renewal(self):
        """Days remaining until next billing"""
        if self.next_billing_at:
            delta = self.next_billing_at - timezone.now()
            return max(0, delta.days)
        return 0


class PlatformInvoice(models.Model):
    """
    Platform-level invoices for company subscriptions and payments
    (Distinct from property invoices in estateApp)
    """
    INVOICE_STATUS = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    company = models.ForeignKey(
        'estateApp.Company',
        on_delete=models.CASCADE,
        related_name='platform_invoices'  # Changed from 'invoices'
    )
    subscription = models.ForeignKey(
        CompanySubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_invoices'  # Changed from 'invoices'
    )
    
    # Financial
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='draft')
    
    # Dates
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Details
    description = models.TextField()
    notes = models.TextField(blank=True)
    
    # Payment
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.company.company_name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number: INV-YYYYMM-XXXXX
            from datetime import datetime
            prefix = datetime.now().strftime('INV-%Y%m')
            last_invoice = PlatformInvoice.objects.filter(
                invoice_number__startswith=prefix
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.invoice_number = f"{prefix}-{new_number:05d}"
        
        super().save(*args, **kwargs)
    
    def mark_as_paid(self, payment_reference='', payment_method=''):
        """Mark invoice as paid"""
        self.status = 'paid'
        self.paid_date = timezone.now().date()
        self.amount_paid = self.total_amount
        self.payment_reference = payment_reference
        self.payment_method = payment_method
        self.save()


class PlatformAnalytics(models.Model):
    """
    Daily snapshot of platform-wide metrics
    """
    date = models.DateField(unique=True, db_index=True)
    
    # Company metrics
    total_companies = models.PositiveIntegerField(default=0)
    active_companies = models.PositiveIntegerField(default=0)
    trial_companies = models.PositiveIntegerField(default=0)
    suspended_companies = models.PositiveIntegerField(default=0)
    new_companies_today = models.PositiveIntegerField(default=0)
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    total_clients = models.PositiveIntegerField(default=0)
    total_marketers = models.PositiveIntegerField(default=0)
    total_admins = models.PositiveIntegerField(default=0)
    new_users_today = models.PositiveIntegerField(default=0)
    
    # Property metrics
    total_properties = models.PositiveIntegerField(default=0)
    properties_sold_today = models.PositiveIntegerField(default=0)
    total_plots_allocated = models.PositiveIntegerField(default=0)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    revenue_today = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    mrr = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Monthly Recurring Revenue")
    arr = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Annual Recurring Revenue")
    
    # Commission metrics
    platform_commission_earned = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    marketer_commission_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # System metrics
    api_calls_today = models.PositiveIntegerField(default=0)
    storage_used_gb = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Platform Analytics"
        verbose_name_plural = "Platform Analytics"
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.date}"


class SystemAuditLog(models.Model):
    """
    Comprehensive audit trail for all super admin actions
    """
    ACTION_TYPES = [
        ('company_created', 'Company Created'),
        ('company_suspended', 'Company Suspended'),
        ('company_activated', 'Company Activated'),
        ('subscription_changed', 'Subscription Changed'),
        ('user_modified', 'User Modified'),
        ('settings_changed', 'Settings Changed'),
        ('invoice_generated', 'Invoice Generated'),
        ('payment_processed', 'Payment Processed'),
        ('feature_toggled', 'Feature Toggled'),
        ('other', 'Other'),
    ]
    
    admin_user = models.ForeignKey(
        SuperAdminUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='system_audit_logs'  # Changed from 'audit_logs'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    target_company = models.ForeignKey(
        'estateApp.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_audit_logs'  # Changed from 'audit_logs'
    )
    
    # Details
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Metadata
    changes = models.JSONField(default=dict, help_text="Before/after values")
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "System Audit Log"
        verbose_name_plural = "System Audit Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin_user', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['target_company', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.action_type} by {self.admin_user} at {self.created_at}"


class CompanyOnboarding(models.Model):
    """
    Tracks onboarding progress for new companies
    """
    ONBOARDING_STEPS = [
        ('registration', 'Registration Complete'),
        ('email_verified', 'Email Verified'),
        ('profile_completed', 'Profile Completed'),
        ('first_property', 'First Property Added'),
        ('first_agent', 'First Agent Added'),
        ('first_client', 'First Client Added'),
        ('payment_method', 'Payment Method Added'),
        ('completed', 'Onboarding Completed'),
    ]
    
    company = models.OneToOneField(
        'estateApp.Company',
        on_delete=models.CASCADE,
        related_name='onboarding'
    )
    
    # Progress tracking
    current_step = models.CharField(max_length=30, default='registration')
    steps_completed = models.JSONField(default=list)
    completion_percentage = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    
    # Status
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Assistance
    needs_help = models.BooleanField(default=False)
    help_requested_at = models.DateTimeField(null=True, blank=True)
    assigned_support_admin = models.ForeignKey(
        SuperAdminUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_onboardings'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Onboarding"
        verbose_name_plural = "Company Onboardings"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company.company_name} - {self.completion_percentage}% complete"
    
    def mark_step_complete(self, step):
        """Mark an onboarding step as complete"""
        if step not in self.steps_completed:
            self.steps_completed.append(step)
            self.completion_percentage = int((len(self.steps_completed) / len(self.ONBOARDING_STEPS)) * 100)
            
            if self.completion_percentage >= 100:
                self.is_completed = True
                self.completed_at = timezone.now()
            
            self.save()


class FeatureFlag(models.Model):
    """
    Feature flags for gradual rollout and A/B testing
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    
    # Status
    is_enabled_globally = models.BooleanField(default=False)
    enabled_for_companies = models.ManyToManyField(
        'estateApp.Company',
        blank=True,
        related_name='enabled_features'
    )
    
    # Rollout
    rollout_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        help_text="Percentage of companies to enable for"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({'Enabled' if self.is_enabled_globally else 'Disabled'})"
    
    def is_enabled_for_company(self, company):
        """Check if feature is enabled for a specific company"""
        if self.is_enabled_globally:
            return True
        return self.enabled_for_companies.filter(id=company.id).exists()


class SystemNotification(models.Model):
    """
    System-wide notifications and announcements
    """
    NOTIFICATION_TYPES = [
        ('maintenance', 'Maintenance'),
        ('update', 'Update'),
        ('security', 'Security Alert'),
        ('feature', 'New Feature'),
        ('announcement', 'Announcement'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='medium')
    
    # Targeting
    send_to_all_companies = models.BooleanField(default=False)
    target_companies = models.ManyToManyField(
        'estateApp.Company',
        blank=True,
        related_name='system_notifications'
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_sent = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(
        SuperAdminUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_notifications'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Notification"
        verbose_name_plural = "System Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_priority_display()})"
