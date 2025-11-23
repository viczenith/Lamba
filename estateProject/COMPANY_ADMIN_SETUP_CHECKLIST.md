# Company Admin Subscription Integration - Setup Checklist

## ✅ Quick Integration Guide

All subscription and billing features are now **fully integrated into the Company Admin's Company Profile page**.

---

## 📋 What Was Implemented

### ✅ Frontend (company_profile.html)
- New "Subscription & Billing" tab in company profile navigation
- Subscription overview card with status and dates
- Feature access matrix showing enabled/disabled features
- Usage metrics dashboard (properties, clients, marketers)
- Billing history table with recent transactions
- 4 interactive modals:
  - Select Plan (for new subscriptions)
  - Upgrade Plan (for plan upgrades)
  - Renew Subscription (for renewals)
  - Payment (Stripe/Paystack payment processing)

### ✅ Backend (subscription_views.py)
- API endpoints for plans and subscription status
- Subscription management views (renew, upgrade)
- Payment processing views (Stripe, Paystack)
- Billing history and invoice download views
- Context preparation for templates

### ✅ URL Configuration (subscription_admin_urls.py)
- 9 URL patterns for all subscription operations
- Both API and admin endpoints
- Organized and well-documented

### ✅ Supporting Files
- `subscription_billing_models.py` - Database models
- `subscription_access.py` - Decorators and middleware
- `payment_integration.py` - Payment gateway integration
- `email_notifications.py` - Email automation

---

## 🚀 Setup Steps

### Step 1: Update Main URLs
**File**: `estateProject/urls.py`

Add this import:
```python
from django.urls import path, include
```

Add to `urlpatterns`:
```python
path('', include('estateApp.subscription_admin_urls')),
```

### Step 2: Update Company Profile View
**File**: `estateApp/views.py` (or wherever company_profile view is)

Find the company_profile view and update context:
```python
from .subscription_views import subscription_context_for_company_profile

# Inside company_profile view
context = {
    'company': company,
    # ... existing context variables ...
}
# Add subscription context
context.update(subscription_context_for_company_profile(request, company))
```

### Step 3: Ensure Models Are Registered
**File**: `estateApp/models.py`

Add these imports at the top:
```python
from .subscription_billing_models import (
    SubscriptionBillingModel,
    BillingHistory,
    SubscriptionFeatureAccess
)
```

### Step 4: Create SubscriptionPlan Records
Run Django shell and create plans:
```bash
python manage.py shell
```

```python
from estateApp.models import SubscriptionPlan

# Create Free plan
SubscriptionPlan.objects.create(
    name='Free',
    price=0,
    properties_limit=5,
    users_limit=2,
    marketers_limit=0,
    has_analytics=False,
    description='Perfect for getting started'
)

# Create Starter plan
SubscriptionPlan.objects.create(
    name='Starter',
    price=5000,
    properties_limit=20,
    users_limit=5,
    marketers_limit=2,
    has_analytics=True,
    description='For growing businesses'
)

# Create Pro plan
SubscriptionPlan.objects.create(
    name='Pro',
    price=15000,
    properties_limit=100,
    users_limit=25,
    marketers_limit=10,
    has_analytics=True,
    description='For professional teams'
)

# Create Enterprise plan
SubscriptionPlan.objects.create(
    name='Enterprise',
    price=50000,
    properties_limit=None,  # Unlimited
    users_limit=None,  # Unlimited
    marketers_limit=None,  # Unlimited
    has_analytics=True,
    description='Custom solutions'
)
```

### Step 5: Configure Environment Variables
**File**: `.env`

```env
# Payment Gateway Configuration
STRIPE_PUBLIC_KEY=pk_test_your_key_here
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_WEBHOOK_SECRET=whsec_test_your_secret_here

PAYSTACK_PUBLIC_KEY=pk_test_your_key_here
PAYSTACK_SECRET_KEY=sk_test_your_key_here
PAYSTACK_WEBHOOK_SECRET=your_webhook_secret_here
```

### Step 6: Update Settings.py
**File**: `estateProject/settings.py`

Add these settings:
```python
import os
from decouple import config

# Payment Gateway Keys
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_WEBHOOK_SECRET = config('PAYSTACK_WEBHOOK_SECRET', default='')

# Subscription Settings
SUBSCRIPTION_GRACE_PERIOD_DAYS = 7
SUBSCRIPTION_TRIAL_DAYS = 14
```

### Step 7: Run Migrations
```bash
python manage.py makemigrations estateApp
python manage.py migrate estateApp
```

### Step 8: Verify Installation
1. Go to company admin profile
2. Look for "Subscription & Billing" tab
3. Click tab and verify it loads
4. Check that plans appear in the UI

---

## 📱 How Company Admins Use It

### View Subscription Status
1. Login as company admin
2. Go to Company Console (company profile)
3. Click "Subscription & Billing" tab
4. See current subscription overview

### Select First Plan
1. If no subscription exists, click "Select a Plan"
2. Choose desired plan
3. Click "Select Plan"
4. Choose payment method (Stripe or Paystack)
5. Complete payment
6. Subscription activated

### Renew Subscription
1. When subscription nearing expiry (warning banner shown)
2. Click "Renew Subscription"
3. Choose payment method
4. Click "Proceed to Payment"
5. Complete payment
6. Subscription extended

### Upgrade Plan
1. To upgrade to higher tier, click "Upgrade Plan"
2. Choose new plan (only higher tiers available)
3. Pay difference (if applicable)
4. New plan activated immediately

### View Billing History
1. Scroll down to "Recent Transactions"
2. See all payment history
3. Click invoice to download PDF (when implemented)

---

## 🔗 File References

| File | Purpose | Location |
|------|---------|----------|
| company_profile.html | Main UI template | `estateApp/templates/admin_side/` |
| subscription_views.py | Backend views | `estateApp/` |
| subscription_admin_urls.py | URL routing | `estateApp/` |
| subscription_billing_models.py | Database models | `estateApp/` |
| subscription_access.py | Access control | `estateApp/` |
| payment_integration.py | Payment gateways | `estateApp/` |
| email_notifications.py | Email automation | `estateApp/` |
| COMPANY_ADMIN_SUBSCRIPTION_INTEGRATION.md | Full documentation | Project root |

---

## ✅ Verification Checklist

- [ ] Main urls.py includes subscription_admin_urls
- [ ] company_profile view passes subscription context
- [ ] SubscriptionPlan records created in database
- [ ] Environment variables configured in .env
- [ ] Settings.py updated with payment keys
- [ ] Database migrations run successfully
- [ ] Payment gateways configured (Stripe/Paystack)
- [ ] Email backend configured
- [ ] CSRF token in templates
- [ ] Bootstrap 5.3 loaded in base template

---

## 🧪 Quick Test

### Test Plan Loading
```bash
# Access the plans API
curl http://localhost:8000/api/plans/
```

Should return JSON with all plans.

### Test in Browser
1. Start Django server: `python manage.py runserver`
2. Login as company admin
3. Go to company profile
4. Click "Subscription & Billing" tab
5. Verify data loads without errors

---

## 🎯 Key Features Ready to Use

✅ **Subscription Overview** - See current plan and status  
✅ **Plan Selection** - Choose from available plans  
✅ **Renewal System** - Automatically extend subscriptions  
✅ **Upgrade Path** - Upgrade to higher tier plans  
✅ **Feature Matrix** - View included/excluded features  
✅ **Usage Metrics** - See current usage against limits  
✅ **Billing History** - Complete transaction history  
✅ **Payment Processing** - Stripe and Paystack integration  
✅ **Email Notifications** - Automatic emails on events  
✅ **Grace Period** - 7-day read-only access after expiry  
✅ **Warning System** - 4-level warning badges  
✅ **Access Control** - Feature restrictions by plan  

---

## 🚨 Important Notes

1. **Test Mode**: Use Stripe/Paystack test keys for development
2. **Currency**: System uses NGN (Nigerian Naira) - update if needed
3. **Email**: Configure SMTP backend in settings.py
4. **Redis**: Optional but recommended for Celery tasks
5. **Webhooks**: Configure in payment provider dashboards

---

## 📞 Support

For issues or questions:
1. Check COMPANY_ADMIN_SUBSCRIPTION_INTEGRATION.md for full docs
2. Review error logs in Django console
3. Check browser console for JavaScript errors
4. Verify all configuration in .env and settings.py

---

**Status**: ✅ Ready for Integration  
**Date**: November 22, 2024  
**Version**: 1.0
