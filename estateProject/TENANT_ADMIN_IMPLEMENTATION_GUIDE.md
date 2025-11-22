# 🚀 TENANT ADMIN AUTHENTICATION - IMPLEMENTATION GUIDE

## Phase 1: Database Migration

### Step 1.1: Add New Fields to CustomUser Model

**File: `estateApp/models.py`** (Add to CustomUser class)

```python
class CustomUser(AbstractUser):
    # ... existing fields ...
    
    # NEW FIELDS FOR SYSTEM ADMIN IDENTIFICATION
    is_system_admin = models.BooleanField(
        default=False,
        verbose_name="Is System Administrator",
        help_text="Has access to Tenant Admin dashboard (system-wide controls only)"
    )
    
    admin_level = models.CharField(
        max_length=20,
        choices=[
            ('system', 'System Admin - Full access to Tenant Admin'),
            ('company', 'Company Admin - Company-only access'),
            ('none', 'Not an admin'),
        ],
        default='none',
        verbose_name="Admin Level"
    )
```

### Step 1.2: Create Migration

```bash
cd "C:\Users\HP\Documents\VictorGodwin\RE\Multi-Tenant Architecture\RealEstateMSApp\estateProject"
python manage.py makemigrations estateApp --name add_system_admin_fields
```

### Step 1.3: Apply Migration

```bash
python manage.py migrate estateApp
```

### Step 1.4: Create System Admin User

**Option A: Django Management Command**

Create `estateApp/management/commands/create_system_admin.py`:

```python
from django.core.management.base import BaseCommand
from estateApp.models import CustomUser

class Command(BaseCommand):
    help = 'Create a system administrator account'

    def handle(self, *args, **options):
        email = input('Enter admin email: ')
        full_name = input('Enter full name: ')
        phone = input('Enter phone number: ')
        password = input('Enter password: ')

        user = CustomUser.objects.create_superuser(
            email=email,
            full_name=full_name,
            phone=phone,
            password=password
        )
        
        user.is_system_admin = True
        user.admin_level = 'system'
        user.company_profile = None
        user.save()

        self.stdout.write(
            self.style.SUCCESS(f'✅ System admin created: {email}')
        )
```

Run:
```bash
python manage.py create_system_admin
```

**Option B: Django Shell**

```bash
python manage.py shell
```

Then in Python shell:
```python
from estateApp.models import CustomUser

user = CustomUser.objects.create_superuser(
    email='admin@system.com',
    full_name='System Administrator',
    phone='1234567890',
    password='SecurePassword@123'
)

user.is_system_admin = True
user.admin_level = 'system'
user.company_profile = None
user.save()

print(f"System admin created: {user.email}")
```

---

## Phase 2: Backend Authentication Setup

### Step 2.1: Update JWT Token Generation

**File: `DRF/admin/api_views/auth_views.py`** (Modify login action)

```python
@action(detail=False, methods=['post'])
@track_errors(error_type='authentication')
def login(self, request):
    """Login user and return token with JWT claims"""
    
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Find user by email
        user = User.objects.get(email=email)
        
        # Authenticate
        if not user.check_password(password):
            raise ValueError("Invalid credentials")
        
        # Check if company is active (unless system admin)
        if not user.is_system_admin and hasattr(user, 'company_profile'):
            if user.company_profile and not user.company_profile.is_active:
                return Response(
                    {'error': 'Company account is suspended'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Log audit
        from estateApp.audit_logging import AuditLogger
        AuditLogger.log_login(
            user=user,
            company=user.company_profile,
            request=request
        )
        
        # Generate/get token
        from rest_framework.authtoken.models import Token
        token_obj, _ = Token.objects.get_or_create(user=user)
        
        # ENHANCED: Create JWT with admin claims
        import jwt
        from django.conf import settings
        from datetime import datetime, timedelta
        
        jwt_payload = {
            'user_id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'is_system_admin': user.is_system_admin,
            'admin_level': user.admin_level,
            'company_id': user.company_profile.id if user.company_profile else None,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'scope': 'tenant_admin' if user.is_system_admin else 'company_admin'
        }
        
        jwt_token = jwt.encode(
            jwt_payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )
        
        return Response({
            'user': CustomUserSerializer(user).data,
            'token': jwt_token,  # Use JWT instead of token key
            'company': CompanyBasicSerializer(user.company_profile).data if user.company_profile else None,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        return Response(
            {'error': 'Login failed'},
            status=status.HTTP_400_BAD_REQUEST
        )
```

### Step 2.2: Add Permission Classes to `estateApp/permissions.py`

```python
class IsSystemAdmin(BasePermission):
    """
    Allows access only to system administrators.
    Used for Tenant Admin endpoints.
    """
    message = "Access Denied: System admin access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', None)
        
        return is_system_admin and admin_level == 'system'


class IsCompanyAdmin(BasePermission):
    """
    Allows access to company admins (system or company level).
    """
    message = "Access Denied: Admin access required"
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        admin_level = getattr(request.user, 'admin_level', None)
        return admin_level in ['system', 'company']
```

### Step 2.3: Create Tenant Admin API Endpoints

**File: `DRF/admin/api_views/tenant_admin_views.py`** (CREATE NEW FILE)

```python
"""
Tenant Admin API Views - System-wide Management
RESTRICTED: Only system administrators can access
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from estateApp.models import Company, CustomUser
from estateApp.permissions import IsSystemAdmin
from DRF.admin.serializers.company_serializers import CompanyDetailedSerializer
from DRF.admin.serializers.user_serializers import CustomUserSerializer
from estateApp.audit_logging import AuditLogger


class TenantAdminViewSet(viewsets.ViewSet):
    """
    Tenant Admin endpoints - System-wide management
    SECURITY: Requires is_system_admin=True and admin_level='system'
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """System-wide dashboard statistics"""
        AuditLogger.log_admin_access(
            user=request.user,
            action='view_dashboard',
            resource='tenant_admin_dashboard',
            request=request
        )
        
        stats = {
            'total_companies': Company.objects.count(),
            'total_users': CustomUser.objects.count(),
            'active_companies': Company.objects.filter(is_active=True).count(),
            'trial_companies': Company.objects.filter(subscription_status='trial').count(),
            'active_subscriptions': Company.objects.filter(subscription_status='active').count(),
            'system_admin_user': request.user.full_name,
            'access_level': 'system_admin'
        }
        
        return Response(stats, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def companies_list(self, request):
        """List all companies with their details"""
        companies = Company.objects.all().order_by('-created_at')
        serializer = CompanyDetailedSerializer(companies, many=True)
        
        return Response({
            'count': companies.count(),
            'companies': serializer.data
        }, status=status.HTTP_200_OK)
```

### Step 2.4: Update Django URLs

**File: `DRF/urls.py`** (Add to existing router)

```python
from DRF.admin.api_views.tenant_admin_views import TenantAdminViewSet

router.register(r'tenant-admin', TenantAdminViewSet, basename='tenant-admin')
```

---

## Phase 3: Frontend Setup

### Step 3.1: Include Authentication Script

**File: `estateApp/templates/tenant_admin/dashboard.html`** (Add at top)

```html
{% extends 'base.html' %}
{% load static %}

{% block head %}
<meta class="tenant-admin-page" />
<!-- Your existing styles -->
{% endblock %}

{% block content %}
<!-- Add admin user info display -->
<div id="admin-user-info" style="position: fixed; top: 20px; right: 20px; z-index: 1000;"></div>

<!-- Your dashboard content -->
{% endblock %}

{% block scripts %}
<!-- Include authentication script FIRST -->
<script src="{% static 'js/tenant-admin-auth.js' %}"></script>

<!-- Then include other scripts -->
<script src="{% static 'js/api-client.js' %}"></script>
<script src="{% static 'js/components.js' %}"></script>
<script src="{% static 'js/error-handler.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', () => {
    // TenantAdminAuth.init() is called automatically
    // Check authentication result
    if (!TenantAdminAuth.isTenantAdmin()) {
        window.location.href = '/tenant-admin/login/';
        return;
    }

    // Initialize dashboard
    console.log('Tenant Admin Dashboard initialized for:', TenantAdminAuth.currentUser.email);
});
</script>
{% endblock %}
```

### Step 3.2: Create Login Page

**File: `estateApp/templates/tenant_admin/login.html`** (CREATE NEW FILE)

Save the login HTML file provided in the security strategy document to this location.

### Step 3.3: Create Access Denied Page

**File: `estateApp/templates/tenant_admin/access-denied.html`** (CREATE NEW FILE)

```html
{% extends 'base.html' %}

{% block head %}
<style>
  .access-denied-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .access-denied-box {
    background: white;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    padding: 60px 40px;
    text-align: center;
    max-width: 500px;
  }

  .access-denied-icon {
    font-size: 60px;
    color: #eb3349;
    margin-bottom: 20px;
  }

  .access-denied-box h1 {
    font-size: 32px;
    color: #333;
    margin: 0 0 10px;
  }

  .access-denied-box p {
    color: #666;
    font-size: 16px;
    margin: 15px 0;
  }

  .access-denied-reason {
    background: #fee;
    border: 1px solid #fcc;
    border-radius: 8px;
    padding: 15px;
    margin: 20px 0;
    color: #c33;
    font-size: 14px;
  }

  .back-to-login {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 30px;
    border-radius: 8px;
    text-decoration: none;
    margin-top: 20px;
    font-weight: 600;
    transition: all 0.3s ease;
  }

  .back-to-login:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
  }
</style>
{% endblock %}

{% block content %}
<div class="access-denied-container">
  <div class="access-denied-box">
    <div class="access-denied-icon">
      <i class="ri-forbid-2-line"></i>
    </div>
    <h1>Access Denied</h1>
    <p>You do not have permission to access the Tenant Admin Dashboard.</p>
    
    {% if reason %}
    <div class="access-denied-reason">
      <strong>Reason:</strong> {{ reason }}
    </div>
    {% endif %}

    <p>Only system administrators can access this portal.</p>
    <a href="/tenant-admin/login/" class="back-to-login">
      <i class="ri-login-box-line"></i> Back to Login
    </a>
  </div>
</div>
{% endblock %}
```

### Step 3.4: Update Django URLs for Templates

**File: `estateApp/urls.py`** (Add these routes)

```python
from django.views.generic import TemplateView
from estateApp.decorators import require_system_admin
from django.utils.decorators import method_decorator

urlpatterns = [
    # ... existing patterns ...
    
    # Tenant Admin routes
    path('tenant-admin/login/', TemplateView.as_view(template_name='tenant_admin/login.html'), name='tenant-admin-login'),
    path('tenant-admin/access-denied/', TemplateView.as_view(template_name='tenant_admin/access-denied.html'), name='tenant-admin-access-denied'),
]
```

---

## Phase 4: Testing

### Test 1: System Admin Login

```bash
# Login with system admin credentials
Email: admin@system.com
Password: SecurePassword@123

# Expected: Should redirect to /tenant-admin/dashboard/
# Check: Browser console should show "✅ Tenant Admin Authentication Successful"
```

### Test 2: Company Admin Rejection

```bash
# Login with company admin credentials
Email: company-admin@company.com
Password: [company-admin-password]

# Expected: Should show "Access Denied: Not a system administrator"
# Check: Browser console should show "Access Denied: User is not a system administrator"
```

### Test 3: Token Verification

```javascript
// Open browser console
TenantAdminAuth.currentUser
// Should show system admin claims
// is_system_admin: true
// admin_level: "system"
// scope: "tenant_admin"
```

### Test 4: JWT Expiration

```javascript
// Check token expiration
TenantAdminAuth.getSessionTimeRemaining()
// Should show remaining time

// Manually expire token and refresh
TenantAdminAuth.refreshToken()
// Should attempt to get new token
```

---

## Phase 5: Production Checklist

- [ ] Database migration applied to production
- [ ] System admin user created
- [ ] JWT token generation updated
- [ ] API permissions configured
- [ ] Frontend authentication files deployed
- [ ] Django URL routes configured
- [ ] Session security settings enabled (HTTPS, HTTPOnly cookies)
- [ ] Rate limiting configured
- [ ] Audit logging enabled
- [ ] CORS properly configured
- [ ] Tested with system admin account
- [ ] Tested rejection of company admins
- [ ] Monitored audit logs for access patterns

---

## Troubleshooting

### Issue: "Access Denied: Not a system administrator"

**Solution:**
```python
# Check user fields
user = CustomUser.objects.get(email='admin@system.com')
print(f"is_system_admin: {user.is_system_admin}")
print(f"admin_level: {user.admin_level}")
print(f"is_superuser: {user.is_superuser}")

# Update if needed
user.is_system_admin = True
user.admin_level = 'system'
user.save()
```

### Issue: "Invalid JWT format"

**Solution:**
- Check that JWT is being generated correctly in login endpoint
- Verify SECRET_KEY is set in settings.py
- Check JWT library is installed: `pip install PyJWT`

### Issue: Token not being validated

**Solution:**
- Open browser console
- Run: `TenantAdminAuth.decodeJWT(localStorage.getItem('auth_token'))`
- Check decoded claims
- Verify claims match expected values

---

## Summary

You now have:

✅ **Database-level distinction** between system and company admins
✅ **JWT tokens** with admin scope verification
✅ **Frontend authentication** with automatic validation
✅ **Backend API protection** with permission classes
✅ **Audit logging** for all sensitive access
✅ **Session management** with token refresh
✅ **Access denied page** for unauthorized users

**Security Level**: Enterprise-Grade 🔐

