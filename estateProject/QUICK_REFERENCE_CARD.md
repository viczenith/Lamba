# Quick Reference Card - Subscription System Phase 2

## 📋 Files You Need to Know

```
Python Files (Copy to estateApp/):
├── subscription_billing_models.py      (638 lines) - Models
├── subscription_ui_templates.py        (780 lines) - Templates & UI
├── subscription_admin_views.py         (480 lines) - Views
└── subscription_access.py              (420 lines) - Decorators

Documentation Files (Read):
├── PHASE2_DELIVERY_SUMMARY.md         (Overview - START HERE)
├── BILLING_SUBSCRIPTION_STRATEGY.md   (Strategy - READ BEFORE IMPLEMENTING)
├── PHASE2_IMPLEMENTATION_GUIDE.md     (Steps - FOLLOW DURING IMPLEMENTATION)
└── SUBSCRIPTION_ARCHITECTURE_DIAGRAMS.md (Design - REFERENCE)

This File:
└── SUBSCRIPTION_SYSTEM_INDEX.md       (This comprehensive index)
```

---

## ⚡ 15-Minute Quick Start

```bash
# Step 1: Copy Python files
cp subscription_billing_models.py estateApp/
cp subscription_ui_templates.py estateApp/
cp subscription_admin_views.py estateApp/
cp subscription_access.py estateApp/

# Step 2: Create migration
python manage.py makemigrations estateApp

# Step 3: Run migration
python manage.py migrate

# Step 4: Update settings.py (copy from guide)
# - Add SubscriptionMiddleware to MIDDLEWARE
# - Add subscription_context to context_processors

# Step 5: Update urls.py (copy patterns from views)
# - Add subscription routes

# Step 6: Create template components (copy HTML from templates.py)
# - templates/components/subscription_warning_banner.html
# - templates/components/subscription_countdown_modal.html

# Step 7: Test
python manage.py runserver
# Visit: http://localhost:8000/admin/company/<slug>/subscription/
```

---

## 🎯 What Each File Does

| File | Lines | Purpose | Copy To |
|------|-------|---------|---------|
| subscription_billing_models.py | 638 | Main models | estateApp/ |
| subscription_ui_templates.py | 780 | UI templates | estateApp/ |
| subscription_admin_views.py | 480 | Django views | estateApp/ |
| subscription_access.py | 420 | Decorators & middleware | estateApp/ |

---

## 📊 Key Models

### SubscriptionBillingModel
```python
# Main billing tracking model
company              # OneToOne to Company
status               # 'trial', 'active', 'grace', 'suspended', 'cancelled', 'expired'
trial_ends_at        # DateTime
subscription_ends_at # DateTime
current_plan         # ForeignKey to SubscriptionPlan
billing_cycle        # 'monthly' or 'annual'
auto_renew           # Boolean
monthly_amount       # Decimal
annual_amount        # Decimal
```

**Key Methods**:
```python
billing.refresh_status()          # Update status based on dates
billing.is_active()               # Check if subscription active
billing.is_grace_period()         # Check if in grace period
billing.get_warning_level()       # 0=Green, 1=Yellow, 2=Orange, 3=Red
billing.get_warning_message()     # Dict with warning details
billing.get_days_remaining()      # Int: days until expiry
billing.start_grace_period()      # Activate grace period
billing.get_access_restrictions() # Dict of what's allowed
```

### BillingHistory
```python
# Transaction tracking
billing              # ForeignKey to SubscriptionBillingModel
transaction_type     # 'charge', 'refund', 'proration', 'adjustment'
state                # 'pending', 'completed', 'failed', 'cancelled'
amount               # Decimal
invoice_number       # String (unique)
transaction_id       # String (from payment gateway)
paid_date            # DateTime
```

---

## 🔌 Integration Points

### 1. Settings.py
```python
# Add Middleware
MIDDLEWARE = [
    # ... existing ...
    'estateApp.subscription_access.SubscriptionMiddleware',
]

# Add Context Processor
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            # ... existing ...
            'estateApp.subscription_access.subscription_context',
        ],
    },
}]
```

### 2. urls.py
```python
from estateApp import views

urlpatterns = [
    # ... existing ...
    path('admin/company/<slug:company_slug>/subscription/', 
         views.subscription_dashboard, name='subscription_dashboard'),
    path('admin/company/<slug:company_slug>/subscription/upgrade/', 
         views.subscription_upgrade, name='subscription_upgrade'),
    # ... more patterns in PHASE2_IMPLEMENTATION_GUIDE.md
]
```

### 3. base.html Template
```html
{% extends 'base.html' %}

{% block content %}
    <!-- Subscription Warning Banner -->
    {% include 'components/subscription_warning_banner.html' %}
    
    <!-- Subscription Countdown Modal -->
    {% include 'components/subscription_countdown_modal.html' %}
    
    <!-- Your existing content -->
    {% block page_content %}{% endblock %}
{% endblock %}
```

### 4. Protect Existing Views
```python
from .subscription_access import (
    subscription_required,
    can_create_client_required,
    can_create_allocation_required,
    read_only_if_grace_period,
)

@subscription_required('clients')
@can_create_client_required
def create_client(request):
    # Your code
    pass

@read_only_if_grace_period
def edit_property(request, property_id):
    # Your code
    pass
```

---

## 🚨 Warning Levels

| Level | Days | Banner | Modal | Email |
|-------|------|--------|-------|-------|
| 0 | >7 | ✗ | ✗ | ✗ |
| 1 (Yellow) | 4-7 | ✓ | ✗ | Daily |
| 2 (Orange) | 2-4 | ✓ | ✓ | 6-hourly |
| 3 (Red) | <2 | ✓ | ✓ | 2-hourly |

---

## 🔄 Subscription States

```
TRIAL (14 days)
  ├─ Full access
  ├─ No payment required
  └─ Transitions to: ACTIVE or EXPIRED

ACTIVE (Paid)
  ├─ Full access
  ├─ Recurring payment
  └─ Transitions to: GRACE_PERIOD or EXPIRED

GRACE_PERIOD (7 days after expiry)
  ├─ Read-only access
  ├─ Features disabled
  └─ Transitions to: ACTIVE or EXPIRED

EXPIRED
  ├─ No access (except read historical)
  ├─ Must renew
  └─ Transitions to: ACTIVE

SUSPENDED (Payment failure)
  ├─ No access
  ├─ Manual recovery needed
  └─ Transitions to: ACTIVE (admin action)

CANCELLED (User quit)
  ├─ Dashboard read-only
  ├─ No features
  └─ Can reactivate manually
```

---

## 💾 Database Migration

```bash
# Create migration
python manage.py makemigrations estateApp

# Run migration
python manage.py migrate

# To populate existing companies (see guide for data migration):
python manage.py shell
# Then create SubscriptionBillingModel records for each Company
```

---

## 📱 Template Context Variables

**Automatically Available in Templates** (after adding context processor):

```html
{{ user_subscription }}         {# SubscriptionBillingModel instance #}
{{ is_trial }}                  {# Boolean #}
{{ is_active }}                 {# Boolean #}
{{ is_grace_period }}           {# Boolean #}
{{ is_expired }}                {# Boolean #}
{{ warning_message }}           {# Dict with title, message, cta #}
{{ days_remaining }}            {# Integer #}
{{ should_show_warning }}       {# Boolean #}
{{ subscription_status }}       {# String #}
{{ user_company }}              {# Company instance #}
```

---

## 🎨 CSS Classes

**Warning Banner**:
```css
.subscription-warning-banner                    /* Main container */
.subscription-warning-banner.subscription-warning-yellow
.subscription-warning-banner.subscription-warning-orange
.subscription-warning-banner.subscription-warning-red
```

**Countdown Display**:
```css
.countdown-display                              /* Container */
.countdown-display.countdown-yellow
.countdown-display.countdown-orange
.countdown-display.countdown-red
.countdown-unit                                 /* Individual unit #}
.countdown-number                               /* Number value */
```

**Status Badge**:
```css
.status-badge.status-trial
.status-badge.status-active
.status-badge.status-grace
.status-badge.status-expired
```

---

## 🔗 URL Routes

```
/admin/company/<slug>/subscription/             → Dashboard
/admin/company/<slug>/subscription/upgrade/     → Upgrade plans
/admin/company/<slug>/subscription/renew/       → Renewal form
/admin/company/<slug>/billing/history/          → Invoice history
/admin/company/<slug>/billing/initiate-payment/ → Payment form
/api/company/<slug>/subscription/status/        → API status (JSON)
```

---

## 🧪 Testing Checklist

```
Functionality:
- [ ] Warning banner appears at correct times
- [ ] Countdown modal shows correct countdown
- [ ] Grace period activates after expiry
- [ ] Read-only mode enforces during grace period
- [ ] Features disabled when expired
- [ ] Upgrade path works
- [ ] Renewal path works
- [ ] Billing history displays
- [ ] API endpoint returns correct status

Responsive:
- [ ] Desktop (1920px)
- [ ] Tablet (768px)
- [ ] Mobile (375px)

Browsers:
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Edge

Edge Cases:
- [ ] Company with no billing record (create on demand)
- [ ] User with no company (gracefully handle)
- [ ] Expired >7 days ago (should be expired)
- [ ] Exactly at expiry moment (test boundary)
```

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| ImportError: No module 'subscription_billing_models' | File not copied | Copy file to estateApp/ |
| Migration errors | Models not imported | Check apps.py default_auto_field |
| Middleware error on request | Middleware placed wrong | Check MIDDLEWARE order |
| Context not in template | Processor not added | Add to TEMPLATES context_processors |
| Timer not updating | Bootstrap not loaded | Verify Bootstrap 5.3 script tag |
| Decorator not working | Not imported | Add to imports at top of views.py |
| Grace period not enforcing | refresh_status() not called | Call in middleware (done automatically) |

---

## 📞 Where to Find Things

| I Need... | Look In... |
|-----------|-----------|
| Business logic | BILLING_SUBSCRIPTION_STRATEGY.md |
| Implementation steps | PHASE2_IMPLEMENTATION_GUIDE.md |
| Architecture details | SUBSCRIPTION_ARCHITECTURE_DIAGRAMS.md |
| Code structure | subscription_billing_models.py |
| Template HTML | subscription_ui_templates.py |
| View code | subscription_admin_views.py |
| Decorators | subscription_access.py |
| Quick start | PHASE2_DELIVERY_SUMMARY.md |
| Troubleshooting | PHASE2_IMPLEMENTATION_GUIDE.md (end) |

---

## ✅ Pre-Flight Checklist

Before going to production:

- [ ] Read all documentation
- [ ] Copied 4 Python files
- [ ] Created and ran migrations
- [ ] Updated settings.py
- [ ] Updated urls.py
- [ ] Created template components
- [ ] Added includes to base template
- [ ] Added decorators to views
- [ ] Tested all views locally
- [ ] Tested on mobile
- [ ] Deployed to staging
- [ ] Full test suite on staging
- [ ] Backed up production database
- [ ] Deployed to production
- [ ] Monitored logs for errors

---

## 🚀 Success Signals

**You'll know it's working when**:

1. ✅ Dashboard shows subscription status
2. ✅ Warning banner appears automatically
3. ✅ Countdown timer updates every second
4. ✅ Modal shows on warning level 3
5. ✅ Grace period activates after expiry
6. ✅ Features are disabled when expired
7. ✅ No errors in Django logs
8. ✅ Mobile views are responsive
9. ✅ API returns correct status

---

## 📈 Key Metrics to Monitor

```
After Deployment:

Performance:
- Middleware response time < 5ms
- Dashboard load time < 1s
- Modal rendering < 100ms

Errors:
- No migration errors
- No 500 errors in logs
- No JavaScript console errors

Usage:
- Track warning banner impressions
- Track modal open rate
- Track renewal click-through rate
- Track upgrade conversion rate
```

---

## 🎓 How to Use This Card

1. **Before Implementation**: Skim entire card
2. **During Implementation**: Reference specific sections
3. **For Quick Lookups**: Use tables and quick code snippets
4. **For Troubleshooting**: Check "Common Issues & Fixes"
5. **For Testing**: Use "Testing Checklist"

---

## 💪 You're Ready When

- [x] You've read PHASE2_DELIVERY_SUMMARY.md
- [x] You've scanned BILLING_SUBSCRIPTION_STRATEGY.md
- [x] You understand the 6 subscription states
- [x] You know what the 3 Python files do
- [x] You have your Django environment ready
- [x] You have a backup of your database

**Then**: Follow PHASE2_IMPLEMENTATION_GUIDE.md step-by-step

---

## 📝 Keep This Handy

This quick reference card is designed to be:
- ✅ Printable (fits on 2-3 pages)
- ✅ Scannable (use headers to find sections)
- ✅ Concise (only essential info)
- ✅ Comprehensive (covers all bases)

Refer back to detailed docs when you need more info.

---

**Phase 2 Subscription System - Ready to Deploy** ✨

Good luck! Start with PHASE2_DELIVERY_SUMMARY.md 🚀
