# 🔍 BACKEND AUDIT - MISSING FEATURES & TODO

**Project Status:** SaaS Core Complete ✅ | Backend Completion Audit 📋  
**Current Phase:** Identify & Implement Missing Backend Features  
**Last Updated:** Today

---

## 📊 EXECUTIVE SUMMARY

The project has **3 core SaaS features 100% complete** with 30+ API endpoints, multi-tenancy middleware, and database migrations applied. However, several critical backend features remain unimplemented for production readiness.

**Completion Status:**
- ✅ Core SaaS Features: 100%
- ✅ API Endpoints: 100%
- ✅ Database Models: 100%
- ✅ Multi-Tenancy: 100%
- ⏳ Payment Processing: 0% (Stripe integration not wired)
- ⏳ Notifications: 30% (Structure exists, delivery not configured)
- ⏳ Error Tracking: 0%
- ⏳ Rate Limiting: 0%
- ⏳ Audit Logging: 0%
- ⏳ Security Hardening: 20%

---

## 🔴 CRITICAL - MUST IMPLEMENT BEFORE PRODUCTION

### 1. STRIPE WEBHOOK INTEGRATION
**Status:** ❌ Not Implemented  
**Impact:** HIGH - Revenue collection depends on this  
**Files Needed:**
- `estateApp/webhooks/stripe_webhooks.py` - NEW
- `estateApp/urls_webhooks.py` - NEW
- `estateApp/management/commands/sync_stripe_subscriptions.py` - NEW

**What's Already Done:**
- ✅ Company model has `stripe_customer_id` field
- ✅ Subscription fields: `subscription_tier`, `subscription_status`, `subscription_ends_at`
- ✅ `is_subscription_active()` method exists
- ✅ `max_plots`, `max_agents`, `max_api_calls_daily` enforcement ready

**What's Missing:**
```python
# Webhook handlers needed:
- handle_checkout_session_completed() → Create subscription, activate company
- handle_subscription_updated() → Update tier/limits
- handle_subscription_deleted() → Suspend company
- handle_payment_intent_succeeded() → Update payment records
- handle_payment_intent_payment_failed() → Alert billing team

# Views needed:
- CreateCheckoutSessionView → Initiate Stripe checkout
- StripeWebhookView → Receive Stripe events
- UpdateSubscriptionView → Change tier
- CancelSubscriptionView → Downgrade/cancel

# Models needed for complete billing:
- Invoice → Store generated invoices
- Payment → Individual payment records
- PaymentMethod → Saved cards/bank accounts
```

**Implementation Effort:** 8-12 hours  
**Priority:** 🔴 CRITICAL

---

### 2. PAYMENT PROCESSING & INVOICING
**Status:** ❌ Not Implemented  
**Impact:** HIGH - Revenue tracking depends on this  
**Files Needed:**
- `estateApp/models.py` → Add Invoice, Payment models
- `estateApp/admin.py` → Add invoice admin
- `estateApp/management/commands/generate_monthly_invoices.py` - ENHANCE
- `estateApp/api_views/billing_views.py` - NEW
- `estateApp/serializers/billing_serializers.py` - NEW

**What's Already Done:**
- ✅ `process_commissions.py` command exists (processes marketer payouts)
- ✅ `generate_invoices.py` command exists (skeleton)
- ✅ Company has `billing_email` field

**What's Missing:**
```python
# Models needed:
class Invoice(models.Model):
    company = ForeignKey(Company)
    amount = DecimalField()
    tax_amount = DecimalField()  # 7.5% VAT for Nigeria
    period_start = DateField()
    period_end = DateField()
    status = ['draft', 'issued', 'paid', 'overdue']
    due_date = DateField()
    paid_at = DateTimeField()
    
class Payment(models.Model):
    invoice = ForeignKey(Invoice)
    amount = DecimalField()
    payment_method = CharField()  # 'stripe', 'bank_transfer', 'cash'
    payment_reference = CharField()
    paid_at = DateTimeField()

# API Endpoints needed:
- GET /api/billing/invoices/ → List invoices
- GET /api/billing/invoices/{id}/ → Get invoice details
- POST /api/billing/invoices/{id}/download/ → PDF download
- GET /api/billing/payments/ → Payment history
- GET /api/billing/subscription/ → Current subscription info
```

**Calculation Logic:**
```
Monthly Invoice = (Subscription Fee) + (Overage Charges) - (Credits)
Overage = (Extra Plots × ₦300) + (Extra API Calls × ₦100 per 1000)
Tax = Invoice Amount × 0.075  # 7.5% VAT
```

**Implementation Effort:** 10-14 hours  
**Priority:** 🔴 CRITICAL

---

### 3. EMAIL NOTIFICATION SYSTEM
**Status:** 🟡 Partial (Structure exists, not wired)  
**Impact:** HIGH - User communication essential  
**Files Needed:**
- `estateApp/tasks.py` → Add email tasks (ENHANCE)
- `estateApp/notifications/email_templates/` → Create email templates
- `estateApp/management/commands/send_pending_notifications.py` - NEW

**What's Already Done:**
- ✅ Notification & UserNotification models exist
- ✅ NotificationDispatch model for batch processing
- ✅ Celery task queue configured
- ✅ Firebase Admin SDK available
- ✅ Email backend partially configured

**What's Missing:**
```python
# Email templates needed:
1. affiliation_approval_email.html
2. affiliation_rejection_email.html
3. commission_approved_email.html
4. commission_payment_email.html
5. invoice_generated_email.html
6. subscription_renewal_email.html
7. subscription_expiration_warning_email.html
8. api_limit_exceeded_email.html
9. payment_failed_email.html
10. trial_ending_soon_email.html

# Celery tasks needed:
@shared_task
def send_affiliation_approval_email(affiliation_id)
def send_commission_payment_email(commission_id)
def send_invoice_email(invoice_id)
def send_subscription_alerts()  # Runs daily
def send_weekly_summary_emails()

# Integration points:
- Signal hook on MarketerAffiliation.approve() → Send email
- Signal hook on MarketerEarnedCommission.mark_as_paid() → Send email
- Signal hook on Invoice.save() → Send email
- Scheduled task: Daily alerts for expiring trials
```

**Email Template Pattern:**
```html
<!-- templates/emails/base_email.html -->
<html>
  <body style="font-family: Arial">
    <h2>{{ company_name }}</h2>
    {% block content %}{% endblock %}
    <footer>
      <p>© {{ current_year }} {{ company_name }}. All rights reserved.</p>
    </footer>
  </body>
</html>
```

**Implementation Effort:** 6-8 hours  
**Priority:** 🔴 CRITICAL

---

### 4. ERROR TRACKING & MONITORING (Sentry)
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Production debugging essential  
**Files Needed:**
- `estateProject/settings.py` → Add Sentry configuration (ENHANCE)
- `estateApp/middleware.py` → Add error tracking (ENHANCE)

**What's Already Done:**
- ✅ Project structure supports Sentry integration
- ✅ Requirements ready for `sentry-sdk`

**What's Missing:**
```python
# settings.py additions:
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment=os.getenv('ENVIRONMENT', 'development'),
)

# Error tracking for:
- Payment failures (Stripe integration)
- Email delivery failures
- API rate limit violations
- Database query errors
- WebSocket connection errors
```

**Implementation Effort:** 2-3 hours  
**Priority:** 🟡 HIGH

---

## 🟡 HIGH PRIORITY - SHOULD IMPLEMENT BEFORE PRODUCTION

### 5. API RATE LIMITING
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Prevent abuse & manage costs  
**Files Needed:**
- `estateApp/throttles.py` - NEW
- `estateApp/settings.py` → Update REST_FRAMEWORK config

**Rate Limits by Subscription Tier:**
```
Starter:      100 requests/hour
Professional: 1,000 requests/hour
Enterprise:   10,000 requests/hour + custom limits

Also enforce max_api_calls_daily from Company model
```

**Implementation:**
```python
# throttles.py
from rest_framework.throttling import UserRateThrottle

class SubscriptionTierThrottle(UserRateThrottle):
    # Read from Company.max_api_calls_daily
    # Enforce per-second rate limiting
    # Track in Redis for performance

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'estateApp.throttles.SubscriptionTierThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'subscription_tier': '1000/hour'  # Default, overridden by tier
    }
}
```

**Implementation Effort:** 4-6 hours  
**Priority:** 🟡 HIGH

---

### 6. AUDIT LOGGING
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Compliance & debugging  
**Files Needed:**
- `estateApp/models.py` → Add AuditLog model (ENHANCE)
- `estateApp/signals.py` → Add audit logging (ENHANCE)
- `estateApp/management/commands/cleanup_audit_logs.py` - NEW

**Audit Events to Track:**
```python
# User actions:
- User login/logout
- File downloads
- Data exports
- Settings changes

# Admin actions:
- Affiliation approvals
- Commission approvals
- Subscription changes
- Marketer suspension/reactivation

# System events:
- Failed API calls
- Payment processing
- Invoice generation
- Backup operations
```

**Model:**
```python
class AuditLog(models.Model):
    company = ForeignKey(Company)
    user = ForeignKey(CustomUser)
    action = CharField()  # 'create', 'update', 'delete', 'download', etc.
    model_name = CharField()
    object_id = IntegerField()
    changes = JSONField()  # Before/after values
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    timestamp = DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            Index(fields=['company', 'timestamp']),
            Index(fields=['user', 'timestamp']),
        ]
```

**Implementation Effort:** 5-7 hours  
**Priority:** 🟡 HIGH

---

### 7. SMS NOTIFICATIONS (OPTIONAL BUT VALUABLE)
**Status:** ❌ Not Implemented  
**Impact:** LOW-MEDIUM - Nice-to-have for alerts  
**Provider:** Twilio or local SMS gateway  
**Files Needed:**
- `estateApp/notifications/sms_service.py` - NEW
- `estateApp/tasks.py` → Add SMS task (ENHANCE)

**Use Cases:**
```
- Commission payment confirmation (SMS)
- Subscription expiration warning (SMS)
- Important alerts (SMS)
- OTP for high-security operations (SMS)
```

**Implementation Effort:** 3-5 hours  
**Priority:** 🟡 HIGH (but after email)

---

## 🟢 MEDIUM PRIORITY - CAN IMPLEMENT AFTER MVP LAUNCH

### 8. CACHING STRATEGY
**Status:** 🟡 Partial (Redis available, not fully utilized)  
**Impact:** MEDIUM - Performance optimization  
**Files Needed:**
- `estateApp/cache_service.py` - NEW
- `estateProject/settings.py` → Configure caching (ENHANCE)

**Cache Strategy:**
```python
# High-impact caches:
- Company subscription status (5 min TTL)
- Company API key validation (1 hour TTL)
- Property listings per company (10 min TTL)
- Client dashboard aggregations (30 min TTL)
- Marketer performance metrics (1 hour TTL)

# Cache invalidation:
- When subscription changes
- When property added/sold
- When commission processed
- When manual invalidation triggered
```

**Implementation Effort:** 4-6 hours  
**Priority:** 🟢 MEDIUM

---

### 9. ADVANCED SEARCH & FILTERING
**Status:** 🟡 Partial (DjangoFilterBackend available, needs optimization)  
**Impact:** MEDIUM - Search quality affects UX  
**Enhancements Needed:**
- Elasticsearch integration (optional)
- Advanced property filters
- Saved searches per client
- Search analytics

**Implementation Effort:** 5-8 hours  
**Priority:** 🟢 MEDIUM (Post-MVP)

---

### 10. ANALYTICS & REPORTING
**Status:** ❌ Not Implemented  
**Impact:** MEDIUM - Business intelligence  
**Files Needed:**
- `estateApp/models.py` → Add AnalyticsEvent model (ENHANCE)
- `estateApp/tasks.py` → Add analytics aggregation (ENHANCE)
- `estateApp/api_views/analytics_views.py` - NEW
- `estateApp/serializers/analytics_serializers.py` - NEW

**Reports Needed:**
```python
1. Revenue report (by company, tier, time period)
2. Usage report (API calls, storage, seats)
3. Performance report (marketer sales, commission earned)
4. Churn report (cancelled subscriptions, reason)
5. Client activity report (logins, properties viewed)
```

**Implementation Effort:** 8-12 hours  
**Priority:** 🟢 MEDIUM (Post-MVP)

---

## 🔵 LOW PRIORITY - FUTURE ENHANCEMENTS

### 11. ADVANCED SECURITY FEATURES
- [ ] Two-factor authentication (2FA)
- [ ] Encrypted sensitive data (bank accounts, SSN)
- [ ] HTTPS enforcement
- [ ] CORS hardening
- [ ] DDoS protection (Cloudflare)
- [ ] IP whitelisting (enterprise)
- [ ] OAuth2 integrations

**Priority:** 🔵 LOW (Post-MVP, when expanding)

---

### 12. API DOCUMENTATION ENHANCEMENT
- [ ] Swagger/OpenAPI generation (auto)
- [ ] API versioning (v1, v2, etc.)
- [ ] Deprecation notices
- [ ] SDK generation (Python, JavaScript)

**Priority:** 🔵 LOW (Can improve incrementally)

---

## 📋 IMPLEMENTATION PRIORITY SEQUENCE

### Phase 1: CRITICAL (Week 1) - Revenue & User Communication
```
1. ✅ Email Notification System (6-8 hrs)
   └─ Enable: Approval notifications, payment confirmations, alerts
   
2. ✅ Stripe Webhook Integration (8-12 hrs)
   └─ Enable: Subscription management, payment processing
   
3. ✅ Payment Processing & Invoicing (10-14 hrs)
   └─ Enable: Revenue tracking, invoice generation, payment history
```
**Total Estimated Time:** 24-34 hours  
**Target Completion:** Week 1 (5 working days)

---

### Phase 2: HIGH (Week 2) - Stability & Monitoring
```
4. ✅ Error Tracking (Sentry) (2-3 hrs)
   └─ Enable: Production monitoring, error alerts
   
5. ✅ API Rate Limiting (4-6 hrs)
   └─ Enable: Cost control, abuse prevention
   
6. ✅ Audit Logging (5-7 hrs)
   └─ Enable: Compliance, debugging, accountability
```
**Total Estimated Time:** 11-16 hours  
**Target Completion:** Week 2 (by day 3-4)

---

### Phase 3: MEDIUM (Weeks 3-4) - Performance & Intelligence
```
7. ✅ Caching Strategy (4-6 hrs)
   └─ Enable: Faster response times, reduced load
   
8. ✅ SMS Notifications (3-5 hrs)
   └─ Enable: Critical alerts via SMS
   
9. ✅ Analytics & Reporting (8-12 hrs)
   └─ Enable: Dashboard metrics, business intelligence
```
**Total Estimated Time:** 15-23 hours  
**Target Completion:** Week 4 (MVP ready for beta)

---

### Phase 4: FUTURE (Post-MVP)
- Advanced search with Elasticsearch
- Security hardening (2FA, encryption)
- API versioning & SDK generation
- Custom integrations

---

## ✅ CHECKLIST: BEFORE MOVING TO DRF APP

Make sure the following are implemented before migrating endpoints:

- [ ] **1. Email System** - Test end-to-end
  - [ ] Configure SMTP in settings
  - [ ] Send test email to admin
  - [ ] Verify email templates render correctly
  - [ ] Test Celery email tasks

- [ ] **2. Stripe Integration** - Test with test keys
  - [ ] Create test Stripe account
  - [ ] Test checkout session creation
  - [ ] Test webhook receipt
  - [ ] Verify subscription status update

- [ ] **3. Rate Limiting** - Test throttles
  - [ ] Verify rate limit headers in response
  - [ ] Test with many rapid requests
  - [ ] Verify 429 response when limit exceeded

- [ ] **4. Error Tracking** - Test Sentry
  - [ ] Send test error to Sentry
  - [ ] Verify error appears in Sentry dashboard
  - [ ] Test error context (user, company, request info)

- [ ] **5. Audit Logging** - Verify logs are created
  - [ ] Create test log entry
  - [ ] Verify all fields captured
  - [ ] Test audit log retrieval API

---

## 🚀 AFTER IMPLEMENTATION - MIGRATION TO DRF APP

Once all backend features are complete:

1. **Move all endpoints to DRF app** (Task 3)
   - Consolidate ViewSets, Serializers, URLs
   - Maintain all functionality
   
2. **Verify all connections** (Task 4)
   - Run integration tests
   - Check all 30+ endpoints work
   
3. **Deploy to production**
   - Use PRODUCTION_DEPLOYMENT_GUIDE.md
   - Run load tests
   - Setup monitoring

---

## 📞 IMPLEMENTATION COMMANDS

### Install Missing Dependencies
```bash
# Email & Notifications
pip install django-mail-templated  # Email templates

# Payment Processing
pip install stripe  # Already in requirements, but verify version

# Error Tracking
pip install sentry-sdk

# SMS (if needed)
pip install twilio

# Search (optional)
pip install elasticsearch

# Analytics
pip install django-analytical
```

### Create Management Commands
```bash
python manage.py startapp payments  # Or use existing commands
python manage.py startapp billing
python manage.py startapp notifications
```

### Test Email System
```bash
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Body', 'from@example.com', ['to@example.com'])
```

### Test Celery Tasks
```bash
# Terminal 1: Start worker
celery -A estateProject worker -l info

# Terminal 2: Send task
python manage.py shell
>>> from estateApp.tasks import dispatch_notification_stream
>>> dispatch_notification_stream.delay(1, 1, [1,2,3])
```

---

## 🎯 NEXT STEPS

**Immediate (Today):**
1. ✅ Complete this backend audit
2. Start implementation of Phase 1 (Critical)

**Short-term (This week):**
1. Implement Email Notification System
2. Implement Stripe Webhook Integration
3. Implement Payment Processing & Invoicing

**Medium-term (Next week):**
1. Implement Error Tracking (Sentry)
2. Implement API Rate Limiting
3. Implement Audit Logging

**Then:**
1. Migrate all endpoints to DRF app (Task 3)
2. Verify all connections (Task 4)
3. Deploy to production!

---

**Status:** 🟡 Backend Audit Complete - Ready for Implementation  
**Next Action:** Start Phase 1 implementation (Email System)
