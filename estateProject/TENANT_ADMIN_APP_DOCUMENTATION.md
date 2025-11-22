# Tenant Admin App - Complete Documentation

## Overview
The **tenantAdmin** Django app provides a dedicated, organized management interface for system administrators to oversee the entire multi-tenant real estate management platform.

## Features
✅ **System-wide Dashboard**: Comprehensive overview of all companies, users, properties, and financial metrics
✅ **Audit Logging**: Complete audit trail for compliance and security
✅ **System Configuration**: Key-value configuration management
✅ **Alert System**: Proactive monitoring and notification system
✅ **Performance Metrics**: Time-series performance data tracking
✅ **Secure Access**: Permission-based access control (IsSystemAdmin)

## Directory Structure
```
tenantAdmin/
├── templates/tenantAdmin/          # Django templates
│   ├── dashboard.html              # Main dashboard (1,645 lines)
│   ├── login.html                  # System admin login
│   └── access_denied.html          # Access denied page
├── static/tenantAdmin/
│   ├── css/
│   │   └── styles.css              # Custom styles
│   └── js/
│       └── auth.js                 # Authentication & API client
├── api/
│   ├── __init__.py
│   ├── urls.py                     # API routing
│   └── views.py                    # API endpoints (3 endpoints)
├── migrations/
│   └── 0001_initial.py             # Database migrations
├── models.py                       # 4 models (AuditLog, SystemConfiguration, SystemAlert, SystemMetric)
├── views.py                        # Dashboard views
├── urls.py                         # URL routing
├── permissions.py                  # 3 permission classes
├── decorators.py                   # 3 decorators
├── admin.py                        # Django admin registration
└── apps.py                         # App configuration
```

## Models

### 1. AuditLog
**Purpose**: System-wide audit trail for compliance and security

**Fields**:
- `user` (ForeignKey): User who performed the action
- `action_type` (CharField): Type of action (create, read, update, delete, login, logout, etc.)
- `resource` (CharField): What was accessed/modified
- `resource_id` (CharField): ID of the resource
- `company` (ForeignKey): Company context (if applicable)
- `ip_address` (GenericIPAddressField): User's IP address
- `user_agent` (TextField): Browser/client information
- `request_method` (CharField): HTTP method (GET, POST, etc.)
- `request_path` (CharField): URL path
- `description` (TextField): Human-readable description
- `metadata` (JSONField): Additional context data
- `timestamp` (DateTimeField): When the action occurred

**Indexes**: 3 composite indexes for performance

**Usage**:
```python
from tenantAdmin.decorators import audit_action

@audit_action(action_type='create', resource='company')
def create_company_view(request):
    # Automatically logged to AuditLog
    pass
```

### 2. SystemConfiguration
**Purpose**: Key-value configuration store for system-wide settings

**Fields**:
- `key` (CharField, unique): Configuration key
- `value` (TextField): Configuration value
- `value_type` (CharField): Type of value (string, integer, float, boolean, json)
- `description` (TextField): What this config does
- `is_sensitive` (BooleanField): Is this sensitive data?
- `updated_by` (ForeignKey): Who last updated it

**Methods**:
- `get_value()`: Returns typed value (int, float, bool, json, or string)

**Usage**:
```python
config = SystemConfiguration.objects.get(key='max_companies')
max_value = config.get_value()  # Returns integer
```

### 3. SystemAlert
**Purpose**: System-wide alerts and notifications for admins

**Fields**:
- `title` (CharField): Alert title
- `message` (TextField): Alert message
- `severity` (CharField): info, warning, error, critical
- `alert_type` (CharField): performance, security, billing, etc.
- `is_active` (BooleanField): Is alert currently active?
- `is_resolved` (BooleanField): Has it been resolved?
- `resolved_by` (ForeignKey): Who resolved it

**Methods**:
- `resolve(user)`: Mark alert as resolved

**Usage**:
```python
alert = SystemAlert.objects.create(
    title='High Database Usage',
    message='Database size exceeds 80% capacity',
    severity='warning',
    alert_type='performance'
)

# Later...
alert.resolve(request.user)
```

### 4. SystemMetric
**Purpose**: Time-series performance data for monitoring

**Fields**:
- `metric_name` (CharField): Name of metric (api_response_time, db_size, etc.)
- `metric_value` (FloatField): Numeric value
- `metric_unit` (CharField): Unit (ms, MB, %, etc.)
- `tags` (JSONField): Flexible metadata
- `timestamp` (DateTimeField): When metric was recorded

**Usage**:
```python
SystemMetric.objects.create(
    metric_name='api_response_time',
    metric_value=124.5,
    metric_unit='ms',
    tags={'endpoint': '/api/companies/', 'method': 'GET'}
)
```

## Permissions

### IsSystemAdmin
**Purpose**: Restrict access to system administrators only

**Checks**:
- `user.is_system_admin == True`
- `user.admin_level == 'system'`

**Usage**:
```python
from tenantAdmin.permissions import IsSystemAdmin

@permission_classes([IsAuthenticated, IsSystemAdmin])
def protected_view(request):
    pass
```

### IsSystemAdminOrReadOnly
**Purpose**: Read-only access for authenticated users, write access for system admins

### IsSuperAdminOnly
**Purpose**: Restrict to Django superusers only

## Decorators

### @require_system_admin
**Purpose**: Redirect non-system-admins to access denied page

**Usage**:
```python
from tenantAdmin.decorators import require_system_admin

@require_system_admin
def dashboard_view(request):
    return render(request, 'dashboard.html')
```

### @require_superuser
**Purpose**: Require Django superuser status

### @audit_action(action_type, resource)
**Purpose**: Automatically log actions to AuditLog

**Usage**:
```python
@audit_action(action_type='delete', resource='company')
def delete_company_view(request, company_id):
    # Action is automatically logged
    pass
```

## API Endpoints

### 1. Dashboard Statistics
**Endpoint**: `GET /api/tenant-admin/dashboard-stats/`

**Response**:
```json
{
  "total_companies": 2,
  "active_companies": 2,
  "trial_companies": 0,
  "company_growth": "+0.0%",
  "total_users": 8,
  "active_users": 8,
  "total_clients": 2,
  "total_marketers": 6,
  "total_admins": 0,
  "user_growth": "+0.0%",
  "total_estates": 0,
  "total_plots": 0,
  "total_allocations": 0,
  "total_revenue": 0.0,
  "pending_payments": 0.0
}
```

### 2. Recent Activity
**Endpoint**: `GET /api/tenant-admin/recent-activity/`

**Response**:
```json
[
  {
    "icon": "ri-building-line",
    "icon_class": "create",
    "text": "New company \"Lamba Real Homes\" registered",
    "time": "2 days ago"
  }
]
```

### 3. System Health
**Endpoint**: `GET /api/tenant-admin/system-health/`

**Response**:
```json
{
  "uptime": "99.9%",
  "api_response_time": "124ms",
  "database_size": "0.15GB",
  "database_capacity": "34%",
  "active_sessions": 2,
  "status": "operational"
}
```

## Views

### TenantAdminLoginView
**URL**: `/tenant-admin/login/`
**Purpose**: System admin authentication

### TenantAdminLogoutView
**URL**: `/tenant-admin/logout/`
**Purpose**: Logout and clear session

### TenantAdminDashboardView
**URL**: `/tenant-admin/` or `/tenant-admin/dashboard/`
**Purpose**: Main management dashboard
**Security**: @require_system_admin decorator

### AccessDeniedView
**URL**: `/tenant-admin/access-denied/`
**Purpose**: Shown when non-admins try to access admin areas

## Integration

### settings.py
```python
INSTALLED_APPS = [
    # ...
    'tenantAdmin',  # Added
    # ...
]
```

### urls.py
```python
urlpatterns = [
    # ...
    path('tenant-admin/', include('tenantAdmin.urls', namespace='tenant_admin')),
    # ...
]
```

## Database Tables Created
- `tenantAdmin_auditlog`
- `tenantAdmin_systemconfiguration`
- `tenantAdmin_systemalert`
- `tenantAdmin_systemmetric`

## Testing Access

### System Admin User
Must have:
- `is_system_admin = True`
- `admin_level = 'system'`

### Create System Admin:
```python
python manage.py shell

from estateApp.models import CustomUser

admin = CustomUser.objects.get(email='admin@example.com')
admin.is_system_admin = True
admin.admin_level = 'system'
admin.save()
```

### Access Dashboard:
1. Navigate to: `http://127.0.0.1:8000/tenant-admin/login/`
2. Login with system admin credentials
3. Redirects to: `http://127.0.0.1:8000/tenant-admin/dashboard/`

## Security Features
✅ Permission-based access control
✅ JWT authentication for API endpoints
✅ Audit logging for all actions
✅ Related name conflicts resolved (`tenant_admin_audit_logs`)
✅ Session-based authentication for dashboard
✅ CSRF protection on forms

## Files Migrated
- Dashboard template: `estateApp/templates/tenant_admin/` → `tenantAdmin/templates/tenantAdmin/`
- API views: `DRF/admin/api_views/tenant_admin_views.py` → `tenantAdmin/api/views.py`

## Development Status
✅ Django app created and registered
✅ Models defined and migrated (4 models)
✅ Permissions created (3 classes)
✅ Decorators created (3 decorators)
✅ Views created (4 views)
✅ URL routing configured
✅ API endpoints operational (3 endpoints)
✅ Templates created (3 templates)
✅ Static files organized (CSS + JS)
✅ Django admin registered (4 models)
✅ Database migrations applied
✅ Integration complete

## Next Steps (Optional)
1. Add more API endpoints (user management, company management)
2. Implement real-time dashboard updates (WebSockets)
3. Add export functionality (CSV, PDF reports)
4. Implement advanced filtering and search
5. Add data visualization widgets
6. Create mobile-responsive views
7. Add notification system integration
8. Implement scheduled tasks (Celery) for metrics collection

## Support
For issues or questions, check:
- Django logs: Check console output
- Audit logs: `tenantAdmin_auditlog` table
- System alerts: `tenantAdmin_systemalert` table

## Conclusion
The **tenantAdmin** app provides a clean, organized, and secure management interface for system administrators. All files are now properly structured following Django best practices with dedicated templates, static files, API endpoints, and models.
