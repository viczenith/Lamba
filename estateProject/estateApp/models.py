import datetime
from datetime import date, time
from decimal import Decimal
import random
import re
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from dateutil.relativedelta import relativedelta
from multiselectfield import MultiSelectField
from django.db.models import Sum, Count, IntegerField, DecimalField, F, Q
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from datetime import timedelta


class CompanyAwareManager(models.Manager):
    """
    Custom manager that automatically filters querysets by current company.
    Prevents accidental data leaks from cross-company queries.
    """
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Get current company from thread-local storage via middleware
        try:
            from estateApp.middleware import get_current_company
            company = get_current_company()
        except ImportError:
            company = None
        
        # If company is set (and not super admin), filter by company
        if company:
            # Check if the model has a direct company field
            if hasattr(self.model, 'company'):
                return qs.filter(company=company)
            # Special handling for Payment model (company via invoice)
            elif self.model.__name__ == 'Payment':
                return qs.filter(invoice__company=company)
            # Special handling for models that should not be filtered by company
            # (e.g., Message, Notification - these might be global or filtered differently)
            elif self.model.__name__ in ['Message', 'Notification', 'UserNotification', 'PropertyRequest']:
                # These models don't have company fields and may need different filtering logic
                # For now, return unfiltered queryset (but this should be reviewed for security)
                return qs
        
        return qs


class Company(models.Model):
    """Company model for multi-tenant system"""
    SUBSCRIPTION_TIERS = [
        ('starter', 'Starter - 1 agent, 50 plots'),
        ('professional', 'Professional - 10 agents, 500 plots'),
        ('enterprise', 'Enterprise - Unlimited'),
    ]
    
    SUBSCRIPTION_STATUS = [
        ('trial', 'Trial - 14 Days'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core fields
    company_name = models.CharField(max_length=255, unique=True, verbose_name="Company Name")
    slug = models.SlugField(
        max_length=255, 
        unique=True, 
        db_index=True,
        null=True,
        blank=True,
        verbose_name="Company Slug (Tenancy ID)",
        help_text="Unique identifier for multi-tenant routing and isolation"
    )
    registration_number = models.CharField(max_length=100, unique=True, verbose_name="Registration Number")
    registration_date = models.DateField(verbose_name="Company Registration Date")
    location = models.CharField(max_length=255, verbose_name="Company Location")
    ceo_name = models.CharField(max_length=255, verbose_name="CEO Name")
    ceo_dob = models.DateField(verbose_name="CEO Date of Birth")
    email = models.EmailField(unique=True, verbose_name="Company Email")
    phone = models.CharField(max_length=15, verbose_name="Company Phone")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, verbose_name="Company Logo")
    
    # SaaS fields
    subscription_tier = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_TIERS,
        default='trial',
        verbose_name="Subscription Tier"
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS,
        default='trial',
        verbose_name="Subscription Status"
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Trial Ends At")
    subscription_ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Subscription Ends At")
    
    # Company limits based on tier
    max_plots = models.PositiveIntegerField(default=50, verbose_name="Max Plots Allowed")
    max_agents = models.PositiveIntegerField(default=1, verbose_name="Max Agents Allowed")
    max_api_calls_daily = models.PositiveIntegerField(default=1000, verbose_name="Max API Calls Per Day")
    
    # API call tracking (SaaS usage metrics)
    api_calls_today = models.PositiveIntegerField(default=0, verbose_name="API Calls Today")
    api_calls_reset_at = models.DateTimeField(null=True, blank=True, verbose_name="API Calls Reset At")
    
    # Current usage counts
    current_plots_count = models.PositiveIntegerField(default=0, verbose_name="Current Plots Count")
    current_agents_count = models.PositiveIntegerField(default=0, verbose_name="Current Agents Count")
    
    # Subscription dates
    subscription_started_at = models.DateTimeField(null=True, blank=True, verbose_name="Subscription Started At")
    subscription_renewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Subscription Last Renewed At")
    
    # Features and read-only mode
    features_available = models.JSONField(default=list, blank=True, verbose_name="Available Features")
    is_read_only_mode = models.BooleanField(default=False, verbose_name="Read-Only Mode")
    grace_period_ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Grace Period Ends At")
    data_deletion_date = models.DateTimeField(null=True, blank=True, verbose_name="Data Deletion Date")
    
    # Billing and receipts
    receipt_counter = models.PositiveIntegerField(default=1, verbose_name="Receipt Counter")
    cashier_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cashier Name")
    cashier_signature = models.ImageField(upload_to='cashier_signatures/', blank=True, null=True, verbose_name="Cashier Signature")
    office_address = models.TextField(blank=True, null=True, verbose_name="Office Address")
    
    # Customization
    custom_domain = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Custom Domain"
    )
    theme_color = models.CharField(max_length=7, default='#003366', verbose_name="Theme Color")
    
    # API Key for programmatic access
    api_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name="API Key"
    )
    
    # Billing
    billing_email = models.EmailField(null=True, blank=True, verbose_name="Billing Email")
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Stripe Customer ID"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscription_status', 'subscription_ends_at']),
            models.Index(fields=['api_key']),
            models.Index(fields=['custom_domain']),
            models.Index(fields=['stripe_customer_id']),
        ]

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        """Auto-generate unique slug from company_name for tenancy isolation"""
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.company_name)
            slug = base_slug
            counter = 1

            # Ensure slug is unique
            while Company.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        # Sync company limits based on subscription tier
        self.sync_plan_limits()

        super().save(*args, **kwargs)

    def get_marketer_by_company_id(self, company_marketer_id: int):
        """
        Get a marketer for this company by their company-specific ID.
        
        Example:
            marketer = company.get_marketer_by_company_id(1)  # Returns marketer with ID "LPLMKT001"
        """
        try:
            profile = self.marketer_profiles.get(company_marketer_id=company_marketer_id)
            return profile.marketer
        except Exception:
            return None

    def get_marketer_by_company_uid(self, company_marketer_uid: str):
        """
        Get a marketer for this company by their company-specific UID.
        
        Example:
            marketer = company.get_marketer_by_company_uid('LPLMKT001')
        """
        try:
            profile = self.marketer_profiles.get(company_marketer_uid=company_marketer_uid)
            return profile.marketer
        except Exception:
            return None

    def get_client_by_company_id(self, company_client_id: int):
        """
        Get a client for this company by their company-specific ID.
        
        Example:
            client = company.get_client_by_company_id(1)  # Returns client with ID "LPLCLT001"
        """
        try:
            profile = self.client_profiles.get(company_client_id=company_client_id)
            return profile.client
        except Exception:
            return None

    def get_client_by_company_uid(self, company_client_uid: str):
        """
        Get a client for this company by their company-specific UID.
        
        Example:
            client = company.get_client_by_company_uid('LPLCLT001')
        """
        try:
            profile = self.client_profiles.get(company_client_uid=company_client_uid)
            return profile.client
        except Exception:
            return None

    def get_marketer_profile(self, marketer) -> 'CompanyMarketerProfile':
        """
        Get the CompanyMarketerProfile for a marketer in this company.
        """
        try:
            return self.marketer_profiles.get(marketer=marketer)
        except Exception:
            return None

    def get_client_profile(self, client) -> 'CompanyClientProfile':
        """
        Get the CompanyClientProfile for a client in this company.
        """
        try:
            return self.client_profiles.get(client=client)
        except Exception:
            return None

    def _company_prefix(self) -> str:
        """Return a short prefix for the company name suitable for UIDs.

        Example: 'Lamba Property Limited' -> 'LPL'
        """
        try:
            if not self.company_name:
                return 'CMP'
            words = re.findall(r"[A-Za-z0-9]+", self.company_name.upper())
            if not words:
                return 'CMP'
            # Take first letter of up to three words
            prefix = ''.join(w[0] for w in words[:3])
            # If prefix too short, pad with company id
            if len(prefix) < 2:
                prefix = f"CMP{self.id}"
            return prefix
        except Exception:
            return 'CMP'

    def sync_plan_limits(self):
        """Synchronize company limits based on subscription tier and plan"""
        try:
            plan = SubscriptionPlan.objects.get(tier=self.subscription_tier)
            self.max_plots = plan.max_plots
            self.max_agents = plan.max_agents
            self.max_api_calls_daily = plan.max_api_calls_daily
        except SubscriptionPlan.DoesNotExist:
            # Default limits if plan doesn't exist
            tier_limits = {
                'starter': {'max_plots': 2, 'max_agents': 1, 'max_api_calls_daily': 1000},
                'professional': {'max_plots': 5, 'max_agents': 10, 'max_api_calls_daily': 10000},
                'enterprise': {'max_plots': 999999, 'max_agents': 999999, 'max_api_calls_daily': 999999},
            }
            limits = tier_limits.get(self.subscription_tier, tier_limits['starter'])
            self.max_plots = limits['max_plots']
            self.max_agents = limits['max_agents']
            self.max_api_calls_daily = limits['max_api_calls_daily']


class CompanySequence(models.Model):
    """Per-company sequence counters for named keys (client, marketer, etc.).

    This model stores the last_value used for a particular company/key pair.
    Use `get_next` to acquire the next integer in a transactionally-safe way
    using SELECT ... FOR UPDATE via Django's `select_for_update`.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='sequences')
    key = models.CharField(max_length=50, help_text="Sequence key, e.g. 'client' or 'marketer'")
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (('company', 'key'),)
        indexes = [models.Index(fields=['company', 'key'])]

    def __str__(self):
        return f"{self.company.company_name}::{self.key} = {self.last_value}"

    @classmethod
    def get_next(cls, company, key) -> int:
        """Return the next integer for (company, key) in an atomic, race-safe manner.

        Example usage:
            next_id = CompanySequence.get_next(company, 'client')
        """
        with transaction.atomic():
            obj, created = cls.objects.select_for_update().get_or_create(company=company, key=key, defaults={'last_value': 0})
            obj.last_value = (obj.last_value or 0) + 1
            obj.save(update_fields=['last_value'])
            return obj.last_value


class AppMetrics(models.Model):
    """Simple per-company mobile app metrics."""
    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='app_metrics')
    android_downloads = models.PositiveIntegerField(default=0)
    ios_downloads = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'App Metrics'
        verbose_name_plural = 'App Metrics'

    def __str__(self):
        return f"App Metrics · {self.company.company_name}"

    @property
    def total_downloads(self) -> int:
        return int((self.android_downloads or 0) + (self.ios_downloads or 0))


class CompanyCeo(models.Model):
    """Holds CEO records for a company. Supports multiple CEOs with one primary."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ceos')
    name = models.CharField(max_length=255, verbose_name="CEO Name")
    dob = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    is_primary = models.BooleanField(default=False, verbose_name="Is Primary CEO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company CEO"
        verbose_name_plural = "Company CEOs"
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.name} ({'Primary' if self.is_primary else 'Secondary'}) - {self.company.company_name}"


class SubscriptionPlan(models.Model):
    """Subscription plans for SaaS tier pricing"""
    TIER_CHOICES = [
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        unique=True,
        verbose_name="Subscription Tier"
    )
    name = models.CharField(max_length=100, verbose_name="Plan Name")
    description = models.TextField(blank=True, help_text="Marketing description for this plan", verbose_name="Plan Description")
    
    # Pricing
    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price in Nigerian Naira",
        verbose_name="Monthly Price (₦)"
    )
    annual_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional annual billing price with discount",
        verbose_name="Annual Price (₦)"
    )
    
    # Limits
    max_plots = models.IntegerField(default=50, help_text="Maximum number of property listings", verbose_name="Maximum Plots")
    max_agents = models.IntegerField(default=1, help_text="Maximum number of team members", verbose_name="Maximum Agents")
    max_api_calls_daily = models.IntegerField(default=1000, help_text="Maximum API calls per 24 hours", verbose_name="Daily API Calls")
    
    # Features JSON (e.g., {"advanced_analytics": true, "api_access": true})
    features = models.JSONField(
        blank=True,
        default=dict,
        help_text="JSON object of feature names and descriptions",
        verbose_name="Plan Features"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Can companies subscribe to this plan?", verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
        ordering = ['tier']
    
    def __str__(self):
        return f"{self.name} - ₦{self.monthly_price}/month"


class CompanyMarketerProfile(models.Model):
    """
    Stores company-specific ID and UID for each marketer in each company.
    This allows marketers to have unique sequential IDs per company.
    """
    marketer = models.ForeignKey(
        'MarketerUser',
        on_delete=models.CASCADE,
        related_name='company_profiles',
        verbose_name="Marketer"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='marketer_profiles',
        verbose_name="Company"
    )
    company_marketer_id = models.PositiveIntegerField(
        db_index=True,
        verbose_name="Company-Specific Marketer ID"
    )
    company_marketer_uid = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Company-Specific Marketer UID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('marketer', 'company'),)
        indexes = [models.Index(fields=['company', 'company_marketer_id']),
                   models.Index(fields=['marketer', 'company'])]
        verbose_name = "Company Marketer Profile"
        verbose_name_plural = "Company Marketer Profiles"

    def __str__(self):
        return f"{self.marketer.full_name} ({self.company_marketer_uid}) @ {self.company.company_name}"


class CompanyClientProfile(models.Model):
    """
    Stores company-specific ID and UID for each client in each company.
    This allows clients to have unique sequential IDs per company.
    """
    client = models.ForeignKey(
        'ClientUser',
        on_delete=models.CASCADE,
        related_name='company_profiles',
        verbose_name="Client"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='client_profiles',
        verbose_name="Company"
    )
    company_client_id = models.PositiveIntegerField(
        db_index=True,
        verbose_name="Company-Specific Client ID"
    )
    company_client_uid = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Company-Specific Client UID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('client', 'company'),)
        indexes = [models.Index(fields=['company', 'company_client_id']),
                   models.Index(fields=['client', 'company'])]
        verbose_name = "Company Client Profile"
        verbose_name_plural = "Company Client Profiles"

    def __str__(self):
        return f"{self.client.full_name} ({self.company_client_uid}) @ {self.company.company_name}"


class MarketerAffiliation(models.Model):
    """
    Allows marketers to affiliate with multiple companies
    and earn commissions on property sales
    """
    COMMISSION_TIERS = [
        ('bronze', 'Bronze - 2%'),
        ('silver', 'Silver - 3.5%'),
        ('gold', 'Gold - 5%'),
        ('platinum', 'Platinum - 7%+'),
    ]
    
    AFFILIATION_STATUS = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]
    
    # Core relationship
    marketer = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='company_affiliations',
        limit_choices_to={'role': 'marketer'},
        verbose_name="Marketer"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='marketer_affiliations',
        verbose_name="Company"
    )
    
    # Commission configuration
    commission_tier = models.CharField(
        max_length=20,
        choices=COMMISSION_TIERS,
        default='bronze',
        verbose_name="Commission Tier"
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        verbose_name="Commission Rate (%)"
    )
    
    # Performance tracking
    properties_sold = models.PositiveIntegerField(default=0, verbose_name="Properties Sold")
    total_commissions_earned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Total Commissions Earned"
    )
    total_commissions_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Total Commissions Paid"
    )
    total_sales_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Total Sales Value"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=AFFILIATION_STATUS,
        default='active',
        verbose_name="Status"
    )
    
    # Dates
    date_affiliated = models.DateTimeField(auto_now_add=True, verbose_name="Date Affiliated")
    approval_date = models.DateTimeField(null=True, blank=True, verbose_name="Approval Date")
    suspension_date = models.DateTimeField(null=True, blank=True, verbose_name="Suspension Date")
    termination_date = models.DateTimeField(null=True, blank=True, verbose_name="Termination Date")
    
    # Bank details for payouts
    bank_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Bank Name")
    account_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="Account Number")
    account_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Account Name")
    
    class Meta:
        unique_together = ['marketer', 'company']
        verbose_name = "Marketer Affiliation"
        verbose_name_plural = "Marketer Affiliations"
        ordering = ['-date_affiliated']
        indexes = [
            models.Index(fields=['marketer', 'status']),
            models.Index(fields=['company', 'status']),
        ]
    
    def __str__(self):
        return f"{self.marketer.full_name} - {self.company.company_name} ({self.get_status_display()})"
    
    def clean(self):
        """SECURITY: Validate that marketer has role='marketer' to prevent data leakage"""
        from django.core.exceptions import ValidationError
        
        if self.marketer and getattr(self.marketer, 'role', None) != 'marketer':
            raise ValidationError({
                'marketer': f"User must have role='marketer'. Got role='{getattr(self.marketer, 'role', None)}'"
            })
    
    def save(self, *args, **kwargs):
        """Run validation before saving"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_pending_commissions(self):
        """Get total commissions that haven't been paid yet"""
        return self.total_commissions_earned - self.total_commissions_paid


class MarketerEarnedCommission(models.Model):
    """
    Tracks individual commissions earned by marketers
    on specific property sales (SaaS model for affiliate tracking)
    """
    COMMISSION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('disputed', 'Disputed'),
    ]
    
    # Relationships
    affiliation = models.ForeignKey(
        MarketerAffiliation,
        on_delete=models.CASCADE,
        related_name='earned_commissions',
        verbose_name="Affiliation"
    )
    plot_allocation = models.ForeignKey(
        'PlotAllocation',
        on_delete=models.SET_NULL,
        null=True,
        related_name='marketer_earned_commission',
        verbose_name="Plot Allocation"
    )
    
    # Commission details
    sale_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Sale Amount"
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Commission Rate (%)"
    )
    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Commission Amount"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=COMMISSION_STATUS,
        default='pending',
        verbose_name="Status"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Approved At")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Paid At")
    
    # Payment tracking
    payment_reference = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Payment Reference"
    )
    
    # Dispute resolution
    dispute_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="Dispute Reason"
    )
    disputed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Disputed At"
    )
    
    class Meta:
        verbose_name = "Marketer Earned Commission"
        verbose_name_plural = "Marketer Earned Commissions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['affiliation', 'status']),
            models.Index(fields=['status', 'paid_at']),
        ]
    
    def __str__(self):
        return f"₦{self.commission_amount} - {self.affiliation.marketer.full_name} ({self.get_status_display()})"
    
    def approve(self):
        """Approve pending commission"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.save()
    
    def mark_as_paid(self, payment_reference):
        """Mark commission as paid"""
        if self.status == 'approved':
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.payment_reference = payment_reference
            self.save()
            # Update affiliation totals
            self.affiliation.total_commissions_paid += self.commission_amount
            self.affiliation.save()


class ClientDashboard(models.Model):
    """
    Aggregates all properties owned by a client
    across multiple companies in one unified view
    """
    # Client relationship
    client = models.OneToOneField(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='dashboard',
        limit_choices_to={'role': 'client'},
        verbose_name="Client"
    )
    
    # Aggregated portfolio data
    total_properties_owned = models.PositiveIntegerField(
        default=0,
        verbose_name="Total Properties Owned"
    )
    total_invested = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Total Amount Invested"
    )
    portfolio_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Current Portfolio Value"
    )
    
    # ROI and growth metrics
    roi_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="ROI Percentage"
    )
    month_over_month_growth = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="Month Over Month Growth (%)"
    )
    
    # Projections
    projected_value_1yr = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Projected Value in 1 Year"
    )
    projected_value_5yr = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Projected Value in 5 Years"
    )
    
    # Preferences
    preferred_currency = models.CharField(
        max_length=3,
        default='NGN',
        verbose_name="Preferred Currency"
    )
    notification_preferences = models.JSONField(
        default=dict,
        verbose_name="Notification Preferences"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    class Meta:
        verbose_name = "Client Dashboard"
        verbose_name_plural = "Client Dashboards"
    
    def __str__(self):
        return f"{self.client.full_name}'s Portfolio Dashboard"
    
    def refresh_portfolio_data(self):
        """
        Recalculate all portfolio metrics from scratch
        Call this after property purchases or allocation updates
        """
        from django.db.models import Sum
        
        # Get all allocations for this client across all companies
        allocations = PlotAllocation.objects.filter(client=self.client)
        
        # Calculate totals
        self.total_properties_owned = allocations.count()
        self.total_invested = allocations.aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        # Portfolio value (assuming 10% annual appreciation)
        self.portfolio_value = self.total_invested * Decimal('1.10')
        self.roi_percentage = ((self.portfolio_value - self.total_invested) / self.total_invested * 100) if self.total_invested > 0 else 0
        
        self.save()


class ClientPropertyView(models.Model):
    """
    Tracks which properties from different companies
    a client is interested in viewing
    """
    # Relationship
    client = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='property_views',
        limit_choices_to={'role': 'client'},
        verbose_name="Client"
    )
    plot = models.ForeignKey(
        'EstatePlot',
        on_delete=models.CASCADE,
        related_name='client_views',
        verbose_name="Plot"
    )
    
    # Tracking
    view_count = models.PositiveIntegerField(default=1, verbose_name="View Count")
    first_viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="First Viewed At")
    last_viewed_at = models.DateTimeField(auto_now=True, verbose_name="Last Viewed At")
    
    # Interest level
    is_interested = models.BooleanField(default=False, verbose_name="Is Interested")
    is_favorited = models.BooleanField(default=False, verbose_name="Is Favorited")
    
    # Notes
    client_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Client Notes"
    )
    
    class Meta:
        unique_together = ['client', 'plot']
        verbose_name = "Client Property View"
        verbose_name_plural = "Client Property Views"
        ordering = ['-last_viewed_at']
    
    def __str__(self):
        return f"{self.client.full_name} viewed {self.plot} ({self.view_count} times)"


class CustomUserManager(BaseUserManager):
    def create_user(self, email, full_name, phone, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, phone=phone, **extra_fields)
        user.set_password(password)  # Set the password hash
        user.save(using=self._db)
        return user
    
    
    def create_superuser(self, email, full_name, phone, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # extra_fields.setdefault('role', None)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, full_name, phone, password, **extra_fields)

    def create_admin(self, email, full_name, phone, password=None, **extra_fields):
        """Create and return an admin user."""
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        # extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, full_name, phone, password, **extra_fields)
    
    # def create_support(self, email, full_name, phone, password=None, **extra_fields):
    #     """
    #     Support users: have messaging/admin-like access, but NOT full superuser privileges.
    #     We set is_staff=True so they can access admin if desired, but is_superuser=False.
    #     Assign role='support'.
    #     """
    #     extra_fields.setdefault('role', 'support')
    #     extra_fields.setdefault('is_staff', True)
    #     extra_fields.setdefault('is_superuser', False)
    #     return self._create_user(email, full_name, phone, password, **extra_fields)

    def create_support(self, email, full_name, phone, password=None, **extra_fields):
        extra_fields.setdefault('role', 'support')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', False)
        return self.create_user(email=email, full_name=full_name, phone=phone, password=password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('client', 'Client'),
        ('marketer', 'Marketer'),
        ('support', 'Support'),
    ]
    
    ADMIN_LEVEL_CHOICES = [
        ('system', 'System Administrator'),  # Platform-level super admin
        ('company', 'Company Administrator'),  # Company-level admin
        ('none', 'No Admin Access'),  # Regular user
    ]

    username = None 
    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    address = models.TextField(blank=True, null=True, verbose_name="Residential Address")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Role", blank=True, null=True)
    company_profile = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name="users", verbose_name="Company")
    
    # Tenant Admin fields (for superAdmin access control)
    is_system_admin = models.BooleanField(
        default=False, 
        verbose_name="Is System Administrator",
        help_text="System admins can manage the entire platform across all companies"
    )
    admin_level = models.CharField(
        max_length=20,
        choices=ADMIN_LEVEL_CHOICES,
        default='none',
        verbose_name="Admin Level",
        help_text="Defines the administrative access level: system (platform-wide), company (single company), or none"
    )
    # marketer = models.ForeignKey(
    #     'self', 
    #     null=True, 
    #     blank=True, 
    #     on_delete=models.SET_NULL, 
    #     related_name="marketer_users", 
    #     verbose_name="Assigned Marketer"
    # )
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    date_registered = models.DateTimeField(default=timezone.now, verbose_name="Date Registered")
    email = models.EmailField(verbose_name="Email Address")


    # profile fields
    about = models.TextField(blank=True, null=True, verbose_name="About")
    company = models.CharField(max_length=255, blank=True, null=True, verbose_name="Company")
    job = models.CharField(max_length=255, blank=True, null=True, verbose_name="Job")
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Country of Residence")
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    # Last login metadata
    last_login_ip = models.CharField(max_length=45, blank=True, null=True, verbose_name="Last Login IP")
    last_login_location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Last Login Location")

    # Full control permission (allows bypassing master admin password for company profile)
    has_full_control = models.BooleanField(
        default=False, 
        verbose_name="Has Full Control",
        help_text="When enabled, this admin can access company profile without master admin password verification"
    )

    # Soft delete fields
    is_deleted = models.BooleanField(default=False, verbose_name="Is Deleted")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")
    deletion_reason = models.TextField(blank=True, null=True, verbose_name="Deletion Reason")

    # Django Auth customization
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    objects = CustomUserManager()

    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        """
        Ensure the inherited first_name and last_name fields are populated
        from full_name so the DB NOT NULL constraint doesn't fail.
        """
        # Only run full validation for new instances or when explicitly saving all fields
        # Skip validation for partial updates (like update_last_login)
        update_fields = kwargs.get('update_fields')
        # Skip full_clean() to prevent validation errors on password field during initial user creation
        # Password will be set via set_password() immediately after creation
        # if (update_fields is None or not update_fields):
        #     # Ensure validation runs during full saves
        #     self.full_clean()
        
        # Only populate if full_name is present:
        if self.full_name:
            parts = self.full_name.strip().split()
            # set actual model fields (these exist on AbstractUser)
            # Avoid overwriting if first_name/last_name intentionally set
            if not self.first_name:
                self.first_name = parts[0]
            if not self.last_name:
                self.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        # If full_name missing and first_name empty, set safe default to avoid NULL insertion:
        if not self.first_name:
            self.first_name = self.full_name or (self.email.split('@')[0] if self.email else '')
        if not self.last_name:
            self.last_name = self.last_name or ""
        super().save(*args, **kwargs)

    def clean(self):
        # Ensure company is set for admin/support roles
        if self.role in ['admin', 'support'] and not self.company_profile:
            raise ValidationError("Company is required for admin/support roles.")
        
        # Check for duplicate accounts within the same role
        # Allow same email across different roles, but prevent duplicates within same role
        existing_users = CustomUser.objects.filter(
            email=self.email,
            role=self.role
        ).exclude(pk=self.pk)
        
        if self.role in ['admin', 'support']:
            # For admin/support roles, also check company uniqueness
            existing_users = existing_users.filter(company_profile=self.company_profile)
            if existing_users.exists():
                raise ValidationError(f"Cannot create multiple {self.role} accounts with the same email in the same company.")
        else:
            # For client/marketer roles, check global uniqueness per role
            if existing_users.exists():
                raise ValidationError(f"Cannot create multiple {self.role} accounts with the same email.")

class AdminUser(CustomUser):
    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"

    def save(self, *args, **kwargs):
        self.role = 'admin'
        self.is_superuser = True
        self.is_staff = True
        super().save(*args, **kwargs)

class SupportUser(CustomUser):
    class Meta:
        verbose_name = "Support User"
        verbose_name_plural = "Support Users"

    def save(self, *args, **kwargs):
        self.role = 'support'
        self.is_staff = True
        self.is_superuser = False
        super().save(*args, **kwargs)

class MarketerUser(CustomUser):
    # Per-company sequential identifier for marketers (assigned on save if missing)
    company_marketer_id = models.PositiveIntegerField(null=True, blank=True, db_index=True, verbose_name="Company Marketer ID")
    # Human-friendly unique UID including company prefix, e.g. LPLMKT001
    company_marketer_uid = models.CharField(max_length=64, null=True, blank=True, unique=True, db_index=True, verbose_name="Company Marketer UID")

    class Meta:
        verbose_name = "Marketer User"
        verbose_name_plural = "Marketer Users"

    def save(self, *args, **kwargs):
        # Ensure role is set
        self.role = 'marketer'

        # For backward compatibility, auto-assign a per-company sequential marketer id when missing
        try:
            if self.company_profile and not getattr(self, 'company_marketer_id', None):
                # Prefer sequence-based allocation for race-safety
                try:
                    self.company_marketer_id = CompanySequence.get_next(self.company_profile, 'marketer')
                except Exception:
                    from django.db.models import Max
                    maxv = MarketerUser.objects.filter(company_profile=self.company_profile).aggregate(maxv=Max('company_marketer_id'))
                    cur = maxv.get('maxv') or 0
                    self.company_marketer_id = int(cur) + 1
        except Exception:
            # Non-fatal; proceed without assignment if aggregation fails
            pass

        # Auto-generate a unique company-prefixed UID (e.g. LPL-MKT001)
        try:
            if self.company_profile and getattr(self, 'company_marketer_id', None) and not getattr(self, 'company_marketer_uid', None):
                # Use the company to compute a stable prefix (avoid calling a user method)
                try:
                    prefix = self.company_profile._company_prefix()
                except Exception:
                    prefix = (self.company_profile.company_name or 'CMP')[:3].upper()

                # Format: PREFIX-ROLECODE###  e.g., LPLMKT001
                base_uid = f"{prefix}MKT{int(self.company_marketer_id):03d}"
                # Ensure uniqueness; if collision, include company id to disambiguate
                if MarketerUser.objects.filter(company_marketer_uid=base_uid).exclude(pk=self.pk).exists():
                    base_uid = f"{prefix}{self.company_profile.id}MKT{int(self.company_marketer_id):03d}"
                self.company_marketer_uid = base_uid
        except Exception:
            pass

        super().save(*args, **kwargs)

        # Create or update CompanyMarketerProfile for the primary company
        if self.company_profile:
            try:
                profile, created = CompanyMarketerProfile.objects.get_or_create(
                    marketer=self,
                    company=self.company_profile,
                    defaults={
                        'company_marketer_id': self.company_marketer_id or 1,
                        'company_marketer_uid': self.company_marketer_uid or f"{(self.company_profile.company_name or 'CMP')[:3].upper()}MKT001"
                    }
                )
                if not created and (self.company_marketer_id or self.company_marketer_uid):
                    # Update profile if these fields changed
                    profile.company_marketer_id = self.company_marketer_id
                    profile.company_marketer_uid = self.company_marketer_uid
                    profile.save(update_fields=['company_marketer_id', 'company_marketer_uid', 'updated_at'])
            except Exception:
                pass


class ClientUser(CustomUser):
    assigned_marketer = models.ForeignKey(
        MarketerUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients",
        verbose_name="Assigned Marketer"
    )
    # Per-company sequential identifier for clients (assigned on save if missing)
    company_client_id = models.PositiveIntegerField(null=True, blank=True, db_index=True, verbose_name="Company Client ID")
    # Human-friendly unique UID including company prefix, e.g. LPLCLT001
    company_client_uid = models.CharField(max_length=64, null=True, blank=True, unique=True, db_index=True, verbose_name="Company Client UID")
    class Meta:
        verbose_name = "Client User"
        verbose_name_plural = "Client Users"

    def save(self, *args, **kwargs):
        if not self.is_superuser:
            self.role = 'client'

        # Auto-assign a per-company sequential client id when missing
        try:
            if self.company_profile and not getattr(self, 'company_client_id', None):
                try:
                    self.company_client_id = CompanySequence.get_next(self.company_profile, 'client')
                except Exception:
                    from django.db.models import Max
                    maxv = ClientUser.objects.filter(company_profile=self.company_profile).aggregate(maxv=Max('company_client_id'))
                    cur = maxv.get('maxv') or 0
                    self.company_client_id = int(cur) + 1
        except Exception:
            # Non-fatal - continue without assignment
            pass
        # Auto-generate a unique company-prefixed UID (e.g. LPLCLT001)
        try:
            if self.company_profile and getattr(self, 'company_client_id', None) and not getattr(self, 'company_client_uid', None):
                try:
                    prefix = self.company_profile._company_prefix()
                except Exception:
                    prefix = (self.company_profile.company_name or 'CMP')[:3].upper()

                # Format: PREFIX-ROLECODE###  e.g., LPLCLT001
                base_uid = f"{prefix}CLT{int(self.company_client_id):03d}"
                if ClientUser.objects.filter(company_client_uid=base_uid).exclude(pk=self.pk).exists():
                    base_uid = f"{prefix}{self.company_profile.id}CLT{int(self.company_client_id):03d}"
                self.company_client_uid = base_uid
        except Exception:
            pass
        super().save(*args, **kwargs)

        # Create or update CompanyClientProfile for the primary company
        if self.company_profile:
            try:
                profile, created = CompanyClientProfile.objects.get_or_create(
                    client=self,
                    company=self.company_profile,
                    defaults={
                        'company_client_id': self.company_client_id or 1,
                        'company_client_uid': self.company_client_uid or f"{(self.company_profile.company_name or 'CMP')[:3].upper()}CLT001"
                    }
                )
                if not created and (self.company_client_id or self.company_client_uid):
                    # Update profile if these fields changed
                    profile.company_client_id = self.company_client_id
                    profile.company_client_uid = self.company_client_uid
                    profile.save(update_fields=['company_client_id', 'company_client_uid', 'updated_at'])
            except Exception:
                pass

    def _fully_paid_transactions_qs(self):
        """
        Return a queryset of this client's transactions that are fully settled:
        - Full payment allocations are always treated as fully paid
        - Part payments included only when sum(payment_records.amount_paid) >= total_amount
        Computed at the DB level to ensure accuracy.
        """
        try:
            return (
                self.transactions
                .annotate(
                    total_paid_sum=Coalesce(
                        Sum('payment_records__amount_paid'),
                        Decimal('0'),
                        output_field=DecimalField(max_digits=18, decimal_places=2)
                    )
                )
                .filter(
                    Q(allocation__payment_type='full') |
                    Q(total_paid_sum__gte=F('total_amount'))
                )
                .select_related('allocation')
            )
        except Exception:
            # Fallback: evaluate in Python if annotation fails for any reason
            txs = list(self.transactions.select_related('allocation').prefetch_related('payment_records'))
            fully_paid = []
            for t in txs:
                if getattr(t.allocation, 'payment_type', None) == 'full':
                    fully_paid.append(t)
                else:
                    total_paid = sum((pr.amount_paid for pr in t.payment_records.all()), Decimal('0'))
                    if total_paid >= (t.total_amount or Decimal('0')):
                        fully_paid.append(t)
            return fully_paid

    def get_assigned_marketer(self, company=None):
        """
        Return the assigned marketer for this client.

        If `company` is provided, prefer a company-specific assignment
        (via ClientMarketerAssignment). Otherwise fall back to the
        legacy `assigned_marketer` field.
        """
        try:
            if company is not None:
                assign = ClientMarketerAssignment.objects.filter(
                    client=self,
                    company=company
                ).select_related('marketer').first()
                if assign:
                    return assign.marketer
        except Exception:
            pass

        return getattr(self, 'assigned_marketer', None)


class ClientMarketerAssignment(models.Model):
    """Assign a marketer to a client for a specific company.

    This allows a client to have different assigned marketers per company
    (useful when a client has purchases across multiple companies).
    """
    client = models.ForeignKey(ClientUser, on_delete=models.CASCADE, related_name='marketer_assignments')
    marketer = models.ForeignKey(MarketerUser, on_delete=models.CASCADE, related_name='client_assignments')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='client_marketer_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('client', 'marketer', 'company')
        indexes = [models.Index(fields=['client', 'company'])]

    def __str__(self):
        return f"{self.client} → {self.marketer} @ {self.company}"

    def clean(self):
        """SECURITY: Validate role integrity to prevent data leakage"""
        from django.core.exceptions import ValidationError
        
        # Ensure client has role='client'
        if self.client and getattr(self.client, 'role', None) != 'client':
            raise ValidationError({
                'client': f"User must have role='client'. Got role='{getattr(self.client, 'role', None)}'"
            })
        
        # Ensure marketer has role='marketer'
        if self.marketer and getattr(self.marketer, 'role', None) != 'marketer':
            raise ValidationError({
                'marketer': f"User must have role='marketer'. Got role='{getattr(self.marketer, 'role', None)}'"
            })
    
    def save(self, *args, **kwargs):
        """Run validation before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def plot_count(self) -> int:
        """Count of fully settled plots for this client.
        Includes only transactions that are fully paid (see _fully_paid_transactions_qs).
        """
        paid_qs = self._fully_paid_transactions_qs()
        try:
            # Distinct allocations in case of any anomalies
            return paid_qs.values('allocation_id').distinct().count()
        except AttributeError:
            # Fallback when paid_qs is a list
            return len({getattr(t, 'allocation_id', getattr(t.allocation, 'id', None)) for t in paid_qs})

    @property
    def total_value(self):
        """Sum of total_amount from fully settled transactions only (Decimal)."""
        paid_qs = self._fully_paid_transactions_qs()
        try:
            agg = paid_qs.aggregate(
                tv=Coalesce(
                    Sum('total_amount'),
                    Decimal('0'),
                    output_field=DecimalField(max_digits=18, decimal_places=2)
                )
            )
            return agg.get('tv') or Decimal('0')
        except AttributeError:
            # Fallback when paid_qs is a list
            total = Decimal('0')
            for t in paid_qs:
                try:
                    total += t.total_amount or Decimal('0')
                except Exception:
                    continue
            return total

    @property
    def rank_tag(self) -> str:
        """Rank tag derived from total_value and plot_count thresholds.
        Rules:
        - Royal Elite: total_value ≥ 150,000,000 AND plot_count ≥ 5
        - Estate Ambassador: total_value ≥ 100,000,000 OR plot_count ≥ 4
        - Prime Investor: total_value ≥ 50,000,000 OR plot_count ≥ 3
        - Smart Owner: total_value ≥ 20,000,000 OR plot_count ≥ 2
        - First-Time Investor: else
        """
        tv = self.total_value
        pc = self.plot_count
        try:
            tv_num = Decimal(tv)
        except Exception:
            tv_num = Decimal('0')

        if tv_num >= Decimal('150000000') and pc >= 5:
            return 'Royal Elite'
        if tv_num >= Decimal('100000000') or pc >= 4:
            return 'Estate Ambassador'
        if tv_num >= Decimal('50000000') or pc >= 3:
            return 'Prime Investor'
        if tv_num >= Decimal('20000000') or pc >= 2:
            return 'Smart Owner'
        return 'First-Time Investor'

    @classmethod
    def with_investment_metrics(cls, qs=None):
        """Simple annotations for totals across all transactions/allocations.
        Note: This does NOT reflect 'fully-paid-only' logic used for rank. Prefer
        using the properties (which compute from fully settled transactions) or
        prefetch helpers below when correctness is required for rankings.
        """
        if qs is None:
            qs = cls.objects.all()
        return qs.annotate(
            total_value_annotated=Coalesce(
                Sum('transactions__total_amount'),
                Decimal('0'),
                output_field=DecimalField(max_digits=18, decimal_places=2)
            ),
            plot_count_annotated=Coalesce(
                Count('plotallocation', distinct=True),
                0,
                output_field=IntegerField()
            ),
        )

    @classmethod
    def with_fully_paid_prefetch(cls, qs=None):
        """Prefetch transactions and payment_records to make fully-paid computations
        efficient in templates without relying on coarse annotations."""
        if qs is None:
            qs = cls.objects.all()
        return qs.prefetch_related(
            models.Prefetch(
                'transactions',
                queryset=(Transaction.objects
                          .select_related('allocation')
                          .prefetch_related('payment_records'))
            )
        )


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('complaint', 'Complaint'),
        ('enquiry', 'Enquiry'),
        ('compliment', 'Compliment'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Sender"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="received_messages",
        verbose_name="Recipient"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        verbose_name="Message Type"
    )
    content = models.TextField(verbose_name="Message Content")
    file = models.FileField(
        upload_to="chat_files/",
        null=True,
        blank=True,
        verbose_name="Attachment"
    )
    date_sent = models.DateTimeField(auto_now_add=True, verbose_name="Date Sent")
    is_read = models.BooleanField(default=False, verbose_name="Is Read")
    # New field: reference for reply functionality
    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',
        verbose_name="Reply To"
    )
    # New field: track the delivery/read status
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name="Message Status"
    )
    deleted_for_everyone = models.BooleanField(
        default=False,
        verbose_name="Deleted For Everyone"
    )
    deleted_for_everyone_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Deleted For Everyone At"
    )
    deleted_for_everyone_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='messages_deleted_globally',
        verbose_name="Deleted For Everyone By"
    )
    # Company scope for the message — enforces company-scoped chats
    company = models.ForeignKey(
        'Company',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='messages',
        verbose_name='Company'
    )
    # Encryption fields for end-to-end encryption
    is_encrypted = models.BooleanField(default=False, verbose_name="Is Encrypted")
    
    class Meta:
        ordering = ['date_sent']
    
    def __str__(self):
        return f"Message from {self.sender} to {self.recipient or 'Admin'} on {self.date_sent}"

    def is_deleted_for_user(self, user):
        """Return True if message was deleted-for-everyone and user isn't the sender."""
        if not self.deleted_for_everyone:
            return False
        if not user:
            return True
        return user != self.sender

    def get_content(self):
        """Get decrypted content for display"""
        from estateApp.encryption_utils import decrypt_message_content
        return decrypt_message_content(self)


# Import signals at the end to avoid circular imports
from django.db.models.signals import pre_save
from django.dispatch import receiver
from estateApp.encryption_utils import encrypt_message_signal

@receiver(pre_save, sender=Message)
def encrypt_message_before_save(sender, instance, **kwargs):
    """Automatically encrypt message content before saving"""
    encrypt_message_signal(sender, instance, **kwargs)


class ChatAssignment(models.Model):
    """
    Assigns chat conversations to specific admin users for better tracking and accountability.
    Ensures every chat gets proper attention and response.
    """
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_assignments',
        verbose_name="Client"
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='chat_assignments',
        verbose_name="Company"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_chats',
        verbose_name="Assigned Admin"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Assigned At")
    last_message_at = models.DateTimeField(auto_now=True, verbose_name="Last Message At")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        default='medium',
        verbose_name="Priority"
    )
    response_time_target = models.DurationField(
        default=timedelta(hours=24),
        verbose_name="Response Time Target"
    )
    first_response_time = models.DurationField(
        null=True,
        blank=True,
        verbose_name="First Response Time"
    )
    last_response_time = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Last Response Time"
    )
    
    class Meta:
        unique_together = ['client', 'company']
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"{self.client} - {self.company} assigned to {self.assigned_to}"
    
    def calculate_response_times(self):
        """Calculate and update response times for performance tracking."""
        # Get first message from client
        first_client_msg = Message.objects.filter(
            sender=self.client,
            company=self.company,
            date_sent__gte=self.assigned_at
        ).order_by('date_sent').first()
        
        # Get first response from assigned admin
        first_admin_response = Message.objects.filter(
            sender=self.assigned_to,
            company=self.company,
            date_sent__gte=first_client_msg.date_sent if first_client_msg else self.assigned_at
        ).order_by('date_sent').first()
        
        if first_client_msg and first_admin_response:
            self.first_response_time = first_admin_response.date_sent - first_client_msg.date_sent
        
        # Get last message from client
        last_client_msg = Message.objects.filter(
            sender=self.client,
            company=self.company,
            date_sent__gte=self.assigned_at
        ).order_by('-date_sent').first()
        
        # Get last response from assigned admin
        last_admin_response = Message.objects.filter(
            sender=self.assigned_to,
            company=self.company,
            date_sent__gte=last_client_msg.date_sent if last_client_msg else self.assigned_at
        ).order_by('-date_sent').first()
        
        if last_client_msg and last_admin_response:
            self.last_response_time = last_admin_response.date_sent - last_client_msg.date_sent
        
        self.save()


class ChatNotification(models.Model):
    """
    Manages chat notifications for admins to ensure no messages are missed.
    Tracks unread counts and sends alerts for urgent conversations.
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_notifications',
        verbose_name="Recipient"
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='chat_notifications',
        verbose_name="Company"
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_notifications',
        verbose_name="Client"
    )
    unread_count = models.PositiveIntegerField(default=0, verbose_name="Unread Count")
    last_message = models.ForeignKey(
        'Message',
        on_delete=models.CASCADE,
        related_name='notification_for',
        verbose_name="Last Message"
    )
    last_message_at = models.DateTimeField(auto_now=True, verbose_name="Last Message At")
    is_urgent = models.BooleanField(default=False, verbose_name="Is Urgent")
    notified_at = models.DateTimeField(null=True, blank=True, verbose_name="Notified At")
    dismissed_at = models.DateTimeField(null=True, blank=True, verbose_name="Dismissed At")
    
    class Meta:
        unique_together = ['recipient', 'company', 'client']
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"{self.recipient} - {self.company} - {self.unread_count} unread"
    
    def mark_as_read(self):
        """Mark all messages as read and update notification."""
        Message.objects.filter(
            sender=self.client,
            recipient=self.recipient,
            company=self.company,
            is_read=False
        ).update(is_read=True, status='read')
        
        self.unread_count = 0
        self.dismissed_at = timezone.now()
        self.save()
    
    def increment_unread(self):
        """Increment unread count when new message arrives."""
        self.unread_count += 1
        self.save()


class ChatSLA(models.Model):
    """
    Defines Service Level Agreements for chat responses.
    Tracks response times and compliance for each company.
    """
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='chat_slas',
        verbose_name="Company"
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        verbose_name="Priority"
    )
    response_time_hours = models.PositiveIntegerField(verbose_name="Response Time (Hours)")
    resolution_time_hours = models.PositiveIntegerField(verbose_name="Resolution Time (Hours)")
    working_hours_start = models.TimeField(default=time(9, 0), verbose_name="Working Hours Start")
    working_hours_end = models.TimeField(default=time(17, 0), verbose_name="Working Hours End")
    include_weekends = models.BooleanField(default=False, verbose_name="Include Weekends")
    
    class Meta:
        unique_together = ['company', 'priority']
    
    def __str__(self):
        return f"{self.company} - {self.priority} - {self.response_time_hours}h response"


class ChatQueue(models.Model):
    """
    Manages incoming chat queues to ensure proper response management.
    Prevents duplicate entries and tracks chat status across the system.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_queues',
        verbose_name="Client"
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='chat_queues',
        verbose_name="Company"
    )
    first_message = models.ForeignKey(
        'Message',
        on_delete=models.CASCADE,
        related_name='queue_entries',
        verbose_name="First Message"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="Priority"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Resolved At")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    objects = CompanyAwareManager()
    
    class Meta:
        verbose_name = "Chat Queue"
        verbose_name_plural = "Chat Queues"
        ordering = ['-created_at']
        unique_together = [['client', 'company']]
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['client', 'company']),
        ]
    
    def __str__(self):
        return f"{self.client} - {self.company} - {self.status}"
    
    def save(self, *args, **kwargs):
        """Ensure proper queue management."""
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def mark_as_resolved(self):
        """Mark the chat queue as resolved."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()
    
    def update_priority(self, priority):
        """Update the priority of the chat queue."""
        self.priority = priority
        self.save()


class ChatAssignment(models.Model):
    """
    Tracks chat assignments to ensure proper response management.
    Monitors SLA compliance and response times for each company.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
        ('closed', 'Closed')
    ]
    
    SLA_STATUS_CHOICES = [
        ('compliant', 'Compliant'),
        ('at_risk', 'At Risk'),
        ('breached', 'Breached'),
        ('resolved', 'Resolved')
    ]
    
    chat_queue = models.ForeignKey(
        'ChatQueue',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Chat Queue"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_assignments',
        verbose_name="Assigned To"
    )
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='chat_assignments',
        verbose_name="Company"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    sla_status = models.CharField(
        max_length=20,
        choices=SLA_STATUS_CHOICES,
        default='compliant',
        verbose_name="SLA Status"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Assigned At")
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Accepted At")
    first_response_at = models.DateTimeField(null=True, blank=True, verbose_name="First Response At")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Resolved At")
    response_time = models.DurationField(null=True, blank=True, verbose_name="Response Time")
    resolution_time = models.DurationField(null=True, blank=True, verbose_name="Resolution Time")
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        default='medium',
        verbose_name="Priority"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    is_urgent = models.BooleanField(default=False, verbose_name="Is Urgent")
    escalation_level = models.PositiveIntegerField(default=0, verbose_name="Escalation Level")
    
    objects = CompanyAwareManager()
    
    class Meta:
        verbose_name = "Chat Assignment"
        verbose_name_plural = "Chat Assignments"
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['chat_queue', 'assigned_to']),
            models.Index(fields=['status', 'assigned_at']),
            models.Index(fields=['sla_status', 'response_time']),
        ]
        unique_together = [['chat_queue', 'assigned_to']]
    
    def __str__(self):
        return f"{self.chat_queue} - Assigned to {self.assigned_to}"
    
    def save(self, *args, **kwargs):
        """Update SLA status based on response times."""
        if self.pk:
            old_assignment = ChatAssignment.objects.get(pk=self.pk)
            
            # Calculate response time if first response was made
            if self.first_response_at and not old_assignment.first_response_at:
                self.response_time = self.first_response_at - self.assigned_at
            
            # Calculate resolution time if resolved
            if self.resolved_at and not old_assignment.resolved_at:
                self.resolution_time = self.resolved_at - self.assigned_at
                self.status = 'resolved'
                self.sla_status = 'resolved'
        
        # Update SLA status based on timing
        self._update_sla_status()
        
        super().save(*args, **kwargs)
    
    def _update_sla_status(self):
        """Update SLA compliance status based on response times."""
        if self.status == 'resolved':
            self.sla_status = 'resolved'
            return
        
        if self.first_response_at:
            response_time = self.first_response_at - self.assigned_at
            sla = ChatSLA.objects.filter(
                company=self.company,
                priority=self.priority
            ).first()
            
            if sla:
                sla_hours = timedelta(hours=sla.response_time_hours)
                if response_time > sla_hours:
                    self.sla_status = 'breached'
                elif response_time > sla_hours * 0.8:
                    self.sla_status = 'at_risk'
                else:
                    self.sla_status = 'compliant'
    
    def accept_assignment(self, user):
        """Accept the chat assignment."""
        if self.assigned_to != user:
            raise ValidationError("You cannot accept this assignment.")
        
        self.status = 'in_progress'
        self.accepted_at = timezone.now()
        self.save()
    
    def resolve_assignment(self, user):
        """Resolve the chat assignment."""
        if self.assigned_to != user:
            raise ValidationError("You cannot resolve this assignment.")
        
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.sla_status = 'resolved'
        self.save()
    
    def escalate_assignment(self, user, notes=""):
        """Escalate the chat assignment."""
        if self.assigned_to != user:
            raise ValidationError("You cannot escalate this assignment.")
        
        self.status = 'escalated'
        self.escalation_level += 1
        self.notes = notes
        self.save()


class ChatResponseTracking(models.Model):
    """
    Tracks chat response metrics for management oversight.
    Provides insights into response times and SLA compliance.
    """
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='response_tracking',
        verbose_name="Company"
    )
    date = models.DateField(default=date.today, verbose_name="Date")
    total_chats = models.PositiveIntegerField(default=0, verbose_name="Total Chats")
    responded_chats = models.PositiveIntegerField(default=0, verbose_name="Responded Chats")
    average_response_time = models.DurationField(null=True, blank=True, verbose_name="Average Response Time")
    sla_compliance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="SLA Compliance Rate (%)"
    )
    breached_chats = models.PositiveIntegerField(default=0, verbose_name="Breached Chats")
    
    class Meta:
        unique_together = ['company', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.company} - {self.date} - {self.total_chats} chats"
    
    def update_metrics(self):
        """Update response tracking metrics for the day."""
        today_assignments = ChatAssignment.objects.filter(
            company=self.company,
            assigned_at__date=self.date
        )
        
        self.total_chats = today_assignments.count()
        self.responded_chats = today_assignments.exclude(first_response_at=None).count()
        
        # Calculate average response time
        response_times = [
            assignment.response_time for assignment in today_assignments
            if assignment.response_time
        ]
        if response_times:
            self.average_response_time = sum(response_times, timedelta()) / len(response_times)
        
        # Calculate SLA compliance rate
        compliant_assignments = today_assignments.filter(sla_status='compliant')
        if self.total_chats > 0:
            self.sla_compliance_rate = (compliant_assignments.count() / self.total_chats) * 100
        
        # Count breached chats
        self.breached_chats = today_assignments.filter(sla_status='breached').count()
        
        self.save()

# ADD ESTATE

class PlotSize(models.Model):
    """Defines the available plot sizes - company scoped"""
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='plot_sizes', null=True, blank=True, help_text="Company that owns this plot size")
    size = models.CharField(max_length=50, verbose_name="Plot Size")

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = "Plot Size"
        verbose_name_plural = "Plot Sizes"
        unique_together = ('company', 'size')  # SECURITY: Unique per company, not globally

    def __str__(self):
        return self.size


class PlotNumber(models.Model):
    """Each plot within an estate has a unique number - company scoped"""
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='plot_numbers', null=True, blank=True, help_text="Company that owns this plot number")
    number = models.CharField(max_length=50, verbose_name="Plot Number")

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = "Plot Number"
        verbose_name_plural = "Plot Numbers"
        unique_together = ('company', 'number')  # SECURITY: Unique per company, not globally

    def __str__(self):
        return self.number


class Estate(models.Model):
    """Defines an estate, its size, location, and title deed type"""
    TITLE_DEED_CHOICES = [
        ('FCDA RofO', 'FCDA RofO'),
        ('FCDA CofO', 'FCDA CofO'),
        ('RofO', 'RofO'),
        ('Gazette', 'Gazette'),
    ]

    name = models.CharField(max_length=255, verbose_name="Estate Name")
    location = models.CharField(max_length=255, verbose_name="Location")
    estate_size = models.CharField(max_length=255, verbose_name="Estate Size")
    title_deed = models.CharField(max_length=255, choices=TITLE_DEED_CHOICES, verbose_name="Title Deed")
    date_added = models.DateTimeField(default=timezone.now, verbose_name="Date Added")
    # SECURITY: Link each estate to a company for multi-tenant isolation.
    # Make nullable to avoid migration issues for legacy data; set when available.
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='estates', null=True, blank=True, help_text="Company that owns this estate")

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = "Estate"
        verbose_name_plural = "Estates"

    @property
    def inventory_status(self):
        return {
            size_unit.plot_size.size: {
                'total': size_unit.total_units,
                'allocated': size_unit.full_allocations,
                'reserved': size_unit.part_allocations
            }
            for size_unit in self.estate_plots.plotsizeunits.all()
        }
    
    @property
    def available_floor_plans(self):
        """Returns a dictionary of floor plans based on plot sizes in the estate."""
        return {
            floor_plan.plot_size.size: floor_plan.floor_plan_image.url
            for floor_plan in self.floor_plans.all()
        }

    @property
    def layout_url(self):
        """Returns the layout image URL if available"""
        return self.layout.layout_image.url if self.layout else None

    @property
    def map_url(self):
        """Returns the Google Maps link for the estate"""
        return self.map.generate_google_map_link if self.map else "No map available"


    def __str__(self):
        return self.name


class PlotSizeUnits(models.Model):
    """Tracks units per plot size within an EstatePlot"""
    estate_plot = models.ForeignKey('EstatePlot', on_delete=models.CASCADE, related_name='plotsizeunits')
    plot_size = models.ForeignKey(PlotSize, on_delete=models.CASCADE)
    total_units = models.PositiveIntegerField(default=0)
    available_units = models.PositiveIntegerField(default=0)

    @property
    def plot_size_for_transaction(self):
        return self.plot_size.size

    @property
    def full_allocations(self):
        if not self.pk:
            return 0
        return self.allocations.filter(payment_type='full', plot_number__isnull=False).count()

    @property
    def part_allocations(self):
        if not self.pk:
            return 0
        return self.allocations.filter(payment_type='part').count()
    
    @property
    def grand_total(self):
        """Total number of units per plot size within an estate."""
        return self.total_units
    
    @property
    def computed_available_units(self):
        # Calculate available units based on total minus allocated and reserved.
        return self.total_units - (self.full_allocations + self.part_allocations)

    @property
    def formatted_size(self):
        """Display format without availability information"""
        return f"{self.plot_size.size}"
    
    def clean(self):
        # Prevent over-allocation
        if self.total_units < (self.full_allocations + self.part_allocations):
            raise ValidationError(
                f"Cannot reduce total units below allocated count for {self.plot_size.size}"
            )

    def save(self, *args, **kwargs):
        # Calculate available units
        self.available_units = self.total_units - (self.full_allocations + self.part_allocations)
        
        if self.available_units < 0:
            raise ValidationError(
                f"Over-allocated {self.plot_size.size} units! Available cannot be negative"
            )
            
        self.available_units = self.computed_available_units

         # Recalculate availability
        self.available_units = self.total_units - (
            self.full_allocations + self.part_allocations
        )
        
        if self.available_units < 0:
            raise ValidationError(
                f"Over-allocated {self.plot_size.size} units! "
                f"Available cannot be negative"
            )
        super().save(*args, **kwargs)

    def check_availability(self):
        if self.available_units <= 0:
            return (False, f"{self.plot_size.size} units completely allocated")
        return (True, "")


    def __str__(self):
        return f"{self.plot_size.size}: {self.available_units}/{self.total_units} units"
    

class EstatePlot(models.Model):
    """Manages plot sizes, numbers, and units per size."""
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name="estate_plots")
    plot_sizes = models.ManyToManyField(PlotSize, through=PlotSizeUnits)
    plot_numbers = models.ManyToManyField(PlotNumber, related_name='estates')

    class Meta:
        verbose_name = "Estate Plot"
        verbose_name_plural = "Estate Plots"

    @property
    def is_allocated(self):
        """Check if any plot number within this estate plot has been allocated"""
        # Ensure checking only allocations for this estate plot, not across all estates
        return self.plot_numbers.filter(plotallocation__estate=self.estate).exists()
    
    @property
    def allocated_plot_count(self):
        """Count of allocated plots specific to this estate plot"""
        return self.plot_numbers.filter(plotallocation__estate=self.estate).count()
    
    @property
    def available_plot_count(self):
        """Count of available plots specific to this estate plot"""
        return self.plot_numbers.count() - self.allocated_plot_count

    def clean(self):
        # Only validate if the instance exists in DB
        if self.pk:
            total_units = sum(unit.total_units for unit in self.plotsizeunits.all())
            if self.plot_numbers.count() != total_units:
                raise ValidationError(
                    f"Total plot numbers ({self.plot_numbers.count()}) must match "
                    f"total units ({total_units})"
                )

    def __str__(self):
        return f"{self.estate.name} - {self.plot_sizes.count()} plot sizes"


# PLOT ALLOCATION
class PlotAllocation(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('part', 'Part Payment'),
    ]

    plot_size_unit = models.ForeignKey(
        PlotSizeUnits, 
        on_delete=models.CASCADE,
        related_name='allocations'
    )

    client = models.ForeignKey(
        # settings.AUTH_USER_MODEL,
        ClientUser,
        on_delete=models.CASCADE,
        # limit_choices_to={'role': 'client'},
        verbose_name="Registered Client Name"
    )
    estate = models.ForeignKey(
        'Estate',
        on_delete=models.CASCADE,
        verbose_name="Estate Name"
    )
    plot_size = models.ForeignKey(
        'PlotSize',
        on_delete=models.CASCADE,
        verbose_name="Plot Size"
    )
    plot_number = models.ForeignKey(
        'PlotNumber',
        on_delete=models.CASCADE,
        verbose_name="Plot Number", 
        null=True, blank=True
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPE_CHOICES,
        verbose_name="Payment Type"
    )
    date_allocated = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plot Allocation"
        verbose_name_plural = "Plot Allocations"
        unique_together = ('estate', 'plot_number')

    # Method for easier data access
    def get_estate_info(self):
        return {
            "id": self.estate.id,
            "name": self.estate.name,
            "plot_size": self.plot_size.size,
            "payment_type": self.payment_type
        }
    
    @property
    def plot_size_for_transaction(self):
        # return self.plot_size_unit.plot_size.size
        """FIXED PROPERTY ACCESSOR"""
        if self.plot_size_unit and self.plot_size_unit.plot_size:
            return self.plot_size_unit.plot_size.size
        return "Unknown"
    

    def assign_plot_number(self):
        if self.payment_type == 'full' and not self.plot_number:
            available = PlotNumber.objects.filter(
                estates__estate=self.estate
            ).exclude(
                id__in=PlotAllocation.objects.filter(
                    estate=self.estate
                ).values('plot_number')
            ).filter(
                estates__estate=self.estate  # Ensure only plot numbers within the current estate
            ).first()

            if available:
                self.plot_number = available
                self.save()

    def clean(self):
        # Validate plot number uniqueness per estate
        if self.payment_type == 'full' and self.plot_number:
            exists = PlotAllocation.objects.filter(
                estate=self.estate,
                plot_number=self.plot_number
            ).exclude(id=self.id).exists()
            
            if exists:
                conflict = PlotAllocation.objects.get(
                    estate=self.estate,
                    plot_number=self.plot_number
                )
                raise ValidationError(
                    f"Plot number already allocated to {conflict.client.full_name}"
                )

        # Validate unit availability
        if self._state.adding:  # Only check for new allocations
            available, msg = self.plot_size_unit.check_availability()
            if not available:
                raise ValidationError(msg)

    def save(self, *args, **kwargs):
        """
        When a new allocation is created, subtract one unit from the 
        corresponding PlotSizeUnits.available_units. (For updates, you can 
        add more sophisticated re-allocation logic if needed.)
        """
        is_new = self.pk is None

        if is_new:
            # Check that there is at least one available unit
            if self.plot_size_unit.available_units <= 0:
                raise ValidationError("No available units left for the selected plot size.")

            # For a full payment allocation, ensure a plot number was chosen
            if self.payment_type == 'full' and not self.plot_number:
                raise ValidationError("Plot number is required for full payment allocations.")

            # Decrement the available units (whether full or part payment)
            self.plot_size_unit.available_units -= 1
            self.plot_size_unit.save()
        else:
            # (Optional: handle changes in an update case by reverting the previous change first.)
            original_allocation = PlotAllocation.objects.get(pk=self.pk)
            if original_allocation.payment_type != self.payment_type:
                # Revert the previous allocation's effect
                original_allocation.plot_size_unit.available_units += 1
                original_allocation.plot_size_unit.save()

                # Then subtract one for the new allocation type
                self.plot_size_unit.available_units -= 1
                self.plot_size_unit.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Plot: {self.plot_number} - Payment: {self.payment_type}"


# NOTIFICATIONS
class Notification(models.Model):
    ANNOUNCEMENT = 'ANNOUNCEMENT'
    CLIENT_ANNOUNCEMENT = 'CLIENT_ANNOUNCEMENT'
    MARKETER_ANNOUNCEMENT = 'MARKETER_ANNOUNCEMENT'

    ANNOUNCEMENT_CHOICES = [
        (ANNOUNCEMENT, 'General Announcement'),
        (CLIENT_ANNOUNCEMENT, 'Client Announcement'),
        (MARKETER_ANNOUNCEMENT, 'Marketer Announcement'),
    ]

    notification_type = models.CharField(
        max_length=100,
        choices=ANNOUNCEMENT_CHOICES,
        default=ANNOUNCEMENT
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    # Company field for multi-tenant notification isolation
    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        help_text="Company this notification belongs to. Null means global/system notification."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"

    class Meta:
        ordering = ['-created_at']

class UserNotification(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'notification')
        ordering = ['-created_at']
        verbose_name = 'User Notification'
        verbose_name_plural = 'User Notifications'

    def __str__(self):
        return f"{self.user.email} - {self.notification.title}"

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'read': self.read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'notification': self.notification.serialize() if self.notification_id else None,
        }


class NotificationDispatch(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = (
        (STATUS_QUEUED, 'Queued'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='dispatches'
    )
    total_recipients = models.PositiveIntegerField(default=0)
    processed_recipients = models.PositiveIntegerField(default=0)
    total_batches = models.PositiveIntegerField(default=0)
    processed_batches = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    last_error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def mark_processing(self):
        from django.utils import timezone

        self.status = self.STATUS_PROCESSING
        self.started_at = self.started_at or timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_completed(self):
        from django.utils import timezone

        self.status = self.STATUS_COMPLETED
        self.finished_at = timezone.now()
        self.save(update_fields=['status', 'finished_at', 'updated_at'])

    def mark_failed(self, error_message: str = ''):
        from django.utils import timezone

        self.status = self.STATUS_FAILED
        self.finished_at = timezone.now()
        self.last_error = error_message[:2000]
        self.save(update_fields=['status', 'finished_at', 'last_error', 'updated_at'])

    def as_dict(self) -> dict:
        total_recipients = self.total_recipients or 0
        processed_recipients = self.processed_recipients or 0
        remaining_recipients = max(total_recipients - processed_recipients, 0)

        total_batches = self.total_batches or 0
        processed_batches = self.processed_batches or 0
        remaining_batches = max(total_batches - processed_batches, 0)

        if total_recipients > 0:
            progress_percent = round((processed_recipients / total_recipients) * 100, 2)
        elif processed_recipients > 0:
            progress_percent = 100.0
        else:
            progress_percent = 0.0

        return {
            'id': self.id,
            'notification_id': self.notification_id,
            'status': self.status,
            'total_recipients': total_recipients,
            'processed_recipients': processed_recipients,
            'remaining_recipients': remaining_recipients,
            'total_batches': total_batches,
            'processed_batches': processed_batches,
            'remaining_batches': remaining_batches,
            'progress_percent': progress_percent,
            'last_error': self.last_error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }


class UserDeviceToken(models.Model):
    class Platform(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='device_tokens'
    )
    token = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    app_version = models.CharField(max_length=32, blank=True)
    device_model = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Device Token'
        verbose_name_plural = 'User Device Tokens'
        unique_together = ('user', 'token')
        indexes = [
            models.Index(fields=['user', 'platform']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} · {self.platform}"

    def mark_seen(self, *, platform: str | None = None, app_version: str | None = None, device_model: str | None = None) -> None:
        updated = False
        if platform and platform != self.platform:
            self.platform = platform
            updated = True
        if app_version is not None and app_version != self.app_version:
            self.app_version = app_version
            updated = True
        if device_model is not None and device_model != self.device_model:
            self.device_model = device_model
            updated = True
        if not self.is_active:
            self.is_active = True
            updated = True
        if updated:
            self.save(update_fields=['platform', 'app_version', 'device_model', 'is_active', 'last_seen'])


# OTHER ESTATE MODELS
class EstateFloorPlan(models.Model):
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name='floor_plans')
    plot_size = models.ForeignKey(PlotSize, on_delete=models.CASCADE, related_name='floor_plans')
    floor_plan_image = models.ImageField(upload_to="floor_plans/")
    plan_title = models.CharField(max_length=255)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_uploaded']

    def clean(self):
        # Validate image size
        max_size = 5 * 1024 * 1024  # 5MB
        if self.floor_plan_image.size > max_size:
            raise ValidationError("Max image size is 5MB")

    def __str__(self):
        return f"{self.plan_title} - {self.estate.name} ({self.plot_size.size})"

    

# prototype
class EstatePrototype(models.Model):
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name='prototypes')
    plot_size = models.ForeignKey(PlotSize, on_delete=models.CASCADE, related_name='prototypes')
    prototype_image = models.ImageField(upload_to="prototypes/")
    Title = models.CharField(max_length=255, null=True, blank=True)
    Description = models.CharField(max_length=255, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_uploaded']

    def __str__(self):
        return f"{self.Title} - {self.estate.name} ({self.plot_size.size})"

    def clean(self):
        # Validate image size
        max_size = 5 * 1024 * 1024  # 5MB
        if self.prototype_image.size > max_size:
            raise ValidationError("Max image size is 5MB")

# amenities
AMENITIES_CHOICES = [
    ('gated_security', 'Gated Security'),
    ('surveillance', '24/7 Surveillance'),
    ('power_backup', 'Power Backup'),
    ('water_supply', 'Water Supply & Treatment'),
    ('clubhouse', 'Clubhouse/Community Center'),
    ('swimming_pool', 'Swimming Pool'),
    ('gym', 'Gym/Fitness Center'),
    ('sports_facilities', 'Sports Facilities'),
    ('playground', "Children's Playground"),
    ('school', 'School/Educational Facility'),
    ('clinic', 'Health Clinic'),
    ('retail', 'Retail/Commercial Area'),
    ('religious', 'Religious Facility'),
    ('green_areas', 'Green Areas & Parks'),
    ('parking', 'Parking Spaces'),
    ('management_office', 'Estate Management Office'),
    ('high_speed_internet', 'High-Speed Internet'),
    ('smart_home', 'Smart Home Systems'),
]

AMENITY_ICONS = {
    'gated_security': 'bi-shield-lock',
    'surveillance': 'bi-camera-video',
    'power_backup': 'bi-lightning-charge-fill',
    'water_supply': 'bi-droplet-fill',
    'clubhouse': 'bi-building',
    'swimming_pool': 'bi-water',
    'gym': 'bi-barbell',
    'sports_facilities': 'bi-trophy',
    'playground': 'bi-emoji-smile',
    'school': 'bi-mortarboard',
    'clinic': 'bi-hospital',
    'retail': 'bi-shop',
    'religious': 'bi-house',
    'green_areas': 'bi-tree',
    'parking': 'bi-car-front-fill',
    'management_office': 'bi-briefcase',
    'high_speed_internet': 'bi-wifi',
    'smart_home': 'bi-house-door-fill',
}


class EstateAmenitie(models.Model):
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name='estate_amenity')
    amenities = MultiSelectField(
        choices=AMENITIES_CHOICES,
        blank=True,
        null=True,
        verbose_name="Select Amenities"
    )

    
    def get_amenity_display(self):
        """
        Returns a list of tuples (display_name, icon_class) for each selected amenity.
        """
        if self.amenities:
            choices_dict = dict(AMENITIES_CHOICES)
            # Iterate directly over the MSFList without calling split()
            return [(choices_dict.get(code, code), AMENITY_ICONS.get(code, '')) for code in self.amenities]
        return []


    def __str__(self):
        return f"Amenities for {self.estate.name}"

# estate layout
class EstateLayout(models.Model):
    """Stores estate layout images"""
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name="estate_layout")
    layout_image = models.ImageField(
        upload_to="estate_layouts/", verbose_name="Estate Layout Image"
    )

    class Meta:
        verbose_name = "Estate Layout"
        verbose_name_plural = "Estate Layouts"

    def __str__(self):
        return f"{self.estate.name} Layout"


# Estate Map
class EstateMap(models.Model):
    """Stores estate location details with Google Maps integration"""
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE, related_name="map")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Longitude"
    )
    google_map_link = models.URLField(
        max_length=100000, blank=True, null=True, verbose_name="Google Maps Link"
    )

    class Meta:
        verbose_name = "Estate Map"
        verbose_name_plural = "Estate Maps"

    def __str__(self):
        return f"{self.estate.name} Map"

    @property
    def generate_google_map_link(self):
        if self.latitude is not None and self.longitude is not None:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}&z=15"
        return self.google_map_link or ""


class ProgressStatus(models.Model):
    estate = models.ForeignKey(Estate, related_name='progress_status', on_delete=models.CASCADE)
    progress_status = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.estate.name} - {self.progress_status}"


# CLIENTS
class PropertyRequest(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    estate = models.ForeignKey(Estate, on_delete=models.CASCADE)
    plot_size = models.ForeignKey(PlotSize, on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50, default="Pending")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Request by {self.client} for {self.estate.name} ({self.plot_size})"


# MANAGEMENT DASHBOARD

# Land Plot Transactions

class Transaction(models.Model):
    INSTALLMENT_PLANS = [
        ('50-30-20', '50-30-20'),
        ('60-20-20', '60-20-20'),
        ('40-30-30', '40-30-30'),
        ('custom', 'Custom'),
    ]
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('pos', 'POS'),
    ]
    INSTALLMENT_CHOICES = [
        (1, 'First'),
        (2, 'Second'),
        (3, 'Third'),
    ]

    # SECURITY: Explicit company FK for direct multi-tenant filtering
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    client = models.ForeignKey(ClientUser, on_delete=models.PROTECT, related_name='transactions')
    allocation = models.ForeignKey(PlotAllocation, on_delete=models.PROTECT, related_name='transactions')
    marketer = models.ForeignKey(MarketerUser, on_delete=models.PROTECT, null=True, blank=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, blank=True, null=True)
    reference_code = models.CharField(max_length=50, null=True, editable=False)

    transaction_date = models.DateField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    special_notes = models.TextField(blank=True, null=True)

    installment_plan = models.CharField(max_length=20, choices=INSTALLMENT_PLANS, blank=True, null=True)
    first_percent = models.PositiveSmallIntegerField(blank=True, null=True)
    second_percent = models.PositiveSmallIntegerField(blank=True, null=True)
    third_percent = models.PositiveSmallIntegerField(blank=True, null=True)
    first_installment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    second_installment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    third_installment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_duration = models.PositiveSmallIntegerField(blank=True, null=True)
    custom_duration = models.PositiveSmallIntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        ordering = ['-transaction_date']

    def clean(self):
        if self.allocation.payment_type == 'full':
            if any([self.first_percent, self.second_percent, self.third_percent]):
                raise ValidationError("Full payments can't have installment percentages")
        else:  # part-payment
            if None in (self.first_percent, self.second_percent, self.third_percent):
                raise ValidationError("All installment percentages are required")
            if self.first_percent + self.second_percent + self.third_percent != 100:
                raise ValidationError("Installment percentages must sum to 100%")

    def save(self, *args, **kwargs):
        # SECURITY: Auto-populate company from allocation's estate
        if not self.company_id and self.allocation and self.allocation.estate:
            self.company = self.allocation.estate.company
        
        if not self.reference_code:
            # Generate reference code with company-specific prefix
            # CRITICAL: Company MUST be present - payment reference is legally sensitive
            company = self.company or (self.allocation.estate.company if self.allocation and self.allocation.estate else None)
            if not company:
                raise ValueError(
                    "Cannot generate payment reference code: Company is required for proper payment tracking and compliance. "
                    "Ensure transaction is linked to a valid company before saving."
                )
            
            prefix = company._company_prefix()
            date_str = timezone.now().strftime("%Y%m%d")
            plot_raw = str(self.allocation.plot_size)
            m = re.search(r'\d+', plot_raw)
            size_num = m.group(0) if m else plot_raw
            suffix = f"{random.randint(0, 9999):04d}"
            self.reference_code = f"{prefix}{date_str}-{size_num}-{suffix}"

        # Auto-assign marketer based on client->company assignments if available
        if not self.marketer_id:
            try:
                company = self.allocation.estate.company if (self.allocation and self.allocation.estate) else None
            except Exception:
                company = None

            try:
                assigned = None
                if hasattr(self.client, 'get_assigned_marketer'):
                    assigned = self.client.get_assigned_marketer(company=company)
                else:
                    assigned = getattr(self.client, 'assigned_marketer', None)
                if assigned:
                    self.marketer = assigned
            except Exception:
                # fallback to legacy field
                if getattr(self.client, 'assigned_marketer', None):
                    self.marketer = self.client.assigned_marketer
        
        if self.allocation.payment_type == 'part' and self.installment_plan:
            if self.installment_plan == 'custom':
                pcts = [
                    self.first_percent or 0,
                    self.second_percent or 0,
                    self.third_percent or 0
                ]
            else:
                try:
                    pcts = list(map(int, self.installment_plan.split('-')))
                except (AttributeError, ValueError):
                    pcts = [0, 0, 0]
            
            if sum(pcts) == 100:
                self.first_installment = (self.total_amount * Decimal(pcts[0])) / 100
                self.second_installment = (self.total_amount * Decimal(pcts[1])) / 100
                self.third_installment = (self.total_amount * Decimal(pcts[2])) / 100
        
        super().save(*args, **kwargs)

    @property
    def total_paid(self):
        return sum(payment.amount_paid for payment in self.payment_records.all())
    
    @property
    def balance(self):
        return self.total_amount - self.total_paid
    
    @property
    def next_due_date(self):
        if self.allocation.payment_type == 'full':
            return None
        
        last_payment = self.payment_records.order_by('-payment_date').first()
        if last_payment:
            if last_payment.installment == 1:
                return self.transaction_date + relativedelta(months=+3)
            elif last_payment.installment == 2:
                return self.transaction_date + relativedelta(months=+6)
        return self.due_date

    @property
    def due_date(self):
        if self.payment_duration:
            return self.transaction_date + relativedelta(months=self.payment_duration)
        elif self.custom_duration:
            return self.transaction_date + relativedelta(months=self.custom_duration)
        return None
    
    @property
    def status(self):
        if self.allocation.payment_type == 'full':
            return "Fully Paid"
        
        try:
            payment_records = self.payment_records.all()
            total_amount_paid = sum(record.amount_paid for record in payment_records)

            if total_amount_paid >= self.total_amount:
                return "Paid Complete"
            elif total_amount_paid > 0:
                if self.due_date and datetime.date.today() > self.due_date:
                    return "Overdue"
                return "Part Payment"
            else:
                if self.due_date and datetime.date.today() > self.due_date:
                    return "Overdue"
                return "Pending"
        except Exception:
            return "Unknown"


    @property
    def payment_installments(self):
        if self.allocation.payment_type == 'full' or not self.installment_plan:
            return []
            
        if self.installment_plan == 'custom':
            pcts = [self.first_percent, self.second_percent, self.third_percent]
        else:
            try:
                pcts = list(map(int, self.installment_plan.split('-')))
            except:
                pcts = [0, 0, 0]
                
        dues = [(self.total_amount * p) / 100 for p in pcts]
        paid = {1: Decimal(0), 2: Decimal(0), 3: Decimal(0)}
        
        for pr in self.payment_records.all():
            if pr.installment in paid:
                paid[pr.installment] += pr.amount_paid
                
        installments = []
        for i in range(3):
            n = i + 1
            due_amt = dues[i] if i < len(dues) else Decimal(0)
            paid_amt = paid[n]
            remaining = max(due_amt - paid_amt, Decimal(0))
            
            installments.append({
                'n': n,
                'due': due_amt.quantize(Decimal('0.01')),
                'paid': paid_amt.quantize(Decimal('0.01')),
                'remaining': remaining.quantize(Decimal('0.01'))
            })
            
        return installments

    def __str__(self):
        return f"{self.client.full_name} - {self.allocation.estate.name} ({self.allocation.plot_size})"

class PaymentRecord(models.Model):
    PAYMENT_METHODS = Transaction.PAYMENT_METHODS
    INSTALLMENT_CHOICES = Transaction.INSTALLMENT_CHOICES

    # SECURITY: Explicit company FK for direct multi-tenant filtering
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payment_records', null=True, blank=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='payment_records')
    installment = models.PositiveSmallIntegerField(choices=INSTALLMENT_CHOICES, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    reference_code = models.CharField(max_length=50, null=True, editable=False)
    selected_installment = models.PositiveSmallIntegerField(
        choices=INSTALLMENT_CHOICES,
        null=True,
        blank=True,
        help_text="The installment the client selected when making payment"
    )

    receipt_generated = models.BooleanField(default=False)
    receipt_date = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=50, null=True, blank=True)

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    def save(self, *args, **kwargs):
        # SECURITY: Auto-populate company from transaction's allocation
        if not self.company_id and self.transaction and self.transaction.allocation:
            self.company = self.transaction.allocation.estate.company
        
        if not self.reference_code:
            # Generate reference code with company-specific prefix
            # CRITICAL: Company MUST be present - payment reference is legally sensitive
            company = self.company or (self.transaction.allocation.estate.company if self.transaction and self.transaction.allocation and self.transaction.allocation.estate else None)
            if not company:
                raise ValueError(
                    "Cannot generate payment record reference code: Company is required for proper payment tracking and compliance. "
                    "Ensure payment record is linked to a valid company before saving."
                )
            
            prefix = company._company_prefix()
            date = timezone.now().strftime("%Y%m%d")
            raw = str(self.transaction.allocation.plot_size)
            m = re.search(r'\d+', raw)
            size = m.group(0) if m else raw
            method = self.payment_method.upper()[:3]
            suffix = f"{random.randint(0,9999):04d}"
            self.reference_code = f"{prefix}{date}-{size}-{method}{suffix}"

        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.reference_code} → {self.transaction.reference_code}"

    def get_selected_installment_display(self):
        if not self.selected_installment:
            return ""
        for num, text in self.INSTALLMENT_CHOICES:
            if num == self.selected_installment:
                return text
        return ""
    
    def generate_receipt_number(self):
        if not self.receipt_number:
            date_str = timezone.now().strftime("%Y%m%d")
            rand_str = f"{random.randint(1000, 9999)}"
            self.receipt_number = f"RC-{date_str}-{rand_str}"
        return self.receipt_number


# Marketers Performance
class MarketerCommission(models.Model):
    # SECURITY: Explicit company FK for direct multi-tenant filtering
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='marketer_commissions',
        null=True,
        blank=True,
        verbose_name="Company"
    )
    marketer = models.ForeignKey(
        MarketerUser, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Marketer (leave blank for all marketers)"
    )
    rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name="Commission Rate (%)"
    )
    effective_date = models.DateField(
        verbose_name="Effective Date"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = "Commission Rate"
        verbose_name_plural = "Commission Rates"
        ordering = ['-effective_date']
        unique_together = ('company', 'marketer')  # SECURITY: Unique per company, not globally

    def save(self, *args, **kwargs):
        # SECURITY: Auto-populate company from marketer's company_profile
        if not self.company_id and self.marketer and self.marketer.company_profile:
            self.company = self.marketer.company_profile
        super().save(*args, **kwargs)

    def __str__(self):
        company_name = self.company.company_name if self.company else "Unknown Company"
        if self.marketer:
            return f"{self.marketer.full_name} - {company_name}: {self.rate}% from {self.effective_date}"
        return f"All Marketers - {company_name}: {self.rate}% from {self.effective_date}"

class MarketerTarget(models.Model):
    PERIOD_TYPE_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]

    # SECURITY: Explicit company FK for direct multi-tenant filtering
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='marketer_targets',
        null=True,
        blank=True,
        verbose_name="Company"
    )
    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        verbose_name="Period Type"
    )
    specific_period = models.CharField(
        max_length=20,
        verbose_name="Specific Period (e.g., 2024-04, 2024-Q2, 2024)"
    )
    marketer = models.ForeignKey(
        MarketerUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Marketer (leave blank for all marketers)"
    )
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Target Amount (₦)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = "Sales Target"
        verbose_name_plural = "Sales Targets"
        unique_together = ('company', 'period_type', 'specific_period', 'marketer')  # SECURITY: Unique per company
        indexes = [
            models.Index(fields=['company', 'period_type']),
            models.Index(fields=['company', 'specific_period']),
        ]

    def save(self, *args, **kwargs):
        # SECURITY: Auto-populate company from marketer's company_profile
        if not self.company_id and self.marketer and self.marketer.company_profile:
            self.company = self.marketer.company_profile
        super().save(*args, **kwargs)

    def __str__(self):
        company_name = self.company.company_name if self.company else "Unknown Company"
        marketer_name = self.marketer.full_name if self.marketer else "All Marketers"
        return f"{marketer_name} - {company_name} - {self.specific_period}: ₦{self.target_amount}"

class MarketerPerformanceRecord(models.Model):
    # SECURITY: Explicit company FK for direct multi-tenant filtering
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='marketer_performance_records',
        null=True,
        blank=True,
        verbose_name="Company"
    )
    marketer = models.ForeignKey(MarketerUser, on_delete=models.CASCADE)
    period_type = models.CharField(max_length=20, choices=MarketerTarget.PERIOD_TYPE_CHOICES)
    specific_period = models.CharField(max_length=20)
    closed_deals = models.PositiveIntegerField(default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        unique_together = ('company', 'marketer', 'period_type', 'specific_period')  # SECURITY: Unique per company
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'marketer']),
            models.Index(fields=['company', 'period_type']),
            models.Index(fields=['company', 'specific_period']),
            models.Index(fields=['company', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        # SECURITY: Auto-populate company from marketer's company_profile
        if not self.company_id and self.marketer and self.marketer.company_profile:
            self.company = self.marketer.company_profile
        super().save(*args, **kwargs)

    def __str__(self):
        company_name = self.company.company_name if self.company else "Unknown Company"
        return f"{self.marketer.full_name} - {company_name} - {self.specific_period}"

# VALUE EVALUATION

class PropertyPrice(models.Model):
    """
    Current pricing record for an estate + specific plot‐size unit.
    """
    # SECURITY: Explicit company FK for direct multi-tenant filtering
    company     = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="property_prices",
        null=True,
        blank=True
    )
    estate      = models.ForeignKey(
        Estate,
        on_delete=models.CASCADE,
        related_name="property_prices"
    )
    plot_unit   = models.ForeignKey(
        PlotSizeUnits,
        on_delete=models.CASCADE,
        related_name="property_prices"
    )
    presale     = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Initial presale price"
    )
    previous    = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Previous price before this change"
    )
    current     = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Current active price"
    )
    effective   = models.DateField(
        help_text="Date this price becomes effective"
    )
    notes       = models.TextField(
        blank=True,
        help_text="Optional notes about this price change"
    )
    created_at  = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created"
    )

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        unique_together = ("estate", "plot_unit")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # SECURITY: Auto-populate company from estate
        if not self.company_id and self.estate:
            self.company = self.estate.company
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.estate.name} | {self.plot_unit.plot_size.size} → ₦{self.current:,}"

class PriceHistory(models.Model):
    """
    Snapshot of each time a PropertyPrice is created or updated.
    """
    price       = models.ForeignKey(
        PropertyPrice,
        on_delete=models.CASCADE,
        related_name="history"
    )
    presale     = models.DecimalField(max_digits=12, decimal_places=2)
    previous    = models.DecimalField(max_digits=12, decimal_places=2)
    current     = models.DecimalField(max_digits=12, decimal_places=2)
    effective   = models.DateField()
    notes       = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return (
            f"{self.price.estate.name} | {self.price.plot_unit.plot_size.size} "
            f"@ ₦{self.current:,} on {self.effective}"
        )

class PromotionalOffer(models.Model):
    """
    Defines a promotion over one or more estates.
    """
    name        = models.CharField(max_length=200)
    discount    = models.PositiveSmallIntegerField(
        help_text="Percentage discount (1–100)"
    )
    start       = models.DateField()
    end         = models.DateField()
    estates     = models.ManyToManyField(
        Estate,
        related_name="promotional_offers",
        help_text="Estates this promo applies to"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional promo description/details"
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        """
        True when today's local date falls between start and end (inclusive).
        Use this in templates as `p.is_active`.
        """
        try:
            today = timezone.localdate()
            if self.start and self.end:
                return self.start <= today <= self.end
        except Exception:
            return False
        return False

    def __str__(self):
        return f"{self.name} ({self.discount}% off) from {self.start} to {self.end}"


# ============================================================================
# BILLING & INVOICING MODELS (Phase 1 - Critical)
# ============================================================================

class Invoice(models.Model):
    """Monthly invoice for SaaS subscription and usage charges"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='invoices',
        verbose_name='Company'
    )
    
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Invoice Number',
        help_text='Auto-generated: INV-YYYYMM-XXXXX'
    )
    
    period_start = models.DateField(
        verbose_name='Period Start Date'
    )
    
    period_end = models.DateField(
        verbose_name='Period End Date',
        null=True,  # Allow null for existing records
        blank=True
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Subscription & Usage Amount (₦)',
        help_text='Subscription fee + overage charges - credits'
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Tax Amount (7.5% VAT)',
        help_text='Automatically calculated as 7.5% for Nigeria'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Invoice Status'
    )
    
    due_date = models.DateField(
        verbose_name='Payment Due Date'
    )
    
    issued_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date Issued',
        help_text='When status changed to "issued"'
    )
    
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date Paid',
        help_text='When payment was received'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Invoice Notes',
        help_text='Internal notes about this invoice'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use CompanyAwareManager for automatic tenant isolation
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-period_end']
        unique_together = ('company', 'period_start', 'period_end')
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'period_end']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['paid_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-calculate tax and generate invoice number"""
        # Generate invoice number if not set
        if not self.invoice_number:
            from django.utils import timezone
            year_month = timezone.now().strftime('%Y%m')
            count = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{year_month}'
            ).count() + 1
            self.invoice_number = f'INV-{year_month}-{count:05d}'
        
        # Calculate tax (7.5% VAT for Nigeria)
        self.tax_amount = self.amount * Decimal('0.075')
        
        # Set issued_at if transitioning to issued
        if self.status == 'issued' and not self.issued_at:
            from django.utils import timezone
            self.issued_at = timezone.now()
        
        # Set paid_at if transitioning to paid
        if self.status == 'paid' and not self.paid_at:
            from django.utils import timezone
            self.paid_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def total_amount(self):
        """Total due: amount + tax"""
        return self.amount + self.tax_amount
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status in ['paid', 'cancelled']:
            return False
        from django.utils import timezone
        return timezone.now().date() > self.due_date
    
    @property
    def days_until_due(self):
        """Days remaining until due date"""
        from django.utils import timezone
        delta = self.due_date - timezone.now().date()
        return max(0, delta.days)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.company.company_name} ({self.period_end.strftime('%B %Y')})"


class Payment(models.Model):
    """Individual payment records for invoices"""
    
    PAYMENT_METHOD_CHOICES = [
        ('stripe', 'Stripe Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('credit', 'Credit Note'),
        ('other', 'Other'),
    ]
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Invoice'
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Payment Amount (₦)'
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='Payment Method'
    )
    
    payment_reference = models.CharField(
        max_length=100,
        verbose_name='Payment Reference',
        help_text='Transaction ID, check number, or reference for verification'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Payment Notes'
    )
    
    paid_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Payment Date'
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Verification Date',
        help_text='When payment was verified by admin'
    )
    
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        verbose_name='Verified By'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Use CompanyAwareManager for automatic tenant isolation (via invoice.company)
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # Fallback for unfiltered queries

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-paid_at']
        indexes = [
            models.Index(fields=['invoice', 'payment_method']),
            models.Index(fields=['paid_at']),
        ]
    
    @property
    def is_verified(self):
        """Check if payment has been verified"""
        return self.verified_at is not None
    
    def mark_verified(self, verified_by: CustomUser):
        """Mark payment as verified"""
        from django.utils import timezone
        self.verified_at = timezone.now()
        self.verified_by = verified_by
        self.save(update_fields=['verified_at', 'verified_by'])
    
    def __str__(self):
        return f"Payment {self.payment_reference} - ₦{self.amount:,.0f} ({self.get_payment_method_display()})"


# MESSAGING AND BIRTHDAY.


