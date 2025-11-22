# 🚀 QUICK START: SuperAdmin Platform Management

## 30-Second Setup

### Step 1: Run Migrations (if needed)
```bash
cd "c:\Users\HP\Documents\VictorGodwin\RE\Multi-Tenant Architecture\RealEstateMSApp\estateProject"
python manage.py migrate
```

### Step 2: Create System Administrator
```bash
python manage.py shell
```
```python
from estateApp.models import CustomUser

# Create platform admin
admin = CustomUser.objects.create_superuser(
    email='admin@realestate.com',
    full_name='Platform Administrator',
    phone='08012345678',
    password='Admin@2024'
)
admin.is_system_admin = True
admin.admin_level = 'system'
admin.company_profile = None  # Platform-level, not company-specific
admin.save()

print(f"✅ System Admin: {admin.email}")
exit()
```

### Step 3: Access Platform Dashboard
1. Start server: `python manage.py runserver`
2. Visit: `http://127.0.0.1:8000/super-admin/`
3. Login with `admin@realestate.com` / `Admin@2024`
4. Manage all companies, users, subscriptions

---

## 🎯 What You Can Do

### Platform Management:
- ✅ View all companies across the platform
- ✅ Manage subscriptions and billing
- ✅ Monitor system analytics and metrics
- ✅ Suspend/activate companies
- ✅ View audit logs for compliance
- ✅ Configure platform settings

---

## 🔐 Creating Different Admin Types

### System Admin (Platform-Wide):
```python
user.is_system_admin = True
user.admin_level = 'system'
user.company_profile = None  # No company
```

### Company Admin (Single Company):
```python
from estateApp.models import Company

company = Company.objects.get(company_name='Example Company')

user.is_system_admin = False
user.admin_level = 'company'
user.company_profile = company  # Tied to one company
```

---

## 🛠️ Using in Your Code

### Protect Views:
```python
from superAdmin.decorators import require_system_admin

@require_system_admin
def my_admin_view(request):
    return render(request, 'admin_page.html')
```

### Protect APIs:
```python
from superAdmin.permissions import IsSystemAdmin
from rest_framework.permissions import IsAuthenticated

class PlatformAPIView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    
    def list(self, request):
        # Only system admins can access
        pass
```

---

## 📊 Check It's Working

### Verify User:
```bash
python manage.py shell
```
```python
from estateApp.models import CustomUser

admin = CustomUser.objects.get(email='admin@realestate.com')
print(f"Is System Admin: {admin.is_system_admin}")
print(f"Admin Level: {admin.admin_level}")
print(f"Company: {admin.company_profile}")  # Should be None
```

### View Audit Logs:
```python
from superAdmin.models import SystemAuditLog

logs = SystemAuditLog.objects.all()[:10]
for log in logs:
    print(f"{log.created_at}: {log.action} by {log.user}")
```

---

## 🎉 That's It!

Your platform admin system is now configured and ready to manage your multi-tenant real estate SaaS platform.

**Dashboard**: `http://127.0.0.1:8000/super-admin/`  
**API Docs**: See `API_DOCUMENTATION.md`  
**Full Details**: See `TENANT_ADMIN_MIGRATION_TO_SUPERADMIN.md`
