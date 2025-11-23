# Lamba Subscription System - Complete Implementation Guide

## Overview
The subscription system is now fully integrated with the company registration workflow. When companies register, they select a subscription tier which determines their feature limits.

---

## 📋 Subscription Tiers

### 1. STARTER - ₦70,000/month (₦700,000/year - Save 2 months!)
**Description:** For Small Companies

**Features:**
- 2 Estate Properties
- 30 Allocations
- 30 Clients
- 20 Affiliates
- 1,000 API calls/day
- Basic analytics
- Email support

**Best For:** Small real estate agencies, local property managers

---

### 2. PROFESSIONAL - ₦100,000/month (₦1,000,000/year - Save 2 months!)
**Description:** For Growing Companies | **PREFERRED PLAN**

**Features:**
- 5 Estate Properties
- 80 Allocations
- 80 Clients
- 30 Affiliates
- 10,000 API calls/day
- Advanced analytics
- Priority support
- Custom branding

**Best For:** Growing real estate companies, multi-location operations

---

### 3. ENTERPRISE - ₦150,000/month (₦1,500,000/year - Save 2 months!)
**Description:** Preferred Package Plan for Large Organizations

**Features:**
- Unlimited Estate Properties
- Unlimited Allocations
- Unlimited Clients
- Unlimited Affiliates
- Unlimited API calls
- Advanced analytics
- Dedicated support
- Custom branding
- SSO Integration
- Multi-currency support

**Best For:** Large enterprises, national/international operations

---

## 🔧 How the System Works

### Registration Flow

1. **Company Registration Modal** (`unified_login.html`)
   - User selects subscription tier using clickable radio buttons
   - Each tier displays pricing, features, and limits
   - Selected tier is sent to backend via POST `subscription_tier` parameter

2. **Backend Processing** (`views.py::company_registration`)
   ```python
   subscription_tier = request.POST.get('subscription_tier', 'professional')
   # Validate tier
   if subscription_tier not in ['starter', 'professional', 'enterprise']:
       subscription_tier = 'professional'
   ```

3. **Company Creation**
   - Company is created with selected `subscription_tier`
   - Trial period: 14 days
   - Limits automatically sync based on SubscriptionPlan model

4. **Auto-Sync Limits** (`models.py::Company.sync_plan_limits()`)
   - When company is saved, limits are automatically synchronized
   - Fetches limits from SubscriptionPlan model
   - Falls back to defaults if plan doesn't exist

---

## 📊 Database Models

### SubscriptionPlan Model
```python
class SubscriptionPlan(models.Model):
    tier: CharField ('starter', 'professional', 'enterprise')
    name: CharField (e.g., "Starter")
    description: TextField
    monthly_price: DecimalField (₦)
    annual_price: DecimalField (₦)
    max_plots: IntegerField
    max_agents: IntegerField
    max_api_calls_daily: IntegerField
    features: JSONField (flexible features dict)
    is_active: BooleanField
```

### Company Model Subscription Fields
```python
subscription_tier: CharField (default='trial')
subscription_status: CharField ('trial', 'active', 'suspended', 'cancelled')
trial_ends_at: DateTimeField
subscription_ends_at: DateTimeField
max_plots: PositiveIntegerField (synced from plan)
max_agents: PositiveIntegerField (synced from plan)
max_api_calls_daily: PositiveIntegerField (synced from plan)
```

---

## 🚀 Key Methods

### Company Model Methods

#### `sync_plan_limits()`
Automatically syncs company limits based on subscription tier.
```python
company.sync_plan_limits()
# or automatically called on save()
company.save()
```

#### `get_subscription_plan()`
Returns the SubscriptionPlan object.
```python
plan = company.get_subscription_plan()
# Returns: SubscriptionPlan(tier='professional', ...)
```

#### `get_feature_limits()`
Returns all feature limits for the company.
```python
limits = company.get_feature_limits()
# Returns: {
#   'estate_properties': 5,
#   'allocations': 80,
#   'clients': 80,
#   'affiliates': 30,
#   'max_plots': 5,
#   'max_agents': 10,
#   'max_api_calls_daily': 10000
# }
```

#### `can_add_client()`
Check if company can add more clients.
```python
can_add, message = company.can_add_client()
if not can_add:
    return error_response(message)
```

#### `can_add_affiliate()`
Check if company can add more affiliates.
```python
can_add, message = company.can_add_affiliate()
```

#### `can_create_allocation()`
Check if company can create more plot allocations.
```python
can_create, message = company.can_create_allocation()
```

#### `can_create_estate()`
Check if company can create more estate properties.
```python
can_create, message = company.can_create_estate()
```

#### `get_usage_stats()`
Get current usage statistics.
```python
stats = company.get_usage_stats()
# Returns: {
#   'estates': 2,
#   'allocations': 45,
#   'clients': 28,
#   'affiliates': 5
# }
```

---

## ✅ Feature Checklist

### ✅ Completed
- [x] Subscription plans model with correct pricing
- [x] Plan selection UI in registration modal
- [x] Radio buttons are clickable
- [x] Pricing updated to specifications
- [x] Company limits sync based on tier
- [x] Feature limit enforcement methods
- [x] Usage stats calculation
- [x] 14-day trial setup
- [x] Trial expiration logic

### 🔄 Next Steps
- [ ] Subscription management dashboard for admins
- [ ] Payment processing integration
- [ ] Subscription upgrade/downgrade
- [ ] Usage monitoring and alerts
- [ ] Automated trial expiration handler
- [ ] Subscription renewal workflow

---

## 🔐 Security & Isolation

### Tenancy Isolation
- Each company has unique `slug` field for routing
- Company-level admins can only manage their own company
- Data queries filtered by `company` ForeignKey
- API calls authenticated and company-scoped

### Subscription Enforcement
- Limits checked before creating resources
- Graceful error messages when limits reached
- Prevents over-allocation through validation

---

## 📱 Frontend Integration

### Registration Modal (unified_login.html)
```html
<!-- Plan Selection -->
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem">
    <!-- Radio buttons with improved styling -->
    <input type="radio" name="subscription_tier" id="planStarter" 
           value="starter" checked />
    <label for="planStarter" ...>Starter Plan</label>
    
    <!-- Professional (PREFERRED) -->
    <input type="radio" name="subscription_tier" id="planProfessional" 
           value="professional" />
    <label for="planProfessional" ...>Professional Plan</label>
    
    <!-- Enterprise -->
    <input type="radio" name="subscription_tier" id="planEnterprise" 
           value="enterprise" />
    <label for="planEnterprise" ...>Enterprise Plan</label>
</div>
```

### CSS Styling for Radio Buttons
```css
input[name="subscription_tier"]:checked+label {
    border-color: #667eea;
    background: linear-gradient(...);
    transform: scale(1.02);
    box-shadow: 0 6px 20px rgba(102,126,234,.2);
}

input[name="subscription_tier"]:hover+label {
    border-color: #a5b4fc;
    background: rgba(102,126,234,.03);
}
```

---

## 🧪 Testing Plan

### Manual Testing Steps

1. **Test Registration with Each Tier**
   - Navigate to registration modal
   - Select Starter plan → Verify limits in DB
   - Select Professional → Verify limits
   - Select Enterprise → Verify unlimited

2. **Test Trial Period**
   - Register new company
   - Verify trial_ends_at = now + 14 days
   - Verify subscription_status = 'trial'

3. **Test Limit Enforcement**
   - Use `company.get_usage_stats()` to check current usage
   - Try to exceed limits
   - Verify error messages

### Sample Test Code
```python
# Test in Django Shell
from estateApp.models import Company, SubscriptionPlan

# Create test company
company = Company.objects.create(
    company_name="Test Company",
    subscription_tier="professional",
    # ... other fields
)

# Check limits
limits = company.get_feature_limits()
print(f"Can create estates: {company.can_create_estate()}")
print(f"Current usage: {company.get_usage_stats()}")
```

---

## 🛠️ Configuration

### Database Setup
```bash
python manage.py migrate
python setup_subscription_plans.py
```

### Environment Variables
Add to `.env`:
```
SUBSCRIPTION_TRIAL_DAYS=14
STRIPE_PUBLISHABLE_KEY=your_key
STRIPE_SECRET_KEY=your_key
```

---

## 📞 Support

For subscription system issues:
1. Check database for SubscriptionPlan entries
2. Verify company `subscription_tier` matches existing plan
3. Check `sync_plan_limits()` is called on company creation
4. Review trial expiration in `is_trial_active()`

---

## 📚 Related Files

- **Models:** `estateApp/models.py` (Company, SubscriptionPlan)
- **Views:** `estateApp/views.py` (company_registration)
- **Templates:** `estateApp/templates/auth/unified_login.html`
- **Setup:** `setup_subscription_plans.py`
- **Documentation:** This file

---

## 🎯 Key Takeaways

✨ **Subscription System is production-ready with:**
- ✅ Three pricing tiers with correct pricing
- ✅ Automatic limit synchronization
- ✅ Feature-based enforcement
- ✅ 14-day trial period
- ✅ Flexible feature flags
- ✅ Usage statistics tracking
- ✅ Graceful limit enforcement

**Next Priority:** Payment integration and subscription management dashboard
