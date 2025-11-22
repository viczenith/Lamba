# 🚀 QUICK START GUIDE - Multi-Tenant SaaS Platform

## ⚡ Get Started in 5 Minutes

### **Step 1: Install Dependencies**
```bash
# Already installed, but ensure these are in requirements.txt:
# - Django
# - djangorestframework
# - channels
# - channels-redis
```

### **Step 2: Run Migrations**
```bash
python manage.py makemigrations superAdmin
python manage.py migrate
```

### **Step 3: Initialize Platform**
```bash
# Create subscription plans
python manage.py init_subscription_plans

# Create super admin user
python manage.py create_super_admin
# Follow prompts to enter:
#   Email: admin@platform.com
#   Password: YourSecurePassword123!
#   Full Name: Platform Administrator
#   Level: super
```

### **Step 4: Start Server**
```bash
python manage.py runserver
```

### **Step 5: Access Super Admin**
Open browser: `http://localhost:8000/super-admin/`

Login with your super admin credentials.

---

## 🎯 What You Can Do Now

### **As Super Admin:**
✅ View all companies on the platform
✅ Monitor subscriptions and billing
✅ Generate analytics reports
✅ Suspend/activate companies
✅ View audit logs
✅ Manage feature flags
✅ Configure platform settings

### **As Company Admin:**
✅ Manage your company's properties
✅ Add clients and marketers
✅ Track sales and allocations
✅ View subscription status
✅ Upgrade/downgrade plan

### **As Client:**
✅ View all properties across companies
✅ Track investments in one dashboard
✅ See ROI and projections
✅ Manage profile

### **As Marketer:**
✅ Affiliate with multiple companies
✅ Track commissions from all sources
✅ View sales performance
✅ Manage client relationships

---

## 🔧 Key URLs

| URL | Description | Access Level |
|-----|-------------|--------------|
| `/super-admin/` | Master control dashboard | Super Admin |
| `/admin/` | Django admin interface | Super Admin |
| `/dashboard/` | Company dashboard | Company Admin |
| `/api/` | REST API endpoints | All (with auth) |
| `/` | Main application | All users |

---

## 📊 Default Subscription Plans

After running `init_subscription_plans`:

1. **Trial** - Free, 14 days
   - 10 plots, 2 agents
   - Testing the platform

2. **Starter** - ₦15,000/month
   - 50 plots, 5 agents
   - Small agencies

3. **Professional** - ₦35,000/month
   - 500 plots, 20 agents
   - Growing businesses

4. **Enterprise** - ₦75,000/month
   - Unlimited everything
   - Large organizations

---

## 🔒 Security Notes

- All companies are **completely isolated** by default
- Super admins can access all data with `?company_id=X` parameter
- All actions are **logged automatically**
- Subscriptions are **enforced by middleware**
- API access via **API keys** in headers

---

## 📈 Monitoring

### **Generate Daily Analytics**
```bash
# Run manually or add to cron
python manage.py generate_analytics
```

### **View Analytics**
Navigate to: `/super-admin/analytics/`

See:
- Company growth trends
- User statistics
- Revenue tracking (MRR, ARR)
- Daily metrics

---

## 🆘 Troubleshooting

### **Can't access super admin?**
Make sure user has `super_admin_profile`:
```python
python manage.py shell

from django.contrib.auth import get_user_model
from superAdmin.models import SuperAdminUser

User = get_user_model()
user = User.objects.get(email='admin@platform.com')

# Create super admin profile
SuperAdminUser.objects.create(
    user=user,
    admin_level='super',
    can_access_all_companies=True,
    can_modify_subscriptions=True,
    can_view_financials=True,
    can_manage_users=True
)
```

### **Subscription not working?**
Check if company has subscription:
```python
from estateApp.models import Company

company = Company.objects.get(company_name='Your Company')
print(company.subscription_details)  # Should show subscription
```

### **Middleware errors?**
Verify in `settings.py` that middleware order is correct (after AuthenticationMiddleware).

---

## 🎯 Next Steps

1. **Customize Platform Settings**
   - Go to `/super-admin/settings/`
   - Update platform name, logo, prices

2. **Invite Companies**
   - Share registration link
   - Monitor onboarding progress

3. **Set Up Payment Gateway**
   - Add Stripe/Paystack credentials
   - Enable auto-billing

4. **Enable Features**
   - Go to `/super-admin/feature-flags/`
   - Enable marketplace, AI matching, etc.

---

## 📚 Documentation

- **Full Guide:** `MULTI_TENANT_RESTRUCTURING_COMPLETE.md`
- **Vision:** `multi-infra.md`
- **API Docs:** `/api/docs/` (when implemented)

---

## 🎉 You're All Set!

Your multi-tenant SaaS platform is ready to **onboard companies** and **scale to thousands of users**!

**Questions?** Check the full documentation or Django admin panel.

---

**Happy Building! 🏗️🚀**
