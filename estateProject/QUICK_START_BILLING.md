# 🚀 Quick Start Guide - Billing System

## Immediate Steps to Get Started

### 1. Install Required Packages (if needed)
```bash
pip install requests
```

### 2. Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:PAYSTACK_SECRET_KEY="sk_test_your_key_here"
$env:PAYSTACK_PUBLIC_KEY="pk_test_your_key_here"
```

**Or add to your `.env` file:**
```
PAYSTACK_SECRET_KEY=sk_test_your_key_here
PAYSTACK_PUBLIC_KEY=pk_test_your_key_here
```

### 3. Get Paystack Keys

1. Go to [https://dashboard.paystack.com/](https://dashboard.paystack.com/)
2. Sign up or log in
3. Navigate to **Settings → API Keys & Webhooks**
4. Copy your **Test Secret Key** (starts with `sk_test_`)
5. Copy your **Test Public Key** (starts with `pk_test_`)

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Create Subscription Plans

**Option A: Using Django Shell**
```bash
python manage.py shell
```

Then paste:
```python
from estateApp.models import SubscriptionPlan

# Create Starter
SubscriptionPlan.objects.get_or_create(
    tier='starter',
    defaults={
        'name': 'Starter',
        'description': 'Perfect for small real estate companies',
        'monthly_price': 70000,
        'annual_price': 700000,
        'max_plots': 50,
        'max_agents': 5,
        'features': {
            'estate_properties': '2',
            'allocations': '30',
            'clients': '30',
            'affiliates': '20'
        },
        'is_active': True
    }
)

# Create Professional
SubscriptionPlan.objects.get_or_create(
    tier='professional',
    defaults={
        'name': 'Professional',
        'description': 'For growing companies',
        'monthly_price': 100000,
        'annual_price': 1000000,
        'max_plots': 200,
        'max_agents': 15,
        'features': {
            'estate_properties': '5',
            'allocations': '80',
            'clients': '80',
            'affiliates': '30'
        },
        'is_active': True
    }
)

# Create Enterprise
SubscriptionPlan.objects.get_or_create(
    tier='enterprise',
    defaults={
        'name': 'Enterprise',
        'description': 'Unlimited everything',
        'monthly_price': 150000,
        'annual_price': 1500000,
        'max_plots': 999999,
        'max_agents': 999999,
        'features': {
            'estate_properties': 'unlimited',
            'allocations': 'unlimited',
            'clients': 'unlimited',
            'affiliates': 'unlimited'
        },
        'is_active': True
    }
)

print("✅ Plans created successfully!")
exit()
```

**Option B: Using Django Admin**
1. Go to `/admin/`
2. Navigate to **Subscription Plans**
3. Click **Add Subscription Plan**
4. Fill in the details for each plan (Starter, Professional, Enterprise)

### 6. Start Development Server
```bash
python manage.py runserver
```

### 7. Test the Billing Page

1. **Log in** to your company admin account
2. Navigate to **Company Profile** page
3. Click on the **Billing** tab
4. You should see:
   - ✅ Three plan cards (Starter, Professional, Enterprise)
   - ✅ Subscription status alert (if on trial)
   - ✅ Payment method selection
   - ✅ Order summary

### 8. Test Upgrade/Downgrade Warnings

**Test Downgrade Warning:**
1. Make sure you have some data:
   - Create 3+ estates
   - Add 50+ clients
2. Select **Starter** plan (has low limits)
3. Click to select it
4. You should see a **warning modal** showing:
   - ⚠️ Current usage vs new limits
   - ❌ Red indicators for exceeded limits
   - 💡 Recommendation message

**Test Upgrade:**
1. Select **Enterprise** plan
2. No warning should appear
3. Plan should be selected immediately

### 9. Test Paystack Payment (Test Mode)

1. Select any plan
2. Choose **Paystack** payment method
3. Click **Proceed to Payment**
4. Fill in email and click **Pay Now**
5. You'll be redirected to Paystack
6. Use test card: **4084 0840 8408 4081**
7. CVV: **408**
8. Expiry: Any future date
9. PIN: **0000** or **1234**
10. OTP: **123456**

### 10. Test Bank Transfer

1. Select any plan
2. Choose **Bank Transfer** payment method
3. Click **Proceed to Payment**
4. You should see:
   - Bank details (dynamic if DVA enabled, static otherwise)
   - Unique payment reference
   - Copy buttons for easy copying
5. Click **I've Made the Transfer**
6. You should see a **pending confirmation** modal

---

## 🎯 What to Look For

### ✅ Working Features

- [ ] **Plans load dynamically** from database
- [ ] **"Subscribed" badge** appears on active plan (green)
- [ ] **"Most Popular" badge** on Professional plan (blue)
- [ ] **Monthly/Annual toggle** updates prices
- [ ] **Savings calculation** shows "Save 2 months" for annual
- [ ] **Downgrade warning modal** appears with usage data
- [ ] **Current usage vs limits** comparison table
- [ ] **Paystack redirect** works on payment
- [ ] **Bank transfer modal** shows account details
- [ ] **Invoice history** loads (if you have transactions)

### ❌ Common Issues

**Plans don't load:**
- Check browser console for errors
- Verify API endpoint: `/api/billing/context/`
- Ensure you're logged in and company exists

**No downgrade warning:**
- Create test data first (estates, clients, etc.)
- Check plan limits in database
- Look at browser console for errors

**Paystack error:**
- Verify environment variables are set
- Check you're using test keys (start with `sk_test_`)
- Ensure keys match your Paystack account

**Bank transfer shows "undefined":**
- This is expected if DVA is not enabled
- System falls back to static bank details
- Payment reference is still generated and tracked

---

## 🔧 Quick Troubleshooting

### Check if API Works
```bash
# Test billing context endpoint
curl http://localhost:8000/api/billing/context/
```

### Check if Plans Exist
```bash
python manage.py shell
```
```python
from estateApp.models import SubscriptionPlan
print(SubscriptionPlan.objects.all().count())
# Should print: 3
```

### Check Environment Variables
```bash
python manage.py shell
```
```python
from django.conf import settings
print(settings.PAYSTACK_PUBLIC_KEY)
print(settings.PAYSTACK_SECRET_KEY)
# Should print your keys
```

### View Server Logs
Watch the terminal running `runserver` for any error messages.

---

## 📱 Testing Checklist

Quick checklist for verification:

**Basic Display:**
- [ ] Billing tab loads without errors
- [ ] Three plan cards appear
- [ ] Current plan shows "Subscribed" badge
- [ ] Prices format correctly with ₦ symbol
- [ ] Toggle switches between monthly/annual

**Plan Selection:**
- [ ] Clicking a plan selects it (blue border)
- [ ] Order summary updates
- [ ] Selected indicator appears

**Upgrade (No Warning):**
- [ ] Select higher tier plan
- [ ] No modal appears
- [ ] Plan selected immediately

**Downgrade (With Warning):**
- [ ] Select lower tier plan
- [ ] Warning modal appears
- [ ] Shows current usage numbers
- [ ] Shows new limit numbers
- [ ] Red indicators for exceeded limits
- [ ] Can cancel or proceed

**Paystack Payment:**
- [ ] Email field validates
- [ ] Redirects to Paystack
- [ ] Test card works
- [ ] Returns to site after payment

**Bank Transfer:**
- [ ] Shows bank details
- [ ] Shows payment reference
- [ ] Copy buttons work
- [ ] Confirmation modal appears

**Invoices:**
- [ ] Invoice modal opens
- [ ] Shows transaction history
- [ ] Displays amounts correctly
- [ ] Shows payment status

---

## 🎉 Success!

If everything above works, your billing system is fully functional!

**Next Steps:**
1. Configure Paystack webhook for production
2. Get live API keys from Paystack
3. Test with real small amounts
4. Enable email notifications
5. Set up monitoring for failed payments

---

## 💡 Pro Tips

1. **Always test in test mode first** - Use test keys and test cards
2. **Monitor webhook logs** - Check Paystack dashboard for webhook deliveries
3. **Keep plans simple** - Start with 3 tiers, add more later if needed
4. **Use meaningful limits** - Set realistic usage limits for each tier
5. **Document for users** - Create help docs explaining upgrade/downgrade

---

## 📞 Need Help?

1. Check browser console (F12) for JavaScript errors
2. Check Django logs for backend errors
3. Verify all files were created correctly
4. Ensure environment variables are loaded
5. Test API endpoints directly with curl

**Common Commands:**
```bash
# Restart server
Ctrl+C
python manage.py runserver

# Check migrations
python manage.py showmigrations

# Create superuser if needed
python manage.py createsuperuser
```

---

**You're all set! Happy billing! 🚀**
