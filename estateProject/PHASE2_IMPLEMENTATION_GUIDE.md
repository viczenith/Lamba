# Phase 2: Grace Period, Warnings & Admin Dashboard - Implementation Guide

## Executive Summary

This guide walks you through implementing the advanced subscription features:
- **Grace Period Logic** (7 days after expiration with read-only access)
- **Warning Banners** (Yellow → Orange → Red countdown)
- **Countdown Modals** (Real-time expiration display)
- **Admin Dashboard** (Billing, usage, renewal interfaces)
- **Feature Restrictions** (Subscription-aware access control)

**Estimated Implementation Time**: 2-3 hours
**Complexity**: Medium (integrates multiple components)

---

## PART 1: DATABASE MIGRATIONS

### Step 1: Create New Models

Create migration file:
```bash
python manage.py makemigrations estateApp --name add_subscription_billing
```

This will include:
- `SubscriptionBillingModel` (main billing tracking)
- `SubscriptionFeatureAccess` (feature definitions per tier)
- `BillingHistory` (transaction logging)

### Step 2: Run Migrations

```bash
python manage.py migrate
```

### Step 3: Initialize Billing Records for Existing Companies

Create a data migration to populate `SubscriptionBillingModel` for all existing companies:

```python
# estateApp/migrations/0XXX_initial_billing_records.py

from django.utils import timezone
from datetime import timedelta

def create_billing_records(apps, schema_editor):
    Company = apps.get_model('estateApp', 'Company')
    SubscriptionBillingModel = apps.get_model('estateApp', 'SubscriptionBillingModel')
    SubscriptionPlan = apps.get_model('estateApp', 'SubscriptionPlan')
    
    for company in Company.objects.all():
        if not hasattr(company, 'billing'):
            plan = SubscriptionPlan.objects.get(tier=company.subscription_tier)
            
            billing = SubscriptionBillingModel.objects.create(
                company=company,
                status='trial' if not company.subscription_ends_at else 'active',
                trial_started_at=company.created_at,
                trial_ends_at=company.trial_ends_at or (timezone.now() + timedelta(days=14)),
                current_plan=plan,
                subscription_started_at=company.created_at,
                subscription_ends_at=company.subscription_ends_at,
                monthly_amount=plan.monthly_price,
                annual_amount=plan.annual_price,
            )

def reverse_billing_records(apps, schema_editor):
    SubscriptionBillingModel = apps.get_model('estateApp', 'SubscriptionBillingModel')
    SubscriptionBillingModel.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('estateApp', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.RunPython(create_billing_records, reverse_billing_records),
    ]
```

Run the data migration:
```bash
python manage.py migrate
```

---

## PART 2: UPDATE URLS

Add to `estateApp/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    # ... existing patterns ...
    
    # Subscription Management
    path('admin/company/<slug:company_slug>/subscription/', 
         views.subscription_dashboard, name='subscription_dashboard'),
    path('admin/company/<slug:company_slug>/subscription/upgrade/', 
         views.subscription_upgrade, name='subscription_upgrade'),
    path('admin/company/<slug:company_slug>/subscription/renew/', 
         views.subscription_renew, name='subscription_renew'),
    path('admin/company/<slug:company_slug>/billing/history/', 
         views.billing_history, name='billing_history'),
    path('admin/company/<slug:company_slug>/billing/initiate-payment/', 
         views.initiate_payment, name='initiate_payment'),
    
    # API Endpoints
    path('api/company/<slug:company_slug>/subscription/status/', 
         views.subscription_api_status, name='subscription_api_status'),
]
```

---

## PART 3: UPDATE DJANGO ADMIN

Add to `estateApp/admin.py`:

```python
from django.contrib import admin
from .subscription_billing_models import (
    SubscriptionBillingModel, BillingHistory, SubscriptionFeatureAccess
)

@admin.register(SubscriptionBillingModel)
class SubscriptionBillingAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'status', 'current_plan', 
        'subscription_ends_at', 'auto_renew'
    ]
    list_filter = ['status', 'billing_cycle', 'auto_renew', 'created_at']
    search_fields = ['company__company_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company', {'fields': ('company',)}),
        ('Status', {'fields': ('status', 'warning_level')}),
        ('Trial Period', {
            'fields': ('trial_started_at', 'trial_ends_at'),
            'classes': ('collapse',)
        }),
        ('Subscription', {
            'fields': (
                'current_plan', 'subscription_started_at', 
                'subscription_ends_at', 'billing_cycle', 'auto_renew'
            )
        }),
        ('Grace Period', {
            'fields': ('grace_period_started_at', 'grace_period_ends_at'),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': (
                'last_payment_date', 'payment_method',
                'stripe_subscription_id', 'paystack_subscription_code'
            ),
            'classes': ('collapse',)
        }),
        ('Amounts', {
            'fields': ('monthly_amount', 'annual_amount'),
            'classes': ('collapse',)
        }),
        ('Metadata', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'billing__company', 'amount', 
        'state', 'billing_date'
    ]
    list_filter = ['state', 'transaction_type', 'billing_date']
    search_fields = ['invoice_number', 'billing__company__company_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def billing__company(self, obj):
        return obj.billing.company.company_name

@admin.register(SubscriptionFeatureAccess)
class SubscriptionFeatureAccessAdmin(admin.ModelAdmin):
    list_display = ['plan', 'feature_name', 'is_enabled', 'daily_limit']
    list_filter = ['plan', 'is_enabled']
    search_fields = ['feature_name']
```

---

## PART 4: UPDATE SETTINGS.PY

Add subscription configuration:

```python
# settings.py

# Subscription Settings
SUBSCRIPTION_SETTINGS = {
    'TRIAL_DAYS': 14,
    'GRACE_PERIOD_DAYS': 7,
    'WARNING_THRESHOLDS': {
        'yellow': 7,      # Days before expiry
        'orange': 4,      # Days before expiry
        'red': 2,         # Days before expiry
    },
    'AUTO_RENEW_ENABLED': True,
    'MAX_PAYMENT_RETRIES': 3,
    'PAYMENT_RETRY_INTERVAL_DAYS': 3,
}

# Add Subscription Middleware
MIDDLEWARE = [
    # ... existing middleware ...
    'estateApp.subscription_access.SubscriptionMiddleware',
]

# Add Subscription Context Processor
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # ... existing context processors ...
                'estateApp.subscription_access.subscription_context',
            ],
        },
    },
]
```

---

## PART 5: CREATE TEMPLATE COMPONENTS

### Create `templates/components/subscription_warning_banner.html`:

```html
{% if warning_message %}
<div class="subscription-warning-banner subscription-warning-{{ warning_message.level }}">
    <div class="banner-content">
        <div class="banner-icon">
            <i class="fas {{ warning_message.icon }}"></i>
        </div>
        <div class="banner-text">
            <h5 class="banner-title">{{ warning_message.title }}</h5>
            <p class="banner-message">{{ warning_message.message }}</p>
        </div>
        <div class="banner-actions">
            <button class="btn btn-sm btn-{{ warning_message.level }}" 
                    onclick="handleSubscriptionAction('{{ warning_message.cta_action }}')">
                {{ warning_message.cta }}
            </button>
            <button class="btn btn-sm btn-outline-secondary" 
                    onclick="dismissSubscriptionBanner()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    </div>
</div>

<style>
.subscription-warning-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 20px;
    margin-bottom: 20px;
    border-radius: 8px;
    border-left: 5px solid;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    animation: slideDown 0.3s ease-in-out;
}

.subscription-warning-banner.subscription-warning-yellow {
    background-color: #fff8dc;
    border-color: #ffc107;
}

.subscription-warning-banner.subscription-warning-orange {
    background-color: #ffe8d6;
    border-color: #fd7e14;
}

.subscription-warning-banner.subscription-warning-red {
    background-color: #f8d7da;
    border-color: #dc3545;
}

@keyframes slideDown {
    from { transform: translateY(-20px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}
</style>

<script>
function dismissSubscriptionBanner() {
    document.querySelector('.subscription-warning-banner').style.display = 'none';
}

function handleSubscriptionAction(action) {
    switch(action) {
        case 'upgrade':
            window.location.href = '/admin/company/{{ user_company.slug }}/subscription/upgrade/';
            break;
        case 'renew':
            window.location.href = '/admin/company/{{ user_company.slug }}/subscription/renew/';
            break;
    }
}
</script>
{% endif %}
```

### Create `templates/components/subscription_countdown_modal.html`:

```html
<div class="modal fade" id="subscriptionCountdownModal" tabindex="-1" data-bs-keyboard="false" data-bs-backdrop="static">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Subscription Status</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            
            <div class="modal-body">
                <div class="text-center">
                    <h6>{{ user_company.company_name }}</h6>
                    <p class="text-muted">{{ subscription_status|upper }}</p>
                </div>
                
                <div class="countdown-display">
                    <div class="countdown-section">
                        <span id="countdown-days">00</span>d
                        <span id="countdown-hours">00</span>h
                        <span id="countdown-minutes">00</span>m
                        <span id="countdown-seconds">00</span>s
                    </div>
                </div>
                
                <p class="text-center">Expires: {{ expiration_datetime|date:"M d, Y H:i" }}</p>
            </div>
            
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <a href="{% url 'subscription_renew' user_company.slug %}" class="btn btn-primary">
                    Renew Now
                </a>
            </div>
        </div>
    </div>
</div>

<script>
function updateCountdown() {
    const end = new Date('{{ expiration_datetime|date:"c" }}').getTime();
    const now = new Date().getTime();
    const distance = end - now;
    
    if (distance < 0) return;
    
    const days = Math.floor(distance / (1000*60*60*24));
    const hours = Math.floor((distance % (1000*60*60*24)) / (1000*60*60));
    const minutes = Math.floor((distance % (1000*60*60)) / (1000*60));
    const seconds = Math.floor((distance % (1000*60)) / 1000);
    
    document.getElementById('countdown-days').textContent = String(days).padStart(2, '0');
    document.getElementById('countdown-hours').textContent = String(hours).padStart(2, '0');
    document.getElementById('countdown-minutes').textContent = String(minutes).padStart(2, '0');
    document.getElementById('countdown-seconds').textContent = String(seconds).padStart(2, '0');
}

setInterval(updateCountdown, 1000);
updateCountdown();

{% if should_show_modal %}
document.addEventListener('DOMContentLoaded', function() {
    new bootstrap.Modal(document.getElementById('subscriptionCountdownModal')).show();
});
{% endif %}
</script>
```

### Create `templates/admin/subscription_dashboard.html`:

Create this template in your templates folder to match the structure from `subscription_admin_views.py`

### Create `templates/admin/subscription_upgrade.html`:

Create this template in your templates folder to match the structure from `subscription_admin_views.py`

---

## PART 6: UPDATE VIEWS

Add the views from `subscription_admin_views.py` to your `estateApp/views.py`

---

## PART 7: ADD DECORATORS TO EXISTING VIEWS

Now protect existing views with subscription decorators:

```python
# In estateApp/views.py

from .subscription_access import (
    subscription_required,
    can_create_client_required,
    can_create_allocation_required,
    read_only_if_grace_period,
)

@subscription_required('client_management')
@can_create_client_required
def create_client(request):
    # Existing create client logic
    pass

@subscription_required('allocation')
@can_create_allocation_required
def create_allocation(request):
    # Existing allocation logic
    pass

@read_only_if_grace_period
def edit_property(request, property_id):
    # Existing property edit logic
    pass
```

---

## PART 8: UPDATE BASE TEMPLATE

Add subscription banner to `templates/admin/base.html`:

```html
{% extends 'base.html' %}

{% block content %}
<div class="admin-container">
    <!-- Subscription Warning Banner -->
    {% include 'components/subscription_warning_banner.html' %}
    
    <!-- Subscription Countdown Modal -->
    {% include 'components/subscription_countdown_modal.html' %}
    
    <!-- Existing content -->
    {% block page_content %}{% endblock %}
</div>
{% endblock %}
```

---

## PART 9: CREATE CELERY TASKS (for automated warnings)

Create `estateApp/tasks.py`:

```python
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .subscription_billing_models import SubscriptionBillingModel
from .models import Company

@shared_task
def check_subscription_expiries():
    """Check for subscriptions approaching expiry and send warnings"""
    now = timezone.now()
    
    # Find subscriptions expiring in 7, 4, and 2 days
    for days in [7, 4, 2]:
        expiry_date = now + timedelta(days=days)
        
        billings = SubscriptionBillingModel.objects.filter(
            subscription_ends_at__date=expiry_date.date(),
            status__in=['active', 'trial']
        )
        
        for billing in billings:
            # Send email notification
            send_subscription_warning_email.delay(billing.id, days)

@shared_task
def process_grace_periods():
    """Check for expired subscriptions and start grace periods"""
    now = timezone.now()
    
    # Find just-expired subscriptions
    expired = SubscriptionBillingModel.objects.filter(
        subscription_ends_at__lt=now,
        status='active'
    )
    
    for billing in expired:
        if not billing.is_grace_period():
            billing.start_grace_period()
            send_grace_period_email.delay(billing.id)

@shared_task
def process_grace_period_expirations():
    """Check for grace periods ending and fully expire subscriptions"""
    now = timezone.now()
    
    expired_grace = SubscriptionBillingModel.objects.filter(
        grace_period_ends_at__lt=now,
        status='grace'
    )
    
    for billing in expired_grace:
        billing.status = 'expired'
        billing.save()
        send_subscription_expired_email.delay(billing.id)

@shared_task
def send_subscription_warning_email(billing_id, days_remaining):
    """Send subscription expiry warning email"""
    from django.core.mail import send_mail
    
    billing = SubscriptionBillingModel.objects.get(id=billing_id)
    
    email_templates = {
        7: 'emails/trial_ending_7days.html',
        4: 'emails/trial_ending_4days.html',
        2: 'emails/trial_ending_2days.html',
    }
    
    # Load template and send email
    subject = f"{days_remaining} days left: Upgrade your {billing.company.company_name} subscription"
    # Send email...

# Schedule these tasks in Celery Beat
```

---

## PART 10: TESTING

### Test Checklist

- [ ] Company trial period shows countdown
- [ ] Yellow warning appears 7 days before expiry
- [ ] Orange warning appears 4 days before expiry
- [ ] Red warning appears 2 days before expiry
- [ ] Warning modal opens automatically on red level
- [ ] "Renew Now" button is clickable
- [ ] Grace period activates after expiry
- [ ] Read-only mode enforced during grace period
- [ ] Features hidden/disabled when expired
- [ ] API returns correct subscription status
- [ ] Dashboard shows usage metrics
- [ ] Upgrade plan changes subscription tier
- [ ] Billing history displays transactions

### Test Script

```python
# management/commands/test_subscription_lifecycle.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from estateApp.models import Company, SubscriptionPlan
from estateApp.subscription_billing_models import SubscriptionBillingModel

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Create test company
        company = Company.objects.create(
            company_name="Test Subscription Lifecycle",
            subscription_tier="professional"
        )
        
        # Create billing record
        plan = SubscriptionPlan.objects.get(tier="professional")
        billing = SubscriptionBillingModel.objects.create(
            company=company,
            status='trial',
            trial_ends_at=timezone.now() + timedelta(days=7),
            current_plan=plan,
        )
        
        # Test warning levels
        print("Testing warning system:")
        print(f"Days remaining: {billing.get_days_remaining()}")
        print(f"Warning level: {billing.get_warning_level()}")
        print(f"Warning message: {billing.get_warning_message()}")
        
        # Test status changes
        print("\nTesting status transitions:")
        billing.subscription_ends_at = timezone.now() - timedelta(days=1)
        billing.save()
        billing.refresh_status()
        print(f"Status: {billing.status}")
        
        # Test grace period
        billing.start_grace_period()
        print(f"Grace period status: {billing.status}")
        print(f"Grace period ends: {billing.grace_period_ends_at}")
```

---

## PART 11: DEPLOYMENT CHECKLIST

- [ ] Create migration files
- [ ] Run migrations on staging
- [ ] Create/update Django admin
- [ ] Add URLs to urls.py
- [ ] Update settings.py
- [ ] Create template components
- [ ] Update base template
- [ ] Add decorators to views
- [ ] Test all views and decorators
- [ ] Set up Celery tasks
- [ ] Test on staging environment
- [ ] Create backup of production database
- [ ] Deploy to production
- [ ] Monitor error logs
- [ ] Verify all features working

---

## PART 12: TROUBLESHOOTING

### Issue: Modal not showing
- Check `should_show_modal` variable in context
- Verify Bootstrap modal JavaScript is loaded
- Check browser console for JS errors

### Issue: Warning banner not appearing
- Verify middleware is in MIDDLEWARE setting
- Check context processor is registered
- Ensure subscription data is in database

### Issue: Countdown timer not updating
- Verify JavaScript timer code
- Check browser timezone settings
- Ensure expirationdatetime is correctly formatted

### Issue: Features still accessible in grace period
- Verify read_only_if_grace_period decorator is applied
- Check that billing.refresh_status() is called
- Check request.method in middleware

---

## NEXT STEPS

1. Follow this guide step-by-step
2. Test each section as you implement
3. Deploy to staging first
4. Get user feedback
5. Deploy to production
6. Continue to Phase 3 (Payment Integration)

**Contact Support**: For issues implementing this phase, provide:
- Error message from logs
- Which step you're on
- What you've already tried
