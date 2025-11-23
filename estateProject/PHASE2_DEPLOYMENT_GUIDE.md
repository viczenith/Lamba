# Phase 2 Subscription System - Complete Deployment Guide

## 📋 Overview

This guide provides step-by-step instructions to deploy the complete Phase 2 subscription system including grace periods, warning banners, countdown modals, billing dashboards, and payment integration.

**Total Components**: 12 files  
**Code Lines**: 3,400+  
**Documentation**: 5,200+ lines  
**Deployment Time**: ~2-3 hours  

---

## 🗂️ File Structure

### Core Models & Database
```
estateApp/
├── subscription_billing_models.py (638 lines)
│   ├── SubscriptionBillingModel
│   ├── BillingHistory
│   └── SubscriptionFeatureAccess
└── models.py (update existing)
```

### Views & Controllers
```
estateApp/
├── subscription_admin_views.py (480 lines)
│   ├── subscription_dashboard
│   ├── subscription_upgrade
│   ├── subscription_renew
│   ├── subscription_history
│   ├── subscription_api
│   └── payment_webhook_handlers
└── payment_integration.py (450+ lines)
    ├── StripePaymentProcessor
    ├── PaystackPaymentProcessor
    └── Webhook handlers
```

### Templates & UI
```
templates/
├── subscription/
│   ├── billing_dashboard.html
│   ├── upgrade_modal.html
│   ├── renewal_modal.html
│   ├── payment_form.html
│   └── email/
│       ├── trial_ending_7days.html
│       ├── trial_ending_2days.html
│       ├── grace_period_active.html
│       ├── subscription_expired.html
│       ├── subscription_renewed.html
│       ├── upgrade_confirmation.html
│       ├── invoice.html
│       ├── payment_failed.html
│       └── refund_processed.html
```

### Utilities & Middleware
```
estateApp/
├── subscription_access.py (420 lines)
│   ├── Decorators
│   ├── SubscriptionMiddleware
│   └── Context processors
└── email_notifications.py (450+ lines)
    ├── SubscriptionEmailNotifications
    └── Celery tasks
```

---

## 🚀 Deployment Steps

### Step 1: Install Required Packages

```bash
pip install stripe paystack celery redis python-decouple
```

**Requirements.txt additions**:
```
stripe==5.4.0
paystack==2.0.0
celery==5.3.0
redis==4.5.0
python-decouple==3.8
```

### Step 2: Create Database Models

#### 2.1 Copy Model Files
```bash
# Copy subscription_billing_models.py to estateApp/
cp subscription_billing_models.py estateApp/
```

#### 2.2 Update `estateApp/models.py`
Add imports at the top:
```python
from .subscription_billing_models import (
    SubscriptionBillingModel,
    BillingHistory,
    SubscriptionFeatureAccess
)
```

#### 2.3 Create & Run Migrations
```bash
# From project root
python manage.py makemigrations estateApp
python manage.py migrate estateApp
```

**Migration SQL** (if needed for manual verification):
```sql
-- Will auto-create 3 new tables:
-- estateApp_subscriptionbillingmodel
-- estateApp_billinghistory
-- estateApp_subscriptionfeatureaccess
```

### Step 3: Configure Settings

#### 3.1 Environment Variables (`.env` file)
```env
# Subscription Settings
SUBSCRIPTION_GRACE_PERIOD_DAYS=7
SUBSCRIPTION_TRIAL_DAYS=14
SUBSCRIPTION_WARNING_DAYS=[7,4,2]

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxxxxxxxxxxx

# Paystack Configuration
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxx
PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxx
PAYSTACK_WEBHOOK_SECRET=xxxxxxxxxxxx

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@lamba.com
SUPPORT_EMAIL=support@lamba.com

# Site Configuration
SITE_URL=https://yourdomain.com
SITE_NAME=LAMBA

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
```

#### 3.2 Update `settings.py`
```python
import os
from decouple import config

# ========== Subscription Configuration ==========
SUBSCRIPTION_GRACE_PERIOD_DAYS = config('SUBSCRIPTION_GRACE_PERIOD_DAYS', default=7, cast=int)
SUBSCRIPTION_TRIAL_DAYS = config('SUBSCRIPTION_TRIAL_DAYS', default=14, cast=int)
SUBSCRIPTION_WARNING_DAYS = [7, 4, 2]  # Send warnings at these days before expiry

# ========== Payment Gateway Configuration ==========
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', '')

PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', '')
PAYSTACK_WEBHOOK_SECRET = config('PAYSTACK_WEBHOOK_SECRET', '')

# ========== Email Configuration ==========
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', 587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', 'true') == 'true'
EMAIL_HOST_USER = config('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', 'noreply@lamba.com')
SUPPORT_EMAIL = config('SUPPORT_EMAIL', 'support@lamba.com')

# ========== Site Configuration ==========
SITE_URL = config('SITE_URL', 'https://localhost:8000')
SITE_NAME = config('SITE_NAME', 'LAMBA')

# ========== Celery Configuration ==========
CELERY_BROKER_URL = config('CELERY_BROKER_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'send_subscription_warnings': {
        'task': 'estateApp.email_notifications.send_subscription_warnings',
        'schedule': crontab(hour=9, minute=0),
    },
    'activate_grace_periods': {
        'task': 'estateApp.email_notifications.activate_grace_periods',
        'schedule': crontab(minute=0),
    },
    'expire_grace_periods': {
        'task': 'estateApp.email_notifications.expire_grace_periods',
        'schedule': crontab(hour=0, minute=0),
    },
    'send_grace_period_reminders': {
        'task': 'estateApp.email_notifications.send_grace_period_reminders',
        'schedule': crontab(hour=15, minute=0),
    },
}

# ========== Middleware ==========
MIDDLEWARE = [
    # ... existing middleware ...
    'estateApp.subscription_access.SubscriptionMiddleware',
]

# ========== Template Context Processors ==========
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # ... existing processors ...
                'estateApp.subscription_access.subscription_context_processor',
            ],
        },
    },
]

# ========== Installed Apps ==========
INSTALLED_APPS = [
    # ... existing apps ...
    'estateApp',
    'rest_framework',
    'corsheaders',
]
```

### Step 4: Copy Files to Django App

```bash
# From project root, copy all files
cp subscription_admin_views.py estateApp/
cp subscription_access.py estateApp/
cp payment_integration.py estateApp/
cp email_notifications.py estateApp/
cp subscription_ui_templates.py estateApp/
```

### Step 5: Update URL Routing

#### 5.1 Create `estateApp/subscription_urls.py`
```python
from django.urls import path
from . import subscription_admin_views, payment_integration

urlpatterns = [
    # Subscription Management
    path('admin/company/<slug:company_slug>/subscription/', 
         subscription_admin_views.subscription_dashboard, 
         name='subscription_dashboard'),
    
    path('admin/company/<slug:company_slug>/subscription/upgrade/', 
         subscription_admin_views.subscription_upgrade, 
         name='subscription_upgrade'),
    
    path('admin/company/<slug:company_slug>/subscription/renew/', 
         subscription_admin_views.subscription_renew, 
         name='subscription_renew'),
    
    path('admin/company/<slug:company_slug>/subscription/history/', 
         subscription_admin_views.subscription_history, 
         name='subscription_history'),
    
    # API Endpoint
    path('api/subscription/<slug:company_slug>/status/', 
         subscription_admin_views.subscription_api, 
         name='subscription_api'),
    
    # Payment Processing
    path('payment/stripe/create/', 
         payment_integration.create_stripe_payment, 
         name='create_stripe_payment'),
    
    path('payment/stripe/webhook/', 
         payment_integration.stripe_webhook, 
         name='stripe_webhook'),
    
    path('payment/paystack/create/', 
         payment_integration.create_paystack_payment, 
         name='create_paystack_payment'),
    
    path('payment/paystack/webhook/', 
         payment_integration.paystack_webhook, 
         name='paystack_webhook'),
]
```

#### 5.2 Update Main `urls.py`
```python
# In your main project urls.py
from django.urls import path, include

urlpatterns = [
    # ... existing patterns ...
    path('', include('estateApp.subscription_urls')),
]
```

### Step 6: Create Email Templates

Create directory: `templates/emails/`

Each template should extend `base_email.html`:

```html
<!-- templates/base_email.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; }
        .email-container { max-width: 600px; margin: 0 auto; }
        .header { background-color: #2c3e50; color: white; padding: 20px; }
        .content { padding: 20px; }
        .cta-button { 
            display: inline-block; 
            background-color: #007bff; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 4px;
        }
        .urgency-critical { color: #dc3545; }
        .urgency-high { color: #fd7e14; }
        .urgency-medium { color: #ffc107; }
        .urgency-low { color: #28a745; }
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>{{ site_name }}</h1>
        </div>
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        <div class="footer" style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
            <p>© {{ current_year }} {{ site_name }}. All rights reserved.</p>
            <p>{{ support_email }}</p>
        </div>
    </div>
</body>
</html>
```

Create individual email templates (see `email_notifications.py` for specific templates needed).

### Step 7: Set Up Celery

#### 7.1 Create `estateProject/celery.py`
```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')

app = Celery('estateProject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

#### 7.2 Update `estateProject/__init__.py`
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

#### 7.3 Start Celery Worker & Beat
```bash
# Terminal 1 - Celery Worker
celery -A estateProject worker -l info

# Terminal 2 - Celery Beat (Scheduler)
celery -A estateProject beat -l info
```

### Step 8: Set Up Redis (if not already running)

#### 8.1 Install Redis
```bash
# Windows (using WSL or Docker)
docker run -d -p 6379:6379 redis:latest

# Or use Windows native installer
# Download from: https://github.com/microsoftarchive/redis/releases
```

#### 8.2 Verify Redis Connection
```bash
redis-cli ping
# Should return: PONG
```

### Step 9: Register Django Admin

Update `estateApp/admin.py`:

```python
from django.contrib import admin
from .subscription_billing_models import (
    SubscriptionBillingModel,
    BillingHistory,
    SubscriptionFeatureAccess
)

@admin.register(SubscriptionBillingModel)
class SubscriptionBillingModelAdmin(admin.ModelAdmin):
    list_display = ('company', 'subscription_plan', 'status', 'subscription_ends_at')
    list_filter = ('status', 'subscription_plan', 'subscription_starts_at')
    search_fields = ('company__company_name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Subscription Info', {
            'fields': ('company', 'subscription_plan', 'status')
        }),
        ('Dates', {
            'fields': ('subscription_starts_at', 'subscription_ends_at', 'grace_period_ends_at')
        }),
        ('Payment', {
            'fields': ('amount', 'payment_method', 'transaction_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'transaction_type', 'amount', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('subscription__company__company_name',)
    readonly_fields = ('created_at',)

@admin.register(SubscriptionFeatureAccess)
class SubscriptionFeatureAccessAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'feature_name', 'is_enabled')
    list_filter = ('is_enabled', 'subscription__subscription_plan')
    search_fields = ('feature_name',)
```

### Step 10: Update Company Model

Add these fields to the `Company` model in `estateApp/models.py`:

```python
class Company(models.Model):
    # ... existing fields ...
    
    # Subscription relationship
    subscription = models.OneToOneField(
        'SubscriptionBillingModel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='company_subscription'
    )
    
    # Grace period flags
    in_grace_period = models.BooleanField(default=False)
    grace_period_warning_sent = models.BooleanField(default=False)
    
    def get_subscription_status(self):
        """Get current subscription status"""
        if hasattr(self, 'subscription') and self.subscription:
            return self.subscription.get_current_status()
        return 'no_subscription'
    
    def can_access_features(self):
        """Check if company can access paid features"""
        if hasattr(self, 'subscription') and self.subscription:
            return self.subscription.can_create_client()
        return False
```

Then run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 11: Configure Payment Webhooks

#### 11.1 Stripe Webhook
1. Go to: https://dashboard.stripe.com/webhooks
2. Create new endpoint
3. URL: `https://yourdomain.com/payment/stripe/webhook/`
4. Events: `payment_intent.succeeded`, `payment_intent.payment_failed`
5. Copy webhook secret to `.env` as `STRIPE_WEBHOOK_SECRET`

#### 11.2 Paystack Webhook
1. Go to: https://dashboard.paystack.com/settings/webhooks
2. Create new webhook
3. URL: `https://yourdomain.com/payment/paystack/webhook/`
4. Events: `charge.success`, `charge.failed`
5. Copy webhook secret to `.env` as `PAYSTACK_WEBHOOK_SECRET`

### Step 12: Test the System

#### 12.1 Create Test Company
```bash
python manage.py shell
```

```python
from estateApp.models import Company, SubscriptionPlan
from estateApp.subscription_billing_models import SubscriptionBillingModel
from django.utils import timezone
from datetime import timedelta

# Create test company (if not exists)
company = Company.objects.get_or_create(
    company_name='Test Company',
    defaults={
        'company_code': 'TEST001',
        'admin': User.objects.first(),
    }
)[0]

# Create subscription
plan = SubscriptionPlan.objects.get(name='pro')
subscription = SubscriptionBillingModel.objects.create(
    company=company,
    subscription_plan=plan,
    subscription_starts_at=timezone.now(),
    subscription_ends_at=timezone.now() + timedelta(days=30),
    amount=plan.price,
    status='active',
    payment_method='stripe'
)

print(f"Created subscription: {subscription}")
print(f"Status: {subscription.get_current_status()}")
print(f"Warning Level: {subscription.get_warning_level()}")
```

#### 12.2 Test Emails
```bash
# Send test warning email
python manage.py shell
from estateApp.email_notifications import SubscriptionEmailNotifications
company = Company.objects.first()
SubscriptionEmailNotifications.send_trial_expiring_email(company, 7)
```

#### 12.3 Test API Endpoint
```bash
curl http://localhost:8000/api/subscription/<company-slug>/status/
```

### Step 13: Local Testing Setup

#### 13.1 Start All Services
```bash
# Terminal 1 - Django Server
python manage.py runserver

# Terminal 2 - Celery Worker
celery -A estateProject worker -l info

# Terminal 3 - Celery Beat
celery -A estateProject beat -l info

# Terminal 4 - Redis (if using Docker)
docker run -d -p 6379:6379 redis:latest

# Or with native Redis:
redis-server
```

#### 13.2 Access Admin Dashboard
- Navigate to: `http://localhost:8000/admin/company/test-company/subscription/`
- View subscription status, upgrade options, billing history

#### 13.3 Test Payment Flow
1. Go to upgrade page
2. Select payment method (Stripe or Paystack)
3. Complete test payment
4. Verify transaction in `BillingHistory`

---

## 📊 Database Schema

### SubscriptionBillingModel
```sql
CREATE TABLE estateApp_subscriptionbillingmodel (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL,
    subscription_plan_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    subscription_starts_at DATETIME NOT NULL,
    subscription_ends_at DATETIME NOT NULL,
    grace_period_ends_at DATETIME NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    created_at DATETIME AUTO_CURRENT_TIMESTAMP,
    updated_at DATETIME AUTO_CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES estateApp_company(id),
    FOREIGN KEY (subscription_plan_id) REFERENCES estateApp_subscriptionplan(id),
    UNIQUE (company_id)
);
```

### BillingHistory
```sql
CREATE TABLE estateApp_billinghistory (
    id BIGINT PRIMARY KEY,
    subscription_id BIGINT NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    description TEXT,
    created_at DATETIME AUTO_CURRENT_TIMESTAMP,
    FOREIGN KEY (subscription_id) REFERENCES estateApp_subscriptionbillingmodel(id)
);
```

### SubscriptionFeatureAccess
```sql
CREATE TABLE estateApp_subscriptionfeatureaccess (
    id BIGINT PRIMARY KEY,
    subscription_id BIGINT NOT NULL,
    feature_name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    FOREIGN KEY (subscription_id) REFERENCES estateApp_subscriptionbillingmodel(id),
    UNIQUE (subscription_id, feature_name)
);
```

---

## 🧪 Testing Checklist

- [ ] Database migrations run successfully
- [ ] Models accessible in Django admin
- [ ] Subscription dashboard loads without errors
- [ ] Warning banners display correctly
- [ ] Countdown modals show accurate time remaining
- [ ] Upgrade modal functions and saves plan selection
- [ ] Payment forms accept valid card details
- [ ] Webhook handlers receive and process payments
- [ ] Grace period activates after subscription ends
- [ ] Emails send for all lifecycle events
- [ ] Celery tasks execute on schedule
- [ ] API endpoint returns correct JSON
- [ ] Admin decorators restrict unauthorized access
- [ ] Middleware injects subscription context
- [ ] Feature access restrictions work

---

## 🔧 Troubleshooting

### Issue: Migrations not found
```bash
python manage.py makemigrations estateApp
python manage.py migrate --run-syncdb
```

### Issue: Celery tasks not executing
```bash
# Check Celery worker logs
celery -A estateProject worker -l debug

# Test task manually
python manage.py shell
from estateApp.email_notifications import send_subscription_warnings
send_subscription_warnings.delay()
```

### Issue: Emails not sending
```bash
# Test email configuration
python manage.py shell
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
```

### Issue: Payment webhook not working
```bash
# Verify webhook URL is publicly accessible
# Check webhook logs in payment provider dashboard
# Verify webhook secret in .env matches
```

### Issue: Redis connection error
```bash
# Test Redis connection
redis-cli ping
# Should return PONG

# If using Docker, verify container is running
docker ps | grep redis
```

---

## 📈 Performance Optimization

### Database Indexing
```python
# In SubscriptionBillingModel
class Meta:
    indexes = [
        models.Index(fields=['company', 'status']),
        models.Index(fields=['subscription_ends_at', 'status']),
        models.Index(fields=['created_at']),
    ]
```

### Caching
```python
# Cache subscription status for 1 hour
from django.core.cache import cache

def get_subscription_status(company_id):
    cache_key = f'subscription_status_{company_id}'
    status = cache.get(cache_key)
    
    if status is None:
        subscription = SubscriptionBillingModel.objects.get(company_id=company_id)
        status = subscription.get_current_status()
        cache.set(cache_key, status, 3600)
    
    return status
```

### Query Optimization
```python
# Use select_related for foreign keys
subscriptions = SubscriptionBillingModel.objects.select_related(
    'company', 'subscription_plan'
).filter(status='active')
```

---

## 🚀 Production Deployment

### Pre-deployment Checklist
- [ ] Environment variables configured
- [ ] Database backed up
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Allowed hosts updated in settings
- [ ] Debug mode disabled
- [ ] HTTPS enabled
- [ ] CSRF middleware active
- [ ] CORS configured if needed

### Using Gunicorn & Nginx
```bash
# Install Gunicorn
pip install gunicorn

# Run Gunicorn
gunicorn estateProject.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Nginx config
upstream django {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/static/;
    }
}
```

### Using Docker
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "estateProject.wsgi:application"]
```

---

## 📞 Support & Documentation

**Quick Reference**: See `QUICK_REFERENCE_CARD.md`  
**Architecture**: See `SUBSCRIPTION_ARCHITECTURE_DIAGRAMS.md`  
**Implementation**: See `PHASE2_IMPLEMENTATION_GUIDE.md`  
**Billing Strategy**: See `BILLING_SUBSCRIPTION_STRATEGY.md`

---

## ✅ Deployment Complete!

Once all steps are completed:

1. **Verify**: Run test suite and manual testing
2. **Monitor**: Check Celery worker logs and email delivery
3. **Optimize**: Monitor database performance and optimize queries
4. **Maintain**: Regular backups and security updates

**Status**: Ready for production deployment ✅

---

*Last Updated: 2024*  
*Phase 2 Complete Subscription System Deployment Guide*
