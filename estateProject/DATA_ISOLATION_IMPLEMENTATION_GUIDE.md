# 🔐 Data Isolation & Company Admin Tenancy - Implementation & Deployment Guide

## 📋 Quick Summary

This implementation provides:

✅ **Complete Data Isolation** - Company A CANNOT access Company B data  
✅ **Subscription-Bound Access** - All company features tied to active subscription  
✅ **Isolated Company Admin Tenancy** - Admins are tenant-scoped, NOT super users  
✅ **System Master Admin Only** - One super admin controls entire platform  
✅ **Role-Based Access** - System Master Admin, Company Admin, Client, Marketer  
✅ **Middleware Enforcement** - Automatic on every request  
✅ **Query-Level Protection** - Custom managers prevent data leaks  
✅ **Grace Period & Read-Only Mode** - 7-day grace period after subscription expires  
✅ **API Isolation** - REST endpoints automatically scoped to company  
✅ **Audit Trail** - All admin actions logged for compliance  

---

## 🚀 Phase-by-Phase Implementation

### Phase 1: Update Settings.py

**File**: `estateProject/settings.py`

```python
# Add to MIDDLEWARE (Order is CRITICAL)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # 🔐 MULTI-TENANT MIDDLEWARE (MUST be after auth)
    'estateApp.middleware.TenantIsolationMiddleware',           # ✅ NEW
    'estateApp.middleware.QuerysetIsolationMiddleware',         # ✅ NEW
    'estateApp.middleware.SubscriptionEnforcementMiddleware',   # ✅ NEW
    'estateApp.middleware.ReadOnlyModeMiddleware',              # ✅ NEW
    'estateApp.middleware.AuditLoggingMiddleware',              # ✅ NEW (optional)
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Tenancy settings
MULTI_TENANT_ENABLED = True
TENANT_ISOLATION_STRICT = True  # Strict mode: fail on cross-tenant access
TENANT_DEFAULT_LIMITS = {
    'max_plots': 50,
    'max_clients': 25,
    'max_marketers': 10,
    'max_api_calls_daily': 1000,
}

# Subscription settings
SUBSCRIPTION_GRACE_PERIOD_DAYS = 7
SUBSCRIPTION_TRIAL_DAYS = 14
SUBSCRIPTION_ENFORCEMENT_ENABLED = True

# Logging for security audit
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'tenant_isolation.log'),
        },
    },
    'loggers': {
        'estateApp.middleware': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Phase 2: Update Models

**File**: `estateApp/models.py`

Update Company model with subscription fields (already done - verify):

```python
class Company(models.Model):
    # ... existing fields ...
    
    # Subscription fields (VERIFY THESE EXIST)
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'Trial - 14 Days'),
            ('active', 'Active'),
            ('grace_period', 'Grace Period - 7 Days'),
            ('expired', 'Expired'),
            ('suspended', 'Suspended'),
            ('cancelled', 'Cancelled'),
        ],
        default='trial',
        verbose_name="Subscription Status"
    )
    
    is_read_only_mode = models.BooleanField(
        default=False,
        verbose_name="Read-Only Mode (Grace Period)"
    )
    
    grace_period_ends_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Grace Period Ends At"
    )
    
    subscription_ends_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Subscription Ends At"
    )
    
    trial_ends_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Trial Ends At"
    )
    
    max_plots = models.PositiveIntegerField(
        default=50,
        verbose_name="Max Plots Allowed"
    )
    
    max_api_calls_daily = models.PositiveIntegerField(
        default=1000,
        verbose_name="Max API Calls Per Day"
    )
    
    api_calls_today = models.PositiveIntegerField(
        default=0,
        verbose_name="API Calls Today"
    )
    
    api_calls_reset_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="API Calls Reset At"
    )
    
    data_deletion_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Data Deletion Date (30 days after grace period)"
    )
```

Add company FK to ALL data models:

```python
# ✅ MUST add this to ALL models that store company-specific data

class Plot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    # ... other fields ...

class Client(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    # ... other fields ...

class Marketer(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    # ... other fields ...

class Transaction(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # ... other fields ...

class Allocation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE)
    # ... other fields ...
```

Create CompanyProfile model:

```python
# estateApp/models.py

class CompanyProfile(models.Model):
    """
    Profile for company admin users.
    Links admin user to company with permissions.
    """
    
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='admin_profile'
    )
    
    # Admin details
    admin_name = models.CharField(max_length=255)
    admin_title = models.CharField(max_length=100, blank=True)
    admin_email = models.EmailField()
    admin_phone = models.CharField(max_length=15)
    
    # Permissions (as JSON list)
    permissions = models.JSONField(
        default=list,
        help_text="List of permissions for this admin"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profiles"
    
    def __str__(self):
        return f"{self.company.company_name} Admin: {self.admin_name}"
    
    def has_permission(self, permission):
        """Check if admin has specific permission"""
        return permission in self.permissions
    
    def grant_permission(self, permission):
        """Grant permission to admin"""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.save()
    
    def revoke_permission(self, permission):
        """Revoke permission from admin"""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.save()
```

Create AuditLog model:

```python
class AuditLog(models.Model):
    """Complete audit trail for compliance"""
    
    ACTION_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    path = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    status_code = models.IntegerField()
    request_data = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['company', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action_type} {self.path} ({self.timestamp})"
```

### Phase 3: Create Managers for Query Isolation

**File**: `estateApp/managers.py` (create new file)

```python
from django.db import models
from .middleware import get_current_company


class CompanyAwareManager(models.Manager):
    """
    Custom manager that automatically filters querysets by current company.
    
    CRITICAL: Prevents accidental data leaks from cross-company queries.
    """
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Get current company from thread-local storage
        company = get_current_company()
        
        # If company is set (and not super admin), filter by company
        if company:
            return qs.filter(company=company)
        
        return qs


# Update all models to use this manager:
# In estateApp/models.py

class Plot(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # ✅ ADD THIS:
    objects = CompanyAwareManager()
    all_objects = models.Manager()  # For super admin queries
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'name']),
            models.Index(fields=['company', 'created_at']),
        ]


class Client(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # ✅ ADD THIS:
    objects = CompanyAwareManager()
    all_objects = models.Manager()
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'full_name']),
        ]
```

### Phase 4: Update Views with Decorators

**File**: `estateApp/views.py`

Example view implementations:

```python
from django.shortcuts import render, redirect
from django.contrib import messages
from .decorators import company_required, subscription_required, read_only_safe
from .middleware import get_current_company
from .models import Plot, Client, Marketer, Transaction

@company_required
def company_dashboard(request):
    """
    Company admin dashboard - complete data isolation.
    All data automatically filtered to current company.
    """
    company = request.company
    
    # These queries automatically filter by company via CompanyAwareManager
    plots = Plot.objects.filter(company=company)
    clients = Client.objects.filter(company=company)
    marketers = Marketer.objects.filter(company=company)
    
    context = {
        'company': company,
        'plots_count': plots.count(),
        'clients_count': clients.count(),
        'marketers_count': marketers.count(),
    }
    
    return render(request, 'admin_side/company_dashboard.html', context)


@company_required
@subscription_required
def manage_clients(request):
    """
    Manage clients - requires active subscription.
    Complete isolation: Only shows current company's clients.
    """
    company = request.company
    
    # Check subscription limit
    clients_limit = company.subscription_details.plan.max_clients if company.subscription_details else 10
    current_clients = Client.objects.filter(company=company).count()
    
    if request.method == 'POST':
        # Check limit
        if current_clients >= clients_limit:
            messages.error(request, f'Client limit ({clients_limit}) reached.')
            return redirect('manage_clients')
        
        # Create client (ALWAYS for current company)
        client = Client.objects.create(
            company=company,  # ✅ Enforce company
            full_name=request.POST['full_name'],
            # ... other fields ...
        )
        
        messages.success(request, 'Client added successfully.')
        return redirect('manage_clients')
    
    clients = Client.objects.filter(company=company)
    
    context = {
        'company': company,
        'clients': clients,
        'clients_limit': clients_limit,
    }
    
    return render(request, 'admin_side/manage_clients.html', context)


@company_required
@read_only_safe
def edit_plot(request, plot_id):
    """
    Edit plot - blocks writes during grace period.
    """
    company = request.company
    
    # ✅ CRITICAL: Verify plot belongs to current company
    try:
        plot = Plot.objects.get(id=plot_id, company=company)
    except Plot.DoesNotExist:
        messages.error(request, 'Plot not found or access denied.')
        return redirect('manage_plots')
    
    if request.method == 'POST':
        plot.name = request.POST['name']
        # ... update other fields ...
        plot.save()
        
        messages.success(request, 'Plot updated successfully.')
        return redirect('manage_plots')
    
    context = {'plot': plot}
    return render(request, 'admin_side/edit_plot.html', context)


@company_required
def manage_subscription(request):
    """
    Manage subscription - company-specific billing.
    """
    company = request.company
    
    context = {
        'company': company,
        'subscription': company.subscription_details,
        'plans': SubscriptionPlan.objects.all(),
    }
    
    return render(request, 'admin_side/manage_subscription.html', context)
```

### Phase 5: Update API Endpoints

**File**: `estateApp/api_views.py`

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .decorators import api_company_required, api_subscription_required, api_read_only_check
from .models import Plot, Client
from .serializers import PlotSerializer, ClientSerializer
from .middleware import get_current_company


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@api_company_required
def api_get_company_plots(request):
    """
    API endpoint to get plots for current company.
    Complete isolation: Only returns current company's plots.
    """
    company = request.company
    
    # Get only current company's plots
    plots = Plot.objects.filter(company=company)
    serializer = PlotSerializer(plots, many=True)
    
    return Response({
        'company': company.company_name,
        'plots_count': plots.count(),
        'plots': serializer.data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@api_company_required
@api_read_only_check
def api_create_plot(request):
    """
    API endpoint to create plot for current company.
    Complete isolation: Always creates for current company ONLY.
    Respects subscription limits.
    """
    company = request.company
    
    # Check plot limit
    current_plots = Plot.objects.filter(company=company).count()
    if current_plots >= company.max_plots:
        return Response(
            {'error': f'Plot limit ({company.max_plots}) reached for your subscription'},
            status=status.HTTP_402_PAYMENT_REQUIRED
        )
    
    # Create plot for current company ONLY (not from request data)
    serializer = PlotSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(company=company)  # ✅ Enforce company
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

---

## 🗂️ Files to Update/Create

| File | Action | Purpose |
|------|--------|---------|
| `estateProject/settings.py` | UPDATE | Add 5 middleware classes |
| `estateApp/middleware.py` | UPDATE | Enhanced middleware implementation |
| `estateApp/decorators.py` | REPLACE | New decorators for data isolation |
| `estateApp/managers.py` | CREATE | CompanyAwareManager for query filtering |
| `estateApp/models.py` | UPDATE | Add company FK, subscription fields, CompanyProfile |
| `estateApp/views.py` | UPDATE | Add @company_required, @subscription_required decorators |
| `estateApp/api_views.py` | UPDATE | Use @api_company_required on endpoints |
| `estateApp/admin.py` | UPDATE | Register new models in Django admin |

---

## 🗄️ Database Migrations

```bash
# Step 1: Create migrations for new models
python manage.py makemigrations estateApp

# Step 2: Review migrations (optional)
python manage.py showmigrations estateApp

# Step 3: Apply migrations
python manage.py migrate estateApp

# Step 4: Verify migration applied
python manage.py showmigrations estateApp
```

---

## ✅ Verification Checklist

### Before Deployment

- [ ] All middleware added to settings.py in correct order
- [ ] TenantIsolationMiddleware is AFTER AuthenticationMiddleware
- [ ] All models have `company` foreign key
- [ ] CompanyAwareManager added to all data models
- [ ] CompanyProfile model created
- [ ] AuditLog model created
- [ ] All views decorated with @company_required
- [ ] All API endpoints decorated with @api_company_required
- [ ] Database migrations created and tested locally
- [ ] Logging configuration added to settings.py

### Post-Deployment Testing

- [ ] Login as Company A admin, verify can only see Company A data
- [ ] Login as Company B admin, verify can only see Company B data
- [ ] Try accessing Company B data as Company A (should be denied)
- [ ] Test creating client for Company A (should create for A only)
- [ ] Test subscription enforcement (trial, active, grace, expired)
- [ ] Test read-only mode during grace period
- [ ] Test super admin access to all companies
- [ ] Check audit logs for all user actions
- [ ] Verify API isolation (query with API key from A, returns A data only)
- [ ] Test query-level isolation (try to fetch Company B data directly)

---

## 🚨 Critical Security Points

### DO's:
✅ Always use `request.company` from middleware  
✅ Always verify company ownership before operations  
✅ Always use CompanyAwareManager for queries  
✅ Always enforce subscription status in middleware  
✅ Always log access attempts for audit trail  

### DON'Ts:
❌ Never trust user input for company_id  
❌ Never bypass @company_required decorator  
❌ Never use `all_objects` instead of `objects` in views  
❌ Never skip subscription enforcement checks  
❌ Never allow super admin and company admin to mix roles  

---

## 📊 Sample Test Script

```bash
# Test data isolation

# 1. Create two companies
python manage.py shell

from estateApp.models import Company, User, CompanyProfile

# Create Company A
company_a = Company.objects.create(
    company_name="Company A",
    slug="company-a",
    registration_number="CA001",
    ceo_name="CEO A",
    email="admin@companya.ng"
)

# Create Company B
company_b = Company.objects.create(
    company_name="Company B",
    slug="company-b",
    registration_number="CB001",
    ceo_name="CEO B",
    email="admin@companyb.ng"
)

# Create admin users
admin_a = User.objects.create_user(
    email="admin_a@companya.ng",
    password="password123",
    username="admin_a"
)

admin_b = User.objects.create_user(
    email="admin_b@companyb.ng",
    password="password123",
    username="admin_b"
)

# Link to companies
CompanyProfile.objects.create(
    company=company_a,
    admin_name="Admin A",
    admin_email=admin_a.email,
    admin_phone="1111111111"
)

# ... create admin_b profile ...

# 2. Test in browser:
# - Login as admin_a, view plots (should see only Company A plots)
# - Login as admin_b, view plots (should see only Company B plots)
# - Try to access admin_b session as admin_a (should fail)
```

---

## 🎯 Success Criteria

✅ Company A admin cannot access ANY Company B data  
✅ Company B admin cannot access ANY Company A data  
✅ Subscription status controls feature access  
✅ Grace period activates automatically after expiration  
✅ Read-only mode blocks writes during grace period  
✅ Super admin can access all companies for platform management  
✅ All actions logged in audit trail  
✅ API endpoints return proper 403/402 errors for access denial  

---

## 📞 Troubleshooting

**Issue**: "Company context not found" error

**Solution**: Verify TenantIsolationMiddleware is active and after AuthenticationMiddleware

```python
# Check in shell:
python manage.py shell
from estateApp.middleware import get_current_company
print(get_current_company())  # Should return company or None
```

**Issue**: Cross-company data appearing

**Solution**: Verify all models have CompanyAwareManager

```python
# Check in shell:
from estateApp.models import Plot
from estateApp.middleware import set_current_company, get_current_company
company_a = Company.objects.first()
set_current_company(company_a)
plots = Plot.objects.all()  # Should only return company_a plots
```

**Issue**: Views not enforcing company_required

**Solution**: Check that all views have @company_required decorator

```bash
grep -r "@company_required" estateApp/views.py
```

---

**Version**: 1.0  
**Date**: November 22, 2025  
**Status**: Ready for Implementation
