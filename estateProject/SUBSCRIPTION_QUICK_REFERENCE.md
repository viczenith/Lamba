# 🚀 Subscription & Billing - Quick Reference Guide

## Common Tasks

### 1. Get Company Subscription Status
```python
from estateApp.models import Company

company = Company.objects.get(id=1)

# Get billing status
status = company.get_billing_status()
print(status)
# {'tier': 'starter', 'status': 'active', 'is_active': True, ...}

# Get current plan
plan = company.get_current_plan()
print(f"Plan: {plan.name}, Price: ₦{plan.monthly_price}")

# Get usage
usage = company.get_usage_percentage()
print(usage)
# {'plots': {'current': 25, 'max': 50, 'percentage': 50}, ...}
```

### 2. Check if Company Can Perform Action
```python
# Can create more plots?
if company.can_create_plot():
    # Proceed to create plot
    pass
else:
    raise PlanLimitExceeded("Max plots reached")

# Can add more agents?
if company.can_add_agent():
    # Proceed to add agent
    pass

# Can make API call?
if company.can_make_api_call():
    company.record_api_call()
    # Proceed with API call
```

### 3. Create a Subscription Plan
```python
from estateApp.models import SubscriptionPlan

plan = SubscriptionPlan.objects.create(
    tier='starter',
    name='Starter Plan',
    description='Perfect for solo agents',
    monthly_price=15000,
    annual_price=150000,
    max_plots=50,
    max_agents=1,
    max_api_calls_daily=1000,
    features={
        'basic_listings': True,
        'api_access': True,
        'advanced_analytics': False,
        'team_collaboration': False,
    },
    is_active=True,
)
```

### 4. Manually Create an Invoice
```python
from estateApp.models import Invoice
from datetime import date, timedelta
from decimal import Decimal

company = Company.objects.get(id=1)

invoice = Invoice.objects.create(
    company=company,
    period_start=date(2024, 11, 1),
    period_end=date(2024, 11, 30),
    amount=Decimal('15000.00'),
    due_date=date(2024, 12, 14),
    status='draft',
    notes='Monthly subscription',
)
print(f"Created: {invoice.invoice_number}")
```

### 5. Create a Payment Record
```python
from estateApp.models import Payment

payment = Payment.objects.create(
    invoice=invoice,
    amount=Decimal('16125.00'),  # Including tax
    payment_method='stripe',
    payment_reference='ch_1234567890',
    notes='Via Stripe',
)
# Invoice is auto-marked as paid if total_paid >= total_amount
```

### 6. Record a Charge
```python
from estateApp.models import BillingRecord
from datetime import date

record = BillingRecord.objects.create(
    company=company,
    subscription_plan=plan,
    invoice=invoice,
    charge_type='subscription',
    amount=Decimal('15000.00'),
    description='Monthly subscription charge',
    status='pending',
    stripe_charge_id='ch_1234567890',
    billing_period_start=date(2024, 11, 1),
    billing_period_end=date(2024, 11, 30),
)

# Mark as processed
record.mark_processed()

# Or refund it
record.refund(reason='Customer requested cancellation')
```

### 7. Access API Endpoints

```bash
# Get current subscription
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/api/subscription/

# List plans
curl https://api.example.com/api/subscription/plans/

# Upgrade subscription
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier": "professional"}' \
  https://api.example.com/api/subscription/upgrade/

# Get billing history
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/api/subscription/billing_history/

# List invoices
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/api/invoices/

# Get invoice details
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/api/invoices/1/
```

### 8. Run Billing Tasks Manually

```python
from adminSupport.tasks import (
    generate_monthly_invoices,
    check_overdue_invoices,
    send_subscription_renewal_reminders,
    handle_expired_subscriptions,
)

# Generate invoices for all active companies
result = generate_monthly_invoices()
print(result)  # {'status': 'success', 'invoices_created': 5}

# Check for overdue invoices and send reminders
result = check_overdue_invoices()
print(result)  # {'status': 'success', 'reminders_sent': 2}

# Send renewal reminders (7 days before expiry)
result = send_subscription_renewal_reminders()
print(result)  # {'status': 'success', 'reminders_sent': 3}

# Suspend expired subscriptions
result = handle_expired_subscriptions()
print(result)  # {'status': 'success', 'suspended': 1}
```

### 9. Query Billing Records
```python
from estateApp.models import BillingRecord

company = Company.objects.get(id=1)

# All charges for company
records = BillingRecord.objects.filter(company=company)

# Processed charges this month
from django.utils import timezone
from datetime import date
this_month_start = date.today().replace(day=1)

records = BillingRecord.objects.filter(
    company=company,
    status='processed',
    created_at__gte=this_month_start,
)

# Failed payments
failed = BillingRecord.objects.filter(
    company=company,
    status='failed',
)

# Total revenue from this company
total_revenue = sum(r.amount for r in records.filter(status='processed'))
```

### 10. Send Manual Email Notification

```python
from estateApp.notifications.email_service import EmailService
from estateApp.models import Invoice

invoice = Invoice.objects.get(id=1)

# Send payment reminder
EmailService.send_email(
    subject=f"Payment Reminder - Invoice {invoice.invoice_number}",
    template_name='emails/invoice_overdue_reminder.html',
    context={
        'invoice': invoice,
        'company': invoice.company,
        'days_overdue': 5,
    },
    recipient_list=[invoice.company.billing_email or invoice.company.email],
)

# Or payment received notification
EmailService.send_email(
    subject="Payment Received",
    template_name='emails/payment_received.html',
    context={
        'invoice': invoice,
        'amount': invoice.total_amount,
        'payment_date': timezone.now(),
    },
    recipient_list=[invoice.company.billing_email or invoice.company.email],
)
```

---

## Database Queries

### Get All Companies by Subscription Status
```sql
SELECT * FROM estateApp_company 
WHERE subscription_status = 'active'
ORDER BY subscription_ends_at ASC;
```

### Get Revenue by Tier
```sql
SELECT 
  subscription_tier,
  COUNT(*) as count,
  SUM(CAST(amount AS DECIMAL)) as total_revenue
FROM estateApp_company c
LEFT JOIN estateApp_billingrecord b ON c.id = b.company_id
WHERE b.status = 'processed'
GROUP BY subscription_tier;
```

### Get Overdue Invoices
```sql
SELECT * FROM estateApp_invoice
WHERE status IN ('issued', 'overdue')
  AND due_date < DATE('today')
ORDER BY due_date ASC;
```

### Get Subscription Expiring Soon
```sql
SELECT c.company_name, c.subscription_ends_at
FROM estateApp_company c
WHERE subscription_status = 'active'
  AND subscription_ends_at < DATE('today') + INTERVAL '7 days'
  AND subscription_ends_at > DATE('today')
ORDER BY subscription_ends_at ASC;
```

---

## Troubleshooting

### Q: How do I enable/disable a subscription plan?
```python
plan = SubscriptionPlan.objects.get(tier='enterprise')
plan.is_active = False  # Disable
plan.save()
```

### Q: How do I prevent a company from being able to create plots?
```python
company = Company.objects.get(id=1)
company.current_plots_count = company.max_plots
company.save()
```

### Q: How do I manually mark a company as trial active?
```python
from django.utils import timezone
from datetime import timedelta

company = Company.objects.get(id=1)
company.subscription_status = 'trial'
company.trial_ends_at = timezone.now() + timedelta(days=14)
company.save()
```

### Q: How do I cancel a subscription?
```python
company = Company.objects.get(id=1)
company.subscription_status = 'cancelled'
company.save()
```

### Q: How do I process a refund?
```python
record = BillingRecord.objects.get(id=1)
record.refund(reason='Customer requested cancellation')
# Updates status to 'refunded' and processed_at
```

### Q: How do I check Stripe webhook logs?
```python
import logging
logger = logging.getLogger('stripe_webhooks')
# Check application logs for stripe_webhooks entries
```

---

## API Examples

### JavaScript/Fetch

```javascript
// Get subscription info
async function getSubscription() {
  const response = await fetch('/api/subscription/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}

// Upgrade subscription
async function upgradeSubscription(tier) {
  const response = await fetch('/api/subscription/upgrade/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      tier: tier,
      success_url: 'https://dashboard.example.com/success',
      cancel_url: 'https://dashboard.example.com/cancel'
    })
  });
  return response.json();
}

// Get billing history
async function getBillingHistory() {
  const response = await fetch('/api/subscription/billing_history/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}
```

### Python/Requests

```python
import requests

token = 'your_api_token'
headers = {'Authorization': f'Bearer {token}'}

# Get subscription
response = requests.get('https://api.example.com/api/subscription/', headers=headers)
subscription = response.json()
print(subscription)

# List plans
response = requests.get('https://api.example.com/api/subscription/plans/')
plans = response.json()

# Upgrade
response = requests.post(
    'https://api.example.com/api/subscription/upgrade/',
    headers=headers,
    json={'tier': 'professional'}
)
result = response.json()
print(result['checkout_url'])  # Redirect user to Stripe
```

---

## Performance Tips

1. **Cache subscription plans** - They don't change often
2. **Use database indexes** - BillingRecord has indexes on key fields
3. **Batch invoice generation** - Use bulk_create for monthly invoices
4. **Async webhooks** - Process Stripe events asynchronously
5. **Archive old invoices** - Move to archive after 2 years

---

## Security Reminders

- ✅ Always verify Stripe webhook signatures
- ✅ Never log payment card data
- ✅ Use HTTPS for all payment URLs
- ✅ Validate amounts in kobo before Stripe
- ✅ Keep STRIPE_SECRET_KEY in environment, never in code
- ✅ Authenticate all billing API endpoints
- ✅ Log all payment events for audit trail

---

Generated: November 20, 2024
