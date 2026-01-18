"""
Lamba Subscription & Billing Management System
Handles subscription states, grace periods, warnings, and feature restrictions
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import enum


class SubscriptionStatus(enum.Enum):
    """Subscription lifecycle states"""
    TRIAL = 'trial'                    # 14-day free trial
    ACTIVE = 'active'                  # Paid subscription active
    GRACE_PERIOD = 'grace'             # 7-day grace period after expiration
    SUSPENDED = 'suspended'            # Hard stop due to payment failure
    CANCELLED = 'cancelled'            # User cancelled
    EXPIRED = 'expired'                # Grace period ended


class SubscriptionBillingModel(models.Model):
    """Enhanced subscription tracking with billing and grace period management"""
    
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    
    PAYMENT_METHODS = [
        ('stripe', 'Stripe'),
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('free_trial', 'Free Trial'),
    ]
    
    company = models.OneToOneField(
        'estateApp.Company',
        on_delete=models.CASCADE,
        related_name='billing'
    )
    
    # Current subscription state
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in SubscriptionStatus],
        default='trial'
    )
    
    # Trial period
    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Paid subscription
    current_plan = models.ForeignKey(
        'superAdmin.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_subscriptions'
    )
    subscription_started_at = models.DateTimeField(null=True, blank=True)
    subscription_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Billing cycle and renewal
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLES,
        default='monthly'
    )
    auto_renew = models.BooleanField(default=True)
    next_billing_date = models.DateField(null=True, blank=True)
    
    # Grace period (7 days after expiration)
    grace_period_started_at = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Payment tracking
    last_payment_date = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        null=True,
        blank=True
    )
    
    # Billing contact info
    billing_email = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Email for receipts and renewal notices"
    )
    billing_contact = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Billing contact name or department"
    )
    
    # Payment gateway IDs
    stripe_subscription_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    paystack_subscription_code = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    
    # Price tracking
    monthly_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    annual_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Warnings and notifications
    warning_level = models.IntegerField(
        default=0,
        help_text="0=No warning, 1=Yellow, 2=Orange, 3=Red"
    )
    last_warning_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Subscription Billing"
        verbose_name_plural = "Subscription Billings"
    
    def __str__(self):
        return f"{self.company.company_name} - {self.status}"
    
    # ==================== STATUS CHECKING ====================
    
    def refresh_status(self):
        """Update subscription status based on dates.

        Important: this method must persist changes (status/date fields) and keep
        the related Company model in sync because many parts of the app rely on
        Company.subscription_* fields for access control and UI.
        """
        now = timezone.now()

        previous_status = self.status
        update_fields = set()

        # Trial active
        if self.trial_ends_at and now < self.trial_ends_at:
            self.status = SubscriptionStatus.TRIAL.value
            update_fields.add('status')

        # Paid subscription active
        elif self.subscription_ends_at and now < self.subscription_ends_at:
            if self.status != SubscriptionStatus.ACTIVE.value:
                self.status = SubscriptionStatus.ACTIVE.value
                self.last_payment_date = now
                update_fields.update({'status', 'last_payment_date'})

        # Grace period
        elif self.grace_period_ends_at and now < self.grace_period_ends_at:
            self.status = SubscriptionStatus.GRACE_PERIOD.value
            update_fields.add('status')

        # Expired
        elif self.grace_period_ends_at and now >= self.grace_period_ends_at:
            self.status = SubscriptionStatus.EXPIRED.value
            update_fields.add('status')

        # Persist only if something changed
        if update_fields and (previous_status != self.status or 'last_payment_date' in update_fields):
            self.save(update_fields=list(update_fields))

        # Always attempt to sync company fields (cheap, avoids drift)
        try:
            self._sync_company_subscription_fields()
        except Exception:
            # Never break request flow due to sync issues
            pass

    def _sync_company_subscription_fields(self):
        """Mirror billing state into Company fields used across the app."""
        company = getattr(self, 'company', None)
        if not company:
            return

        # Map richer billing statuses to Company.subscription_status choices
        mapped_status = self.status
        if mapped_status in {SubscriptionStatus.GRACE_PERIOD.value, SubscriptionStatus.EXPIRED.value}:
            mapped_status = 'suspended'
        elif mapped_status not in {'trial', 'active', 'suspended', 'cancelled'}:
            mapped_status = 'suspended'

        # Best-effort tier sync from current plan
        plan = getattr(self, 'current_plan', None)
        if plan and getattr(plan, 'tier', None):
            company.subscription_tier = plan.tier

        company.subscription_status = mapped_status
        company.trial_ends_at = self.trial_ends_at
        company.subscription_ends_at = self.subscription_ends_at
        company.grace_period_ends_at = self.grace_period_ends_at
        company.is_read_only_mode = bool(self.is_grace_period() or self.is_expired())

        # Keep started/renewed timestamps aligned when available
        if self.subscription_started_at and not company.subscription_started_at:
            company.subscription_started_at = self.subscription_started_at
        if self.last_payment_date:
            company.subscription_renewed_at = self.last_payment_date

        company.save(update_fields=[
            'subscription_tier',
            'subscription_status',
            'trial_ends_at',
            'subscription_ends_at',
            'grace_period_ends_at',
            'is_read_only_mode',
            'subscription_started_at',
            'subscription_renewed_at',
        ])
    
    def is_trial(self):
        """Check if in trial period"""
        self.refresh_status()
        return self.status == SubscriptionStatus.TRIAL.value
    
    def is_active(self):
        """Check if subscription is active (trial or paid)"""
        self.refresh_status()
        return self.status in [
            SubscriptionStatus.TRIAL.value,
            SubscriptionStatus.ACTIVE.value
        ]
    
    def is_grace_period(self):
        """Check if in grace period"""
        self.refresh_status()
        return self.status == SubscriptionStatus.GRACE_PERIOD.value
    
    def is_suspended(self):
        """Check if suspended"""
        return self.status == SubscriptionStatus.SUSPENDED.value
    
    def is_expired(self):
        """Check if expired"""
        self.refresh_status()
        return self.status == SubscriptionStatus.EXPIRED.value
    
    # ==================== WARNING LEVELS ====================
    
    def get_warning_level(self):
        """
        Determine warning level based on time until expiration
        0 = No warning (>7 days)
        1 = Yellow (4-7 days)
        2 = Orange (2-4 days)
        3 = Red (<2 days or grace period)
        """
        now = timezone.now()
        
        # Trial expiration
        if self.is_trial() and self.trial_ends_at:
            days_left = (self.trial_ends_at - now).days
            if days_left <= 0:
                return 3  # Red
            elif days_left <= 2:
                return 3  # Red
            elif days_left <= 4:
                return 2  # Orange
            elif days_left <= 7:
                return 1  # Yellow
            return 0  # No warning
        
        # Subscription expiration
        if self.subscription_ends_at:
            days_left = (self.subscription_ends_at - now).days
            if self.is_grace_period():
                return 3  # Red - Grace period active
            elif days_left <= 0:
                return 3  # Red
            elif days_left <= 2:
                return 3  # Red
            elif days_left <= 4:
                return 2  # Orange
            elif days_left <= 7:
                return 1  # Yellow
            return 0  # No warning
        
        return 0
    
    def should_show_warning_banner(self):
        """Check if warning banner should be displayed"""
        level = self.get_warning_level()
        return level > 0
    
    def get_warning_message(self):
        """Get appropriate warning message"""
        now = timezone.now()
        
        if self.is_trial():
            days_left = (self.trial_ends_at - now).days if self.trial_ends_at else 0
            if days_left <= 0:
                return {
                    'level': 'red',
                    'icon': 'fa-exclamation-circle',
                    'title': '⚠️ Trial Period Expired',
                    'message': f'Your 14-day trial has ended. Upgrade to a paid plan to continue.',
                    'cta': 'Upgrade Now',
                    'cta_action': 'upgrade'
                }
            elif days_left == 1:
                return {
                    'level': 'red',
                    'icon': 'fa-exclamation-circle',
                    'title': '⏰ Last Day of Trial!',
                    'message': f'Your trial expires tomorrow at {self.trial_ends_at.strftime("%I:%M %p")}. Upgrade now to avoid service interruption.',
                    'cta': 'Upgrade Now',
                    'cta_action': 'upgrade'
                }
            elif days_left <= 2:
                return {
                    'level': 'red',
                    'icon': 'fa-clock',
                    'title': '⚠️ Trial Expiring Soon',
                    'message': f'Your trial expires in {days_left} days. Plan your upgrade now.',
                    'cta': 'View Plans',
                    'cta_action': 'view_plans'
                }
            elif days_left <= 4:
                return {
                    'level': 'orange',
                    'icon': 'fa-calendar-check',
                    'title': 'Trial Expiring',
                    'message': f'Your trial expires in {days_left} days. Choose your plan to continue.',
                    'cta': 'Choose Plan',
                    'cta_action': 'choose_plan'
                }
            elif days_left <= 7:
                return {
                    'level': 'yellow',
                    'icon': 'fa-info-circle',
                    'title': 'Upcoming Upgrade',
                    'message': f'Your trial expires in {days_left} days.',
                    'cta': 'Explore Plans',
                    'cta_action': 'explore_plans'
                }
        
        elif self.is_grace_period():
            days_left = (self.grace_period_ends_at - now).days if self.grace_period_ends_at else 0
            return {
                'level': 'red',
                'icon': 'fa-exclamation-triangle',
                'title': '🚨 Grace Period Active',
                'message': f'Service access is limited. Renew subscription in {days_left} days to restore full access.',
                'cta': 'Renew Now',
                'cta_action': 'renew'
            }
        
        elif self.is_active():
            days_left = (self.subscription_ends_at - now).days if self.subscription_ends_at else 0
            if days_left <= 2:
                return {
                    'level': 'red',
                    'icon': 'fa-alert',
                    'title': '⚠️ Subscription Expiring Soon',
                    'message': f'Your subscription expires in {days_left} days.',
                    'cta': 'Renew',
                    'cta_action': 'renew'
                }
            elif days_left <= 4:
                return {
                    'level': 'orange',
                    'icon': 'fa-calendar',
                    'title': 'Subscription Reminder',
                    'message': f'Your subscription expires in {days_left} days.',
                    'cta': 'Renew',
                    'cta_action': 'renew'
                }
            elif days_left <= 7:
                return {
                    'level': 'yellow',
                    'icon': 'fa-info-circle',
                    'title': 'Subscription Expiring',
                    'message': f'Your subscription expires in {days_left} days.',
                    'cta': 'Renew',
                    'cta_action': 'renew'
                }
        
        return None
    
    # ==================== COUNTDOWN & TIME ====================
    
    def get_days_remaining(self):
        """Get days until expiration"""
        now = timezone.now()
        
        if self.is_trial() and self.trial_ends_at:
            days = (self.trial_ends_at - now).days
            return max(0, days)
        
        if self.subscription_ends_at:
            days = (self.subscription_ends_at - now).days
            return max(0, days)
        
        if self.is_grace_period() and self.grace_period_ends_at:
            days = (self.grace_period_ends_at - now).days
            return max(0, days)
        
        return 0
    
    def get_hours_remaining(self):
        """Get hours until expiration"""
        now = timezone.now()
        
        end_date = None
        if self.is_trial():
            end_date = self.trial_ends_at
        elif self.is_active():
            end_date = self.subscription_ends_at
        elif self.is_grace_period():
            end_date = self.grace_period_ends_at
        
        if end_date:
            hours = (end_date - now).total_seconds() / 3600
            return max(0, int(hours))
        
        return 0
    
    def get_expiration_datetime(self):
        """Get exact expiration datetime"""
        if self.is_trial():
            return self.trial_ends_at
        elif self.subscription_ends_at:
            return self.subscription_ends_at
        elif self.is_grace_period():
            return self.grace_period_ends_at
        return None
    
    # ==================== GRACE PERIOD LOGIC ====================
    
    def start_grace_period(self):
        """Initiate grace period after subscription expires"""
        now = timezone.now()
        self.grace_period_started_at = now
        self.grace_period_ends_at = now + timedelta(days=7)
        self.status = SubscriptionStatus.GRACE_PERIOD.value
        self.save()
    
    def has_grace_period_remaining(self):
        """Check if grace period still has time"""
        if not self.is_grace_period():
            return False
        
        return timezone.now() < self.grace_period_ends_at
    
    def grace_period_days_remaining(self):
        """Get days remaining in grace period"""
        if not self.has_grace_period_remaining():
            return 0
        
        days = (self.grace_period_ends_at - timezone.now()).days
        return max(0, days)
    
    # ==================== RESTRICTIONS ====================
    
    def can_access_features(self):
        """Check if company can access all features"""
        return self.is_active()
    
    def can_create_client(self):
        """Check if company can add new clients"""
        # Active + Grace period allowed
        return self.status in [
            SubscriptionStatus.TRIAL.value,
            SubscriptionStatus.ACTIVE.value
        ]
    
    def can_create_allocation(self):
        """Check if company can create allocations"""
        return self.is_active()
    
    def can_use_api(self):
        """Check if company can use API"""
        return self.is_active()
    
    def get_access_restrictions(self):
        """Get current access restrictions based on status"""
        restrictions = {
            'can_access_dashboard': self.status != SubscriptionStatus.EXPIRED.value,
            'can_create_clients': self.can_create_client(),
            'can_create_allocations': self.can_create_allocation(),
            'can_use_api': self.can_use_api(),
            'can_export_data': self.is_active(),
            'read_only_mode': self.is_grace_period() or self.is_expired(),
            'message': self.get_access_restriction_message()
        }
        return restrictions
    
    def get_access_restriction_message(self):
        """Get message explaining current restrictions"""
        if self.is_expired():
            return "Subscription expired. All features are disabled. Please renew to continue."
        elif self.is_grace_period():
            days = self.grace_period_days_remaining()
            return f"Grace period active. Read-only mode enabled. Renew within {days} days to restore access."
        elif self.is_trial():
            days = self.get_days_remaining()
            return f"Trial active. {days} days remaining."
        elif self.is_active():
            return "Subscription active. Full access enabled."
        return "Contact support for access details."
    
    # ==================== PRICING ====================
    
    def update_billing_amounts(self):
        """Sync pricing from subscription plan"""
        if self.current_plan:
            self.monthly_amount = self.current_plan.monthly_price
            self.annual_amount = self.current_plan.annual_price or (
                self.current_plan.monthly_price * 12
            )
            self.save()
    
    def get_current_amount(self):
        """Get amount charged based on billing cycle"""
        if self.billing_cycle == 'annual':
            return self.annual_amount
        return self.monthly_amount
    
    def calculate_proration(self, from_date, to_date):
        """Calculate prorated amount for date range"""
        days = (to_date - from_date).days
        daily_rate = self.get_current_amount() / 30
        return Decimal(str(days)) * daily_rate


class SubscriptionFeatureAccess(models.Model):
    """Track which features are accessible at each tier level"""
    
    plan = models.ForeignKey(
        'superAdmin.SubscriptionPlan',
        on_delete=models.CASCADE,
        related_name='feature_access'
    )
    
    feature_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)
    
    # Rate limiting
    daily_limit = models.IntegerField(null=True, blank=True)
    monthly_limit = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['plan', 'feature_name']
        verbose_name = "Subscription Feature Access"
        verbose_name_plural = "Subscription Feature Access"
    
    def __str__(self):
        return f"{self.plan.name} - {self.feature_name}"


class BillingHistory(models.Model):
    """Track all billing transactions"""
    
    TRANSACTION_TYPES = [
        ('charge', 'Charge'),
        ('refund', 'Refund'),
        ('proration', 'Proration'),
        ('adjustment', 'Adjustment'),
    ]
    
    TRANSACTION_STATES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    billing = models.ForeignKey(
        SubscriptionBillingModel,
        on_delete=models.CASCADE,
        related_name='transaction_history'
    )
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    state = models.CharField(max_length=20, choices=TRANSACTION_STATES, default='pending')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    
    description = models.TextField()
    transaction_id = models.CharField(max_length=255, unique=True)
    
    billing_date = models.DateTimeField()
    due_date = models.DateField()
    paid_date = models.DateTimeField(null=True, blank=True)
    
    invoice_number = models.CharField(max_length=100, unique=True)
    
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-billing_date']
        verbose_name = "Billing History"
        verbose_name_plural = "Billing Histories"
    
    def __str__(self):
        return f"{self.invoice_number} - ₦{self.amount} ({self.state})"
    
    def mark_paid(self):
        """Mark transaction as paid"""
        self.state = 'completed'
        self.paid_date = timezone.now()
        self.save()
    
    def mark_failed(self):
        """Mark transaction as failed"""
        self.state = 'failed'
        self.save()
