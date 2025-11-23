# LAMBA Real Estate - Comprehensive Billing & Subscription Strategy

## 1. OVERVIEW: Complete Subscription Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│  SUBSCRIPTION LIFECYCLE STATE MACHINE                              │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──── TRIAL (14 days) ────┐
                    │                         │
                    │ • Full feature access   │
                    │ • No payment required   │
                    │ • Counts down to end    │
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │  USER SELECTS PLAN &     │
                    │  PROVIDES PAYMENT INFO   │
                    └────────────┬──────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
    PAYMENT            PAYMENT            PAYMENT
    SUCCESSFUL         FAILED             CANCELLED
        │                │                    │
        ▼                ▼                    ▼
   ACTIVE              SUSPENDED         CANCELLED
   (Paid)          (Hard stop)          (No access)
     │                  │                    │
     │ Day 7            │                    │
     │ before           │                    │
     │ expiry           │                    │
     │ = warning        │                    │
     │                  │                    │
     ▼                  │                    │
   EXPIRES             │                    │
   (End of              │                    │
    paid term)          │                    │
     │                  │                    │
     ▼                  │                    │
 GRACE_PERIOD       (Resolved by             │
 (Read-only)        payment)                 │
 (7 days)               │                    │
     │                  ▼                    │
     │ Day 7       ACTIVE                    │
     │ expires      again                    │
     │                                       │
     ▼                                       │
 EXPIRED                                     │
 (No access) ◄──────────────────────────────┘
```

## 2. SUBSCRIPTION STATES & TRANSITIONS

### STATE: TRIAL
- **Duration**: 14 days from company creation
- **Access Level**: Full (all features available)
- **Payment**: Not required
- **Warnings**: Starting Day 8 (6 days remaining)
- **Transitions to**: ACTIVE (if payment provided) or EXPIRED (if no action)

### STATE: ACTIVE (Paid)
- **Duration**: Based on billing cycle (monthly or annual)
- **Access Level**: Full (all features available)
- **Payment**: Recurring (auto-renew if enabled)
- **Warnings**: 
  - 7 days before expiry (Yellow)
  - 4 days before expiry (Orange)
  - 2 days before expiry (Red)
- **Transitions to**: GRACE_PERIOD or EXPIRED

### STATE: GRACE_PERIOD
- **Duration**: 7 days after subscription expires
- **Access Level**: Read-only (can view but not create/edit)
- **Payment**: Encouraged (prevent feature loss)
- **Warnings**: Red - "Renew subscription to restore access"
- **Transitions to**: ACTIVE (if renewed) or EXPIRED (if no action)

### STATE: SUSPENDED
- **Duration**: After failed payment (manual recovery)
- **Access Level**: No access (locked out)
- **Payment**: Immediate payment required
- **Cause**: Payment failure, chargeback, fraud
- **Transitions to**: ACTIVE (manual admin action)

### STATE: EXPIRED
- **Duration**: Permanent (until renewal)
- **Access Level**: No access (all features disabled)
- **Payment**: Must pay to reactivate
- **Transitions to**: ACTIVE (if renewed)

### STATE: CANCELLED
- **Duration**: Permanent
- **Access Level**: Dashboard read-only (historical data)
- **Cause**: User cancellation or policy violation
- **Transitions to**: ACTIVE (manual admin action)

## 3. WARNING SYSTEM & NOTIFICATIONS

### Warning Levels

| Level | Status | Days | Banner | Modal | Email |
|-------|--------|------|--------|-------|-------|
| 0 | Green | >7 | None | None | None |
| 1 | Yellow | 4-7 | Yes | No | Daily |
| 2 | Orange | 2-4 | Yes | Yes | Every 6 hours |
| 3 | Red | <2 | Yes | Yes | Every 2 hours |

### Notification Triggers

**7 Days Before Expiry**
```
Email Subject: "Your Lamba subscription expires in 7 days"
Banner: Yellow warning
Action CTA: "View Plans" / "Upgrade"
```

**4 Days Before Expiry**
```
Email Subject: "Only 4 days left - Don't lose access!"
Banner: Orange warning with countdown
Modal: Shows if user logs in
Action CTA: "Upgrade Now"
```

**2 Days Before Expiry**
```
Email Subject: "URGENT: 2 days to maintain access"
Banner: Red warning, pulsing countdown
Modal: Immediate on login
Action CTA: "Upgrade Now" (prominent)
SMS: Alert with link
```

**Grace Period Active**
```
Email Subject: "Service limited - Renew subscription now"
Banner: Red "Read-only mode active"
Modal: Shows on every login
Action CTA: "Renew Now"
SMS: "Your subscription expired. Renew within 7 days"
```

**Expiration Confirmed**
```
Email: "Subscription expired - Full service disabled"
SMS: "Lamba: Your subscription has expired"
All features: Disabled
Dashboard: Read-only mode for historical review
```

## 4. FEATURE ACCESS CONTROL

### Access Matrix

```
FEATURE                 TRIAL   ACTIVE   GRACE   SUSPENDED   EXPIRED
─────────────────────────────────────────────────────────────────────
Create Client           ✓       ✓        ✗       ✗           ✗
Create Allocation       ✓       ✓        ✗       ✗           ✗
View Properties         ✓       ✓        ✓       ✗           ✗
Edit Settings           ✓       ✓        ✗       ✗           ✗
Export Data             ✓       ✓        ✗       ✗           ✗
API Access              ✓       ✓        ✗       ✗           ✗
Add Team Members        ✓       ✓        ✗       ✗           ✗
Use Marketplace         ✓       ✓        ✗       ✗           ✗
View Billing            ✓       ✓        ✓       ✓           ✓
Dashboard Access        ✓       ✓        ✓       ✗           ✓
```

### Rate Limiting Per Plan

**Starter Plan (₦70,000/month)**
- Max Properties: 5
- Max Clients: 2
- Max Allocations: 10/month
- Max API Calls: 100/day
- Max Team Members: 1
- Storage: 1GB

**Professional Plan (₦100,000/month)**
- Max Properties: 20
- Max Clients: 10
- Max Allocations: 100/month
- Max API Calls: 1000/day
- Max Team Members: 5
- Storage: 10GB

**Enterprise Plan (₦150,000/month)**
- Max Properties: Unlimited
- Max Clients: Unlimited
- Max Allocations: Unlimited
- Max API Calls: 10000/day
- Max Team Members: Unlimited
- Storage: 100GB

## 5. GRACE PERIOD STRATEGY

### Why Grace Period?

1. **Payment Retries**: Automatic payment may succeed on next attempt
2. **Customer Retention**: Keeps company data accessible during transition
3. **Revenue Recovery**: Reduces churn from accidental lapses
4. **Compliance**: Allows time to settle invoices or disputes

### Grace Period Flow

```
Day 0: Subscription Expires
  └─ Trigger grace period
  └─ Send notification: "Grace period active"
  └─ Enable read-only mode
  └─ Set grace_period_ends_at = 7 days from now

Days 1-3: Active Retention
  └─ Email: Daily renewal reminder
  └─ Dashboard: Red "Renew Now" banner
  └─ SMS: Alert with payment link

Days 4-6: Escalated Messaging
  └─ Email: 2x daily reminders
  └─ Modal: Shows on login
  └─ Dashboard: Pulsing red countdown

Day 7: Final Day
  └─ Email: "FINAL DAY" notice
  └─ SMS: Urgent reminder
  └─ Modal: Persistent (cannot dismiss)

Day 7, 11:59 PM: Expiration
  └─ Status: EXPIRED
  └─ Access: Fully disabled
  └─ Data: Still readable by admins (archive)
```

## 6. PAYMENT PROCESSING

### Payment Gateway Integration

**Stripe Configuration**
```python
STRIPE_API_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')

stripe_subscription = stripe.Subscription.create(
    customer=customer_id,
    items=[{
        'price': price_id,
    }],
    payment_behavior='default_incomplete',
    expand=['latest_invoice.payment_intent']
)
```

**Paystack Configuration**
```python
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')

paystack_subscription = requests.post(
    'https://api.paystack.co/subscription',
    headers={'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'},
    json={
        'customer': customer_id,
        'plan': plan_code,
        'authorization': auth_code
    }
)
```

### Payment Flow

1. **Initiate**: User selects plan and clicks "Upgrade"
2. **Tokenize**: Payment method tokenized (Stripe/Paystack)
3. **Charge**: First payment processed
4. **Confirm**: Payment confirmed, subscription activated
5. **Webhook**: Payment gateway sends webhook confirmation
6. **Update**: SubscriptionBillingModel updated with payment details
7. **Email**: Confirmation email sent to company admin

### Payment Failure Handling

```
Payment Failed
    │
    ├─ Email notification to admin
    │
    ├─ Set retry count = 1
    │
    ├─ Schedule retry in 3 days
    │
    ├─ If retry #1 fails:
    │   └─ Schedule retry #2 in 5 days
    │
    ├─ If retry #2 fails:
    │   └─ Mark as SUSPENDED
    │   └─ Disable all features
    │   └─ Send urgent recovery email
    │
    └─ If retry #3 (manual) fails:
        └─ Begin cancellation process
        └─ 30-day data retention period
```

## 7. BILLING HISTORY & INVOICING

### Invoice Structure

```
INVOICE #LAM-2024-001
Company: Acme Real Estate Limited
Date: January 1, 2024
Due: January 31, 2024

Item Description                Qty   Rate         Amount
─────────────────────────────────────────────────────────
Professional Plan - Monthly      1    ₦100,000     ₦100,000
                                                   ──────────
Subtotal                                           ₦100,000
Tax (VAT 7.5%)                                     ₦7,500
─────────────────────────────────────────────────────────
TOTAL DUE                                          ₦107,500

Payment Methods Accepted:
  • Stripe (Credit/Debit Card)
  • Paystack (Card, Transfer, USSD)
  • Bank Transfer
```

### Invoice Generation

- **Automatic**: Generated at billing date (monthly/annually)
- **Format**: PDF downloadable from admin dashboard
- **Email**: Sent to company admin's registered email
- **Retention**: 7-year archival for compliance
- **Tax**: NGN VAT calculated and included

### Billing History Tracking

```python
# BillingHistory model tracks:
- transaction_type (charge, refund, proration)
- state (pending, completed, failed, cancelled)
- amount and currency
- payment_method (stripe, paystack, bank_transfer)
- invoice_number (unique)
- transaction_id (gateway reference)
- paid_date vs due_date
```

## 8. UPGRADE/DOWNGRADE LOGIC

### Upgrade Path (e.g., Starter → Professional)

1. User selects new plan
2. System calculates prorated credit
3. Create new invoice with:
   - Remaining credits from old plan
   - Charge for new plan (with credit applied)
4. Update company subscription_tier
5. Increase rate limits immediately
6. Send confirmation email
7. Log transaction in BillingHistory

**Example Calculation:**
```
Old Plan (Starter): ₦70,000/month (30 days)
Days Remaining: 10 days
Credit: (10/30) × ₦70,000 = ₦23,333

New Plan (Professional): ₦100,000/month
Charge: ₦100,000 - ₦23,333 = ₦76,667
```

### Downgrade Path (e.g., Professional → Starter)

1. ⚠️ **Validation**: Check if company exceeds new limits
   - If 15 clients exist but Starter allows 2: Reject
   - If exceeded, show cleanup required notice
2. Allow downgrade only if compliant or after data cleanup
3. Calculate credit for unused portion
4. Apply credit to next billing cycle
5. Reduce rate limits effective next billing cycle
6. Send downgrade confirmation

## 9. ADMINISTRATIVE CONTROLS

### Company Admin Interface

**Location**: `/admin/company/<slug>/subscription/`

**Available Actions:**
- View current subscription status
- See feature usage vs limits
- Download invoices
- View billing history
- Upgrade/change plans
- Update payment method
- Request refund (for failed charges)
- Cancel subscription

### Super Admin Controls

**Location**: `/admin/subscription-management/`

**Available Actions:**
- Manual subscription activation
- Emergency suspension/reactivation
- Credit adjustments
- Plan overrides (for special cases)
- Billing report generation
- Chargeback/dispute handling
- Bulk subscription operations

## 10. FINANCIAL REPORTING

### Dashboard Metrics

- **Monthly Recurring Revenue (MRR)**
  ```
  MRR = Sum of all active monthly subscription amounts
  ```

- **Annual Recurring Revenue (ARR)**
  ```
  ARR = Sum of all active annual subscription amounts
  ```

- **Churn Rate**
  ```
  Churn = (Cancelled Subscriptions / Total Subscriptions) × 100
  ```

- **Expansion Revenue**
  ```
  Upgrades revenue vs Total revenue
  ```

### Analytics Available

- Revenue by plan tier
- Customer acquisition cost
- Lifetime value (LTV)
- Payment success rate
- Refund requests and approval rate
- Grace period recovery rate

## 11. SECURITY & COMPLIANCE

### PCI Compliance

- ✅ Use Stripe/Paystack (PCI DSS Level 1 compliant)
- ✅ NEVER store full credit card numbers
- ✅ Tokenize payment methods
- ✅ Encrypt sensitive fields in database

### Data Protection

```python
# SubscriptionBillingModel encryption
class SubscriptionBillingModel(models.Model):
    stripe_subscription_id = EncryptedCharField()
    paystack_subscription_code = EncryptedCharField()
```

### Audit Trail

```python
# Log all subscription changes
class SubscriptionAuditLog(models.Model):
    company = ForeignKey(Company)
    action = CharField()  # created, upgraded, downgraded, suspended
    old_tier = CharField()
    new_tier = CharField()
    timestamp = DateTimeField(auto_now_add=True)
    admin = ForeignKey(CustomUser)
    reason = TextField()
```

### Fraud Prevention

- ✅ Duplicate payment detection
- ✅ Velocity checks (multiple transactions in short time)
- ✅ 3D Secure for high-risk transactions
- ✅ IP geolocation monitoring
- ✅ Automatic chargeback monitoring

## 12. IMPLEMENTATION CHECKLIST

### Phase 1: Core Subscription (✅ COMPLETE)
- ✅ SubscriptionPlan model with 3 tiers
- ✅ Company model with subscription fields
- ✅ Trial period (14 days) auto-setup
- ✅ Feature enforcement methods
- ✅ UI plan selection (clickable)
- ✅ Pricing display (₦70K, ₦100K, ₦150K)
- ✅ Limit synchronization

### Phase 2: Billing & Grace Period (⏳ IN PROGRESS)
- ⏳ SubscriptionBillingModel (created)
- ⏳ BillingHistory tracking
- ⏳ Grace period logic (7 days)
- ⏳ Warning banners and modals
- ⏳ Countdown timers
- ⏳ Admin dashboard integration

### Phase 3: Payment Integration
- ⏻ Stripe integration
- ⏻ Paystack integration
- ⏻ Webhook handlers
- ⏻ Payment retry logic
- ⏻ Invoice generation/PDF

### Phase 4: Advanced Features
- ⏻ Upgrade/downgrade workflows
- ⏻ Prorated billing
- ⏻ Refund/credit system
- ⏻ Analytics dashboard
- ⏻ Email notification system

## 13. URLs FOR ADMIN DASHBOARD

```python
# Subscription Management Routes
/admin/company/<slug>/subscription/               # Main dashboard
/admin/company/<slug>/subscription/upgrade/       # Upgrade plans
/admin/company/<slug>/subscription/renew/         # Renewal form
/admin/company/<slug>/billing/history/            # Invoice history
/admin/company/<slug>/billing/initiate-payment/   # Payment initiation

# API Endpoints
/api/company/<slug>/subscription/status/          # JSON status
/api/company/<slug>/subscription/usage/           # Usage metrics
```

## 14. EMAIL TEMPLATES NEEDED

Create these email templates in `estateApp/email_templates/`:

1. `trial_ending_7days.html` - Yellow warning
2. `trial_ending_2days.html` - Red urgent warning
3. `trial_ended.html` - Upgrade required
4. `subscription_renewal_reminder.html` - Gentle reminder
5. `grace_period_active.html` - Limited access notification
6. `subscription_expired.html` - Final notice
7. `payment_failed.html` - Payment retry instructions
8. `invoice_receipt.html` - Invoice email
9. `upgrade_confirmation.html` - Upgrade success
10. `refund_processed.html` - Refund notification

## 15. NEXT IMMEDIATE TASKS

1. **Migrate Models**: Run `python manage.py makemigrations && python manage.py migrate`
2. **Create Admin Views**: Register SubscriptionBillingModel in Django admin
3. **Add URL Patterns**: Include subscription routes in urls.py
4. **Create Templates**: Add HTML templates for dashboard/upgrade/renewal
5. **Integrate Payment**: Connect Stripe/Paystack API
6. **Set Up Celery Tasks**: Automated warnings and renewal reminders
7. **Create Email Service**: Implement notification system
8. **Test End-to-End**: Full subscription lifecycle testing

---

**Document Version**: 2.0  
**Last Updated**: 2024  
**Status**: Complete Strategy Documentation Ready for Implementation
