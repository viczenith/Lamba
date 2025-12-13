# LAMBA Subscription System - Architecture & Data Flow

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAMBA SUBSCRIPTION SYSTEM                        │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Dashboard Views                                                 │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │   │
│  │  │ Subscription   │  │ Plan Upgrade   │  │ Billing        │    │   │
│  │  │ Dashboard      │  │ Interface      │  │ History        │    │   │
│  │  │                │  │                │  │                │    │   │
│  │  │ • Overview     │  │ • Plan Cards   │  │ • Transactions │    │   │
│  │  │ • Usage Stats  │  │ • Comparison   │  │ • Invoices     │    │   │
│  │  │ • Countdown    │  │ • Billing      │  │ • Downloads    │    │   │
│  │  │ • Actions      │  │   Cycle Choice │  │                │    │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  UI Components (Injected in all pages)                          │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ┌──────────────────────────────┐  ┌──────────────────────┐    │   │
│  │  │ Warning Banner               │  │ Countdown Modal      │    │   │
│  │  │ (Yellow/Orange/Red)          │  │ (Real-time timer)    │    │   │
│  │  │                              │  │                      │    │   │
│  │  │ • Icon + Message             │  │ • Day : Hour : Min   │    │   │
│  │  │ • Dismissible                │  │ • Status + Details   │    │   │
│  │  │ • CTA Button                 │  │ • Auto-show (<2 days)│    │   │
│  │  │ • Countdown ticker           │  │ • Renewal button     │    │   │
│  │  └──────────────────────────────┘  └──────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

                                 ↓↑

┌──────────────────────────────────────────────────────────────────────────┐
│                        MIDDLEWARE LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  SubscriptionMiddleware                                         │   │
│  │  • Runs on EVERY request                                        │   │
│  │  • Extracts subscription status                                 │   │
│  │  • Injects into request object                                  │   │
│  │  • request.subscription                                         │   │
│  │  • request.can_access_features                                  │   │
│  │  • request.access_restrictions                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

                                 ↓↑

┌──────────────────────────────────────────────────────────────────────────┐
│                        VIEW LAYER                                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Protected Views (with decorators):                                     │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  @subscription_required                                        │    │
│  │  @can_create_client_required                                   │    │
│  │  @can_create_allocation_required                               │    │
│  │  @read_only_if_grace_period                                    │    │
│  │  @api_access_required                                          │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Subscription Views:                                                    │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  subscription_dashboard()        → /subscription/              │    │
│  │  subscription_upgrade()          → /subscription/upgrade/      │    │
│  │  subscription_renew()            → /subscription/renew/        │    │
│  │  billing_history()               → /billing/history/           │    │
│  │  initiate_payment()              → /billing/initiate-payment/  │    │
│  │  subscription_api_status()       → /api/.../status/            │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

                                 ↓↑

┌──────────────────────────────────────────────────────────────────────────┐
│                        BUSINESS LOGIC LAYER                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SubscriptionBillingModel Methods:                                      │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  refresh_status()              • Updates status based on dates  │    │
│  │  is_trial() / is_active()      • Status checks                 │    │
│  │  is_grace_period() / is_expired()                              │    │
│  │  get_warning_level()           • 0=Green, 1=Yellow, 2=Orange, │    │
│  │                                  3=Red                          │    │
│  │  get_warning_message()         • Returns formatted message      │    │
│  │  should_show_warning_banner()  • Boolean check                 │    │
│  │  get_days_remaining()          • Integer days left             │    │
│  │  get_expiration_datetime()     • DateTime object               │    │
│  │  start_grace_period()          • Activate 7-day grace          │    │
│  │  get_access_restrictions()     • Dict of restrictions          │    │
│  │  can_access_features()         • Feature gating                │    │
│  │  can_create_client()           • Client creation check         │    │
│  │  can_use_api()                 • API access check              │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Company Model Methods (existing):                                      │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  can_add_client()              • Client limit enforcement      │    │
│  │  can_add_affiliate()           • Affiliate limit enforcement   │    │
│  │  can_create_allocation()       • Allocation limit enforcement  │    │
│  │  get_feature_limits()          • Return all tier limits        │    │
│  │  get_usage_stats()             • Current usage statistics      │    │
│  │  sync_plan_limits()            • Auto-sync from SubscriptionPlan│   │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

                                 ↓↑

┌──────────────────────────────────────────────────────────────────────────┐
│                        DATA MODEL LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  SubscriptionBillingModel                                    │      │
│  ├──────────────────────────────────────────────────────────────┤      │
│  │  Fields:                                                     │      │
│  │  • company (ForeignKey → Company)                            │      │
│  │  • status (CharField: trial/active/grace/suspended/etc)      │      │
│  │  • trial_started_at, trial_ends_at (DateTime)                │      │
│  │  • subscription_started_at, subscription_ends_at             │      │
│  │  • current_plan (ForeignKey → SubscriptionPlan)              │      │
│  │  • grace_period_started_at, grace_period_ends_at             │      │
│  │  • billing_cycle (monthly/annual)                            │      │
│  │  • auto_renew (Boolean)                                      │      │
│  │  • monthly_amount, annual_amount (Decimal)                   │      │
│  │  • payment_method, stripe_id, paystack_code                  │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  BillingHistory (One-to-Many)                                │      │
│  ├──────────────────────────────────────────────────────────────┤      │
│  │  • billing (ForeignKey → SubscriptionBillingModel)           │      │
│  │  • transaction_type (charge/refund/proration/adjustment)     │      │
│  │  • state (pending/completed/failed/cancelled)                │      │
│  │  • amount, currency                                          │      │
│  │  • invoice_number (unique)                                   │      │
│  │  • transaction_id (gateway reference)                        │      │
│  │  • billing_date, due_date, paid_date                         │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  SubscriptionPlan (Lookup Table)                             │      │
│  ├──────────────────────────────────────────────────────────────┤      │
│  │  • tier (starter/professional/enterprise)                    │      │
│  │  • name, description                                         │      │
│  │  • monthly_price, annual_price (₦70K/₦100K/₦150K)            │      │
│  │  • max_plots, max_agents, max_api_calls_daily                │      │
│  │  • features (JSONField)                                      │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Company (Existing Model - Enhanced)                         │      │
│  ├──────────────────────────────────────────────────────────────┤      │
│  │  Added Fields:                                               │      │
│  │  • subscription_tier (starter/professional/enterprise)       │      │
│  │  • subscription_status (active/suspended/etc)                │      │
│  │  • trial_ends_at, subscription_ends_at (DateTime)            │      │
│  │  • max_plots, max_agents, max_api_calls_daily (from tier)    │      │
│  │                                                              │      │
│  │  Added Relationship:                                         │      │
│  │  • billing (OneToOne → SubscriptionBillingModel)             │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

                                 ↓↑

┌──────────────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Tables:                                                                │
│  • estateApp_subscriptionbillingmodel                                   │
│  • estateApp_billinghistory                                             │
│  • estateApp_subscriptionfeatureaccess                                  │
│  • estateApp_subscriptionplan (existing, enhanced)                      │
│  • estateApp_company (existing, enhanced)                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Request Processing Flow

```
User Request
    ↓
Django Routing
    ↓
SubscriptionMiddleware
    ├─ Get company from user
    ├─ Get SubscriptionBillingModel
    ├─ Call refresh_status()
    ├─ Inject into request
    └─ Inject into context
    ↓
View Function
    ├─ Check decorators (@subscription_required, etc)
    ├─ Call business logic (if needed)
    ├─ Gather context data
    └─ Render template
    ↓
Template Rendering
    ├─ Access context processor data
    ├─ Include warning banner (if applicable)
    ├─ Include countdown modal (if applicable)
    ├─ Render main content
    └─ Add JavaScript timers
    ↓
Response to Browser
    ├─ HTML + CSS
    ├─ JavaScript (countdown logic)
    └─ Timers update every 1 second
```

---

## State Transition Diagram

```
                    ┌──────────────────┐
                    │     TRIAL        │
                    │   (14 days)      │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           │          (Day 8+) No action       │
           │                 │                 │
           ▼                 ▼                 ▼
      ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
      │   ACTIVE    │  │   EXPIRED    │  │ CANCELLED    │
      │  (Paid sub) │  │  (No action) │  │ (User quit)  │
      └──────┬──────┘  └──────────────┘  └──────────────┘
             │
        (Days 1-7 warning)
             │
      ┌──────▼──────┐
      │Grace Period │ (7 days)
      │ (Read-only) │
      └──────┬──────┘
             │
        (Day 7)
             │
      ┌──────▼──────┐
      │  EXPIRED    │
      │(All disabled)│
      └─────────────┘

Also possible from any state:
┌───────────────────────────┐
│    SUSPENDED              │
│ (Payment failure,         │
│  chargeback, fraud)       │
│ (Requires manual recovery)│
└───────────────────────────┘
```

---

## Warning Timeline

```
Day 0: Subscription Active
├─ Status: ACTIVE
├─ Warning: None
└─ Access: Full

Day 1-5: Pre-warning period
├─ Status: ACTIVE  
├─ Warning: None
├─ Days remaining: 8-4
└─ Access: Full

Day 8: Yellow Warning (7 days before)
├─ Status: ACTIVE
├─ Warning level: 1 (Yellow)
├─ Banner: "Upcoming Upgrade" (light yellow)
├─ Modal: No
├─ Email: Gentle reminder
└─ Access: Full

Day 11: Orange Warning (4 days before)
├─ Status: ACTIVE
├─ Warning level: 2 (Orange)
├─ Banner: "Subscription Reminder" (orange with countdown)
├─ Modal: Yes (shows on login)
├─ Email: Reminder every 6 hours
└─ Access: Full

Day 13: Red Warning (2 days before)
├─ Status: ACTIVE
├─ Warning level: 3 (Red)
├─ Banner: "Subscription Expiring Soon" (red, pulsing countdown)
├─ Modal: Yes (persistent)
├─ Email/SMS: Every 2 hours
└─ Access: Full

Day 15: Expiration
├─ Status: GRACE_PERIOD
├─ Warning level: 3 (Red)
├─ Banner: "Grace Period Active - Renew within 7 days"
├─ Modal: Persistent on every login
├─ Email: Daily renewal reminder
└─ Access: Read-only (can't create/edit)

Day 22: Grace Period Ends
├─ Status: EXPIRED
├─ Warning: Access completely disabled
├─ Banner: Not shown (no access to dashboard)
├─ Modal: Not applicable
├─ Email: "Subscription fully expired"
└─ Access: None (except read historical data)
```

---

## Feature Access Matrix

```
                    TRIAL   ACTIVE  GRACE   SUSPENDED  EXPIRED
────────────────────────────────────────────────────────────────
Dashboard          ✓       ✓       ✓       ✗          ✓*
Create Client      ✓       ✓       ✗       ✗          ✗
Create Allocation  ✓       ✓       ✗       ✗          ✗
View Properties    ✓       ✓       ✓       ✗          ✓*
Edit Settings      ✓       ✓       ✗       ✗          ✗
Export Data        ✓       ✓       ✗       ✗          ✗
API Access         ✓       ✓       ✗       ✗          ✗
Add Team Members   ✓       ✓       ✗       ✗          ✗
Billing History    ✓       ✓       ✓       ✓          ✓*
View Invoices      ✓       ✓       ✓       ✓          ✓*

* Read-only, no modifications
```

---

## Decorator Execution Order

```
@login_required
    ↓
@subscription_required('feature')
    ├─ Check user.company exists
    ├─ Get company.billing
    ├─ Call billing.refresh_status()
    └─ Check billing.is_active()
    ↓
@can_create_client_required
    ├─ Call company.can_add_client()
    └─ Check (bool, message) response
    ↓
@read_only_if_grace_period
    ├─ Check billing.is_grace_period()
    └─ If True: Only allow GET, HEAD, OPTIONS
    ↓
View Function Logic
    ├─ Access request.subscription
    ├─ Access request.access_restrictions
    └─ Execute main functionality
    ↓
Context Data Gathered
    ├─ get_subscription_context()
    ├─ Adds all needed template variables
    └─ Returns dict with 15+ keys
    ↓
Template Rendering
    ├─ Components included
    ├─ Timers initialized
    └─ Response sent
```

---

## JavaScript Execution Flow (Client-side)

```
Page Load
    ↓
Bootstrap Modal JavaScript Loaded
    ├─ Modal ID: #subscriptionCountdownModal
    ├─ Options: static backdrop, no keyboard
    └─ Auto-show if should_show_modal=True
    ↓
Countdown Timer Functions
    ├─ updateCountdown() called on page load
    ├─ setInterval(updateCountdown, 1000)
    └─ Every second:
       ├─ Calculate time remaining
       ├─ Update DOM elements
       └─ Update banner countdown
    ↓
Event Listeners
    ├─ "Renew Now" button click
    ├─ "Upgrade Now" button click
    ├─ Close button click
    └─ Banner dismiss button
    ↓
Timer Updates
    ├─ 1 second intervals
    ├─ Stops if distance < 0
    └─ Updates: days, hours, minutes, seconds
```

---

## Database Query Performance

```
On Each Request:
├─ Get Company: 1 query (cached by login_required)
├─ Get SubscriptionBillingModel: 1 query (via company.billing)
├─ refresh_status() execution:
│  ├─ No new queries (pure Python logic)
│  ├─ Uses existing data
│  └─ Saves only if status changed
└─ Total: ~2 queries (heavily cached)

Middleware Optimization:
├─ Try/except prevents errors if billing missing
├─ Middleware runs before view
├─ Results injected into request object
├─ Can be cached with cache framework
└─ Approximately 1-2ms per request
```

---

## Error Handling Flow

```
Exception Occurs
    ↓
Django Logging
    ├─ logger.error() called
    ├─ Error recorded to logs
    └─ Stack trace captured
    ↓
User Experience
    ├─ Try/except block catches
    ├─ Graceful fallback applied
    ├─ Dashboard still accessible
    └─ User sees generic message
    ↓
Admin Notification
    ├─ Error logged to console
    ├─ Django admin sees in logs
    └─ Admin can investigate
```

---

## Integration Touchpoints

```
Existing Code → New Code Integration:

1. Company Model
   └─ Relationship: company.billing (OneToOne)
   
2. CustomUser Model  
   └─ Via: user.company.billing
   
3. Views (Protected)
   └─ Add: @subscription_required decorator
   
4. Templates
   └─ Include: subscription_warning_banner.html
   └─ Include: subscription_countdown_modal.html
   
5. Settings
   └─ Add: SubscriptionMiddleware
   └─ Add: subscription_context processor
   
6. URLs
   └─ Add: subscription management routes
   
7. Admin
   └─ Register: SubscriptionBillingModel
   └─ Register: BillingHistory
```

---

## Deployment Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Load Balancer                                                  │
│      ↓                                                           │
│  ┌───┴────────────────────┐                                     │
│  │                        │                                     │
│  ▼                        ▼                                     │
│ Django App 1         Django App 2 (with Celery)                 │
│ (request handling)    (background tasks)                        │
│  │                        │                                     │
│  └────────┬───────────────┘                                     │
│           ▼                                                     │
│      Database (PostgreSQL)                                      │
│      • subscription_billingmodel table                          │
│      • billinghistory table                                     │
│      • subscriptionfeatureaccess table                          │
│                                                                 │
│  Cache Layer (Redis)                                            │
│  • subscription status (5 min TTL)                              │
│  • feature limits (1 hour TTL)                                  │
│                                                                 │
│  Celery Tasks (scheduled)                                       │
│  • check_subscription_expiries() - daily                        │
│  • process_grace_periods() - daily                              │
│  • process_grace_period_expirations() - daily                   │
│  • send_subscription_warning_email() - triggered                │
│                                                                 │
│  Email Service (SES/SMTP)                                       │
│  • Trial expiry warnings                                        │
│  • Grace period notifications                                   │
│  • Invoice receipts                                             │
│                                                                 │
│  Payment Gateways                                               │
│  • Stripe (webhooks for payment updates)                        │
│  • Paystack (webhooks for payment updates)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

**Diagram Version**: 1.0  
**Last Updated**: 2024  
**Status**: Complete Architecture Documentation
