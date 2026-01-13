# SuperAdmin Dashboard - Quick Setup Guide

## 🚀 Quick Start (3 Steps)

### Step 1: Update Main URL Configuration

Edit `estateProject/urls.py` and add the SuperAdmin URLs:

```python
from django.urls import path, include

urlpatterns = [
    # ... your existing patterns ...
    
    # SuperAdmin Comprehensive Dashboard
    path('super-admin/', include('superAdmin.admin_urls', namespace='superadmin')),
]
```

### Step 2: Create a SuperAdmin User

**Option A: Via Django Shell**
```bash
python manage.py shell
```

Then run:
```python
from django.contrib.auth import get_user_model

User = get_user_model()

# Get or create admin user
user, created = User.objects.get_or_create(
    email='superadmin@yourdomain.com',
    defaults={
        'username': 'superadmin',
        'first_name': 'Super',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True,
    }
)

# Set as system admin
user.is_system_admin = True
user.admin_level = 'system'

# Set password
user.set_password('YourSecurePassword123!')
user.save()

print(f"SuperAdmin user {'created' if created else 'updated'}: {user.email}")
```

**Option B: Via Django Admin**
1. Login to Django Admin (`/admin/`)
2. Go to Users
3. Edit an existing user or create new
4. Check these boxes:
   - ✅ Is system admin
   - ✅ Is superuser
   - ✅ Is staff
5. Set "Admin level" to "system"
6. Save

### Step 3: Access the Dashboard

1. Run your server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to: `http://127.0.0.1:8000/super-admin/`

3. Login with your SuperAdmin credentials

4. You should see the comprehensive dashboard!

---

## ✅ Verification Checklist

After setup, verify these features work:

- [ ] Dashboard loads with metrics
- [ ] Charts display (revenue and signups)
- [ ] Companies page loads and filters work
- [ ] Users page shows all users across companies
- [ ] Subscriptions page displays correctly
- [ ] Billing page shows all transactions
- [ ] Analytics page loads with calculations
- [ ] Company action buttons work (activate/suspend)
- [ ] Pagination works on all list pages
- [ ] Search and filters function correctly

---

## 🎨 Customization (Optional)

### Change Chart Colors

Edit `main_dashboard.html`, find the Chart.js configuration:

```javascript
// Revenue Chart
new Chart(revenueCtx, {
    data: {
        datasets: [{
            borderColor: 'rgb(79, 70, 229)',  // Change this
            backgroundColor: 'rgba(79, 70, 229, 0.1)',  // And this
        }]
    }
});
```

### Adjust Pagination

In `comprehensive_views.py`, change `paginate_by`:

```python
class CompanyManagementView(SystemAdminRequiredMixin, ListView):
    paginate_by = 100  # Default is 50
```

### Modify Metrics Period

In `SuperAdminDashboardView.get_context_data()`:

```python
# Change from 30 days to 60 days
month_ago = today - timedelta(days=60)
```

---

## 🔧 Troubleshooting

### Dashboard Not Loading?

**Check 1:** URL configuration correct?
```bash
python manage.py show_urls | grep super-admin
```

**Check 2:** User has correct permissions?
```python
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='your@email.com')
print(f"Is system admin: {user.is_system_admin}")
print(f"Admin level: {user.admin_level}")
```

**Check 3:** Templates exist?
```bash
ls superAdmin/templates/superadmin/comprehensive/
```

### "Access Denied" Error?

Make sure user has:
- `is_system_admin = True`
- OR `admin_level = 'system'`
- OR `is_superuser = True`

### Charts Not Showing?

Check browser console for errors. Make sure CDNs are accessible:
- Tailwind CSS CDN
- Bootstrap Icons CDN
- Chart.js CDN

Try accessing: https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js

### API Returning 403?

Ensure CSRF token is included in POST requests. Check browser dev tools network tab.

---

## 📊 What You Get

### Dashboard Features:
✅ Real-time platform statistics  
✅ Revenue and growth charts  
✅ Company management with filters  
✅ User management across all companies  
✅ Subscription oversight  
✅ Billing transaction tracking  
✅ Advanced analytics and metrics  
✅ System health monitoring  
✅ Export capabilities (CSV)  

### Management Actions:
✅ Activate/Suspend companies  
✅ Extend subscriptions  
✅ Reset trial periods  
✅ Manual payment verification  
✅ Company deletion  
✅ Bulk operations  

---

## 📖 Full Documentation

For detailed documentation, see: [SUPERADMIN_COMPREHENSIVE_GUIDE.md](SUPERADMIN_COMPREHENSIVE_GUIDE.md)

---

## 🎉 You're All Set!

Your SuperAdmin Dashboard is now ready to use. You can manage all companies, users, subscriptions, and monitor your platform's health from one comprehensive interface.

**Default Access:** `http://yoursite.com/super-admin/`

---

## Next Steps

1. **Create additional admin users** if needed
2. **Set up email notifications** for alerts
3. **Configure backup schedule** for audit logs
4. **Review security settings** and access controls
5. **Test all features** with real data

Happy managing! 🚀
