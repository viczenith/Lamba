# Billing Page Implementation - Comprehensive Summary

## Overview
Implemented a complete subscription billing system with Paystack payment integration, including:
1. Dynamic subscription status badges ("Subscribed" tag on current plan)
2. **SMART downgrade validation system (blocks downgrades when usage exceeds target plan limits)**
3. Downgrade warning system (warns when switching from unlimited to limited plans - ONLY when usage is within limits)
4. Paystack card payment integration (credit/debit cards, USSD, bank transfers)
5. Bank transfer with Paystack Dedicated Virtual Accounts (dynamic account generation)

## Files Modified

### 1. Frontend - Billing Template
**File**: `estateApp/templates/admin_side/company_profile_tabs/_billing.html`

**Key Changes**:
- Added Paystack inline JS library: `<script src="https://js.paystack.co/v1/inline.js"></script>`
- Added subscription status tracking with `currentSubscription` object
- Implemented plan hierarchy system (Starter=1, Professional=2, Enterprise=3)
- Added "Subscribed" badge to current plan in `renderPlans()` function
- Implemented downgrade warning modal with comparison display
- Integrated Paystack payment popup with transaction verification
- Added dynamic virtual account generation for bank transfers
- Updated bank transfer modal to show generated account details

**Subscription Status Indicators**:
```javascript
const currentSubscription = {
  plan: '{{ subscription.plan.name|lower }}',
  planName: '{{ subscription.plan.name }}',
  tier: '{{ subscription.plan.tier|lower }}',
  isActive: {{ subscription.is_active|lower }},
  endDate: '{{ subscription.end_date|date:"Y-m-d" }}',
};
```

**Features**:
- ✅ Green "Subscribed" badge on active plan
- ⚠️ Orange downgrade warning modal
- 💳 Paystack payment popup integration
- 🏦 Dynamic virtual account generation
- 🔄 Automatic subscription activation after payment

### 2. Backend - Payment Views
**File**: `estateApp/paystack_payment_views.py` (NEW)

**Endpoints Created**:
1. **`verify_paystack_payment`** - POST endpoint to verify Paystack payment
   - Verifies transaction with Paystack API
   - Activates subscription and updates company
   - Records transaction in database
   - Updates plan limits (unlimited for Enterprise, limited for others)

2. **`generate_virtual_account`** - POST endpoint for bank transfer
   - Creates/retrieves Paystack customer
   - Generates dedicated virtual account (Wema Bank)
   - Stores pending transaction
   - Returns account details to frontend

3. **`paystack_webhook`** - POST endpoint for Paystack webhooks
   - Verifies webhook signature (HMAC SHA512)
   - Processes charge.success events
   - Automatically activates subscription on bank transfer confirmation
   - Updates pending transactions to completed

**Security Features**:
- CSRF protection (except webhook with signature verification)
- Login required decorators
- Company isolation checks
- Webhook signature validation

### 3. URL Configuration
**File**: `estateApp/urls.py`

**Routes Added**:
```python
path('api/subscription/verify-payment/', verify_paystack_payment, name='verify-paystack-payment'),
path('api/subscription/generate-virtual-account/', generate_virtual_account, name='generate-virtual-account'),
path('api/subscription/validate-downgrade/', validate_downgrade, name='validate-downgrade'),  # NEW
path('api/paystack/webhook/', paystack_webhook, name='paystack-webhook'),
```

### 4. Database Models
**File**: `estateApp/models.py`

**Field Added to Company Model**:
```python
paystack_customer_code = models.CharField(
    max_length=255,
    unique=True,
    null=True,
    blank=True,
    verbose_name="Paystack Customer Code"
)
```

**Migration File**: `estateApp/migrations/0002_add_paystack_customer_code.py`

### 5. Views Context
**File**: `estateApp/views.py`

**Added to company_profile_view context**:
```python
'PAYSTACK_PUBLIC_KEY': paystack_public_key,
```

## Payment Flow

### Card Payment Flow (Paystack Popup)
1. User selects plan and clicks "Subscribe"
2. Payment modal opens, user enters email
3. JavaScript calls `processPaystackPayment(email)`
4. Paystack popup opens with payment form
5. User completes payment (card/USSD/bank)
6. On success, `verifyPayment(reference)` called
7. Frontend POSTs to `/api/subscription/verify-payment/`
8. Backend verifies with Paystack API
9. Subscription activated, page reloads

### Bank Transfer Flow (Virtual Account)
1. User selects plan and "Bank Transfer" method
2. JavaScript calls `initiateBankTransfer()`
3. Frontend POSTs to `/api/subscription/generate-virtual-account/`
4. Backend creates Paystack customer if needed
5. Backend generates dedicated virtual account
6. Account details returned and displayed in modal
7. User makes transfer to provided account
8. Paystack webhook notifies system (charge.success event)
9. Backend automatically activates subscription
10. Transaction updated to "completed"

## Downgrade Warning System

**Two-Stage Validation Process**:

### Stage 1: Usage Validation (NEW)
Before showing any warning, system validates if downgrade is possible:

```javascript
function validateDowngradeWithBackend(newPlan) {
  fetch('/api/subscription/validate-downgrade/', {
    method: 'POST',
    body: JSON.stringify({ plan_id: newPlan.id })
  })
  .then(response => response.json())
  .then(data => {
    if (data.can_downgrade) {
      // Usage within limits - show warning
      showDowngradeWarning(currentPlan, newPlan);
    } else {
      // Usage exceeds limits - BLOCK downgrade
      showDowngradeBlocked(currentPlan, newPlan, data.usage_comparison, data.exceeds);
    }
  });
}
```

**Backend Validation Logic**:
```python
# Calculate current usage
current_estates = Estate.objects.filter(company=company).count()
current_allocations = Transaction.objects.filter(company=company, transaction_type__in=['full_payment', 'part_payment']).count()
current_clients = (primary_clients + affiliated_clients)
current_marketers = (primary_marketers + affiliated_marketers)

# Compare against target plan limits
for resource in [estates, allocations, clients, marketers, properties]:
    if current_count > target_limit:
        exceeds.append({resource, current, limit, overage})

can_downgrade = len(exceeds) == 0
```

### Stage 2A: Downgrade Blocked Modal (When Usage Exceeds Limits)

**Displayed When**: Current usage exceeds ANY limit of target plan

**Example Scenario**:
- Company on Enterprise (unlimited) has:
  - 150 Estates
  - 300 Allocations
  - 600 Clients
  - 50 Marketers
- Tries to downgrade to Starter (25/50/100/5 limits)

**Modal Display**:
```
🚫 DOWNGRADE BLOCKED

Your current usage exceeds Starter Plan limits:

┌──────────────┬─────────────┬──────────────┬────────────┐
│  Resource    │ Your Usage  │ Starter Max  │  Overage   │
├──────────────┼─────────────┼──────────────┼────────────┤
│ Estates      │    150      │      25      │  +125 ❌   │
│ Allocations  │    300      │      50      │  +250 ❌   │
│ Clients      │    600      │     100      │  +500 ❌   │
│ Marketers    │     50      │       5      │   +45 ❌   │
└──────────────┴─────────────┴──────────────┴────────────┘

To downgrade to Starter plan:
1. Estates: Delete/archive 125 (reduce from 150 to 25 max)
2. Allocations: Delete/archive 250 (reduce from 300 to 50 max)
3. Clients: Delete/archive 500 (reduce from 600 to 100 max)
4. Marketers: Delete/archive 45 (reduce from 50 to 5 max)

OR stay on Enterprise plan to keep unlimited access.
```

**User Options**:
- **Close** - Dismiss modal, revert to current plan
- **Stay on [Current Plan]** - Explicitly keep current plan

**Result**: Downgrade is REFUSED. User cannot proceed until they reduce usage.

### Stage 2B: Downgrade Warning Modal (When Usage is Within Limits)

**Displayed When**: Current usage fits within target plan limits

**Trigger Condition**:
```javascript
const currentTier = planHierarchy[currentSubscription.tier];  // 3 (Enterprise)
const newTier = newPlan.tier;  // 1 (Starter)

if (newTier < currentTier && can_downgrade) {
  showDowngradeWarning(currentPlanObj, newPlan);
}
```

**Warning Display**:
- Shows current plan → new plan comparison
- Lists features that will be lost:
  - Unlimited features becoming limited
  - Future restrictions on adding more resources
  - Potential data access limitations
  - Immediate effect warning

**User Options**:
- **Cancel** - Reverts selection to current plan
- **I Understand, Continue** - Proceeds with downgrade

**Result**: Downgrade is ALLOWED but requires explicit confirmation.

## Subscription Status Badges

**Current Plan Badge** (Green):
```html
<div class="price-badge bg-emerald-500 text-white">
  <i class="bi bi-check-circle-fill"></i> Subscribed
</div>
```

**Popular Plan Badge** (Blue with pulse):
```html
<div class="price-badge bg-indigo-500 text-white badge-popular">
  Most Popular
</div>
```

**Recommended Badge** (Amber):
```html
<div class="price-badge bg-amber-100 text-amber-700">
  Recommended
</div>
```

## Configuration Required

### Environment Variables (Required)
Add to your `.env` or environment:
```bash
PAYSTACK_SECRET_KEY=sk_test_your_secret_key_here
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key_here
```

### Django Settings
Already configured in `estateProject/settings.py`:
```python
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')
```

### Paystack Webhook Setup
1. Go to Paystack Dashboard → Settings → Webhooks
2. Add webhook URL: `https://yourdomain.com/api/paystack/webhook/`
3. Events to subscribe: `charge.success`
4. Webhook will auto-activate subscriptions on bank transfer completion

## Database Migration

Run migration to add paystack_customer_code field:
```bash
python manage.py migrate estateApp
```

## Testing Checklist

### Card Payment Testing
- [ ] Click Subscribe with Paystack payment method
- [ ] Enter email in payment modal
- [ ] Paystack popup opens successfully
- [ ] Complete test payment (use Paystack test cards)
- [ ] Success modal appears
- [ ] Page reloads with activated subscription
- [ ] Plan shows "Subscribed" badge

### Bank Transfer Testing
- [ ] Click Subscribe with Bank Transfer method
- [ ] Loading spinner shows during account generation
- [ ] Bank transfer modal displays with account details
- [ ] Copy buttons work for account number and reference
- [ ] Make test transfer to virtual account
- [ ] Webhook receives charge.success event
- [ ] Subscription activates automatically
- [ ] Transaction status updates to "completed"

### Downgrade Warning Testing
- [ ] Click Subscribe with Paystack payment method
- [ ] Subscribe to Enterprise plan (highest tier)
- [ ] Verify "Subscribed" badge appears on Enterprise

**Test Case 1: Downgrade Blocked (Usage Exceeds Limits)**
- [ ] Add 150+ estates, 300+ allocations, 600+ clients, 50+ marketers
- [ ] Try to select Starter plan (25/50/100/5 limits)
- [ ] "Validating..." spinner shows
- [ ] Downgrade BLOCKED modal appears (red border)
- [ ] Usage comparison table shows all overages with red indicators
- [ ] Reduction steps listed clearly
- [ ] Cannot proceed with downgrade
- [ ] "Stay on Enterprise" button works
- [ ] "Close" button reverts to current plan

**Test Case 2: Downgrade Warning (Usage Within Limits)**
- [ ] Ensure usage is below Starter limits (e.g., 10 estates, 20 allocations)
- [ ] Try to select Starter plan
- [ ] "Validating..." spinner shows
- [ ] Downgrade WARNING modal appears (orange border)
- [ ] Warning explains feature loss
- [ ] "Cancel" button reverts to current plan
- [ ] "I Understand, Continue" allows downgrade to proceed

**Test Case 3: Edge Cases**
- [ ] Try downgrade with exactly at limit (e.g., 25 estates for Starter)
- [ ] Should allow downgrade (within limits)
- [ ] Try downgrade with 26 estates (1 over limit)
- [ ] Should block downgrade
- [ ] Verify overage shows "+1" correctly

### Badge Testing
- [ ] Current plan shows green "Subscribed" badge
- [ ] Popular plan shows blue "Most Popular" badge
- [ ] Badges animate smoothly
- [ ] Only one plan shows "Subscribed" at a time

## API Response Examples

### Verify Payment Success
```json
{
  "success": true,
  "message": "Subscription activated successfully",
  "subscription": {
    "plan": "Enterprise",
    "billing_cycle": "annual",
    "end_date": "2025-12-15T10:30:00Z"
  }
}
```

### Generate Virtual Account Success
```json
{
  "success": true,
  "account": {
    "account_number": "9876543210",
    "account_name": "Real Estate MS Limited",
    "bank_name": "Wema Bank",
    "bank_id": 20
  },
  "reference": "SUB-ENTERPRISE-1734235800ABC123"
}
```

### Webhook Event (charge.success)
```json
{
  "event": "charge.success",
  "data": {
    "reference": "SUB-ENTERPRISE-1734235800ABC123",
    "status": "success",
    "amount": 15000000,
    "currency": "NGN",
    "customer": {
      "email": "company@example.com"
    }
  }
}
```

## Plan Limits Configuration

**Starter Plan** (Tier 1 - Limited):
- Max Plots: 25
- Max Agents: 5
- Max Clients: 100
- Max Properties: 50

**Professional Plan** (Tier 2 - Limited):
- Max Plots: 100
- Max Agents: 25
- Max Clients: 500
- Max Properties: 200

**Enterprise Plan** (Tier 3 - Unlimited):
- Max Plots: -1 (unlimited)
- Max Agents: -1 (unlimited)
- Max Clients: -1 (unlimited)
- Max Properties: -1 (unlimited)

## Security Considerations

1. **Payment Verification**:
   - Always verify transactions with Paystack API
   - Never trust client-side payment confirmations
   - Use reference numbers for transaction tracking

2. **Webhook Security**:
   - Verify HMAC SHA512 signature on all webhooks
   - Reject webhooks with invalid signatures
   - Log all webhook events for audit trail

3. **Company Isolation**:
   - All payment endpoints check request.user.company
   - Transactions linked to specific companies
   - No cross-company subscription access

4. **Downgrade Protection**:
   - Warn users before downgrading
   - Explain feature loss clearly
   - Require explicit confirmation

## Troubleshooting

### Payment Not Activating
- Check Paystack webhook is configured correctly
- Verify webhook URL is publicly accessible
- Check webhook signature is valid
- Review server logs for errors

### Virtual Account Not Generating
- Verify PAYSTACK_SECRET_KEY is set
- Check Paystack API connectivity
- Ensure customer creation succeeded
- Review Paystack dashboard for errors

### Downgrade Warning Not Showing
- Verify currentSubscription object has correct data
- Check planHierarchy mapping is correct
- Ensure tier values are 1, 2, 3 (not strings)

### "Subscribed" Badge Not Showing
- Check subscription.is_active flag
- Verify plan ID matches subscription.plan.name
- Ensure currentSubscription object is properly set

## Next Steps

1. **Set Paystack API Keys**: Add test/live keys to environment variables
2. **Run Migration**: Apply database changes for paystack_customer_code
3. **Configure Webhook**: Set up webhook URL in Paystack dashboard
4. **Test Payments**: Use Paystack test cards to verify flow
5. **Monitor Transactions**: Check Transaction model for payment records
6. **Update Plan Pricing**: Modify prices in _billing.html plans array if needed

## Support

For Paystack integration issues:
- Documentation: https://paystack.com/docs
- Support: support@paystack.com
- Test Cards: https://paystack.com/docs/payments/test-payments

For implementation questions:
- Review this document
- Check server logs (Django logs)
- Inspect browser console for JavaScript errors
- Verify Paystack dashboard for transaction status
