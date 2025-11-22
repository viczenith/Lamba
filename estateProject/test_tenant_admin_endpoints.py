"""
Tenant Admin Endpoint Test Script
Run this to verify all endpoints are properly wired
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.urls import reverse, resolve
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory

print("=" * 80)
print("TENANT ADMIN ENDPOINT VERIFICATION")
print("=" * 80)

# Test URL Resolution
print("\n✅ URL RESOLUTION TEST:")
print("-" * 80)

try:
    dashboard_url = reverse('tenant_admin:dashboard')
    print(f"✅ Dashboard URL: {dashboard_url}")
except Exception as e:
    print(f"❌ Dashboard URL Error: {e}")

try:
    login_url = reverse('tenant_admin:login')
    print(f"✅ Login URL: {login_url}")
except Exception as e:
    print(f"❌ Login URL Error: {e}")

try:
    logout_url = reverse('tenant_admin:logout')
    print(f"✅ Logout URL: {logout_url}")
except Exception as e:
    print(f"❌ Logout URL Error: {e}")

try:
    access_denied_url = reverse('tenant_admin:access-denied')
    print(f"✅ Access Denied URL: {access_denied_url}")
except Exception as e:
    print(f"❌ Access Denied URL Error: {e}")

# Test API URL Resolution
print("\n✅ API URL RESOLUTION TEST:")
print("-" * 80)

api_endpoints = [
    '/api/tenant-admin/dashboard-stats/',
    '/api/tenant-admin/recent-activity/',
    '/api/tenant-admin/system-health/',
    '/api/tenant-admin/auth/login/',
    '/api/tenant-admin/auth/logout/',
]

for endpoint in api_endpoints:
    try:
        resolved = resolve(endpoint)
        print(f"✅ {endpoint:50} -> {resolved.func.__name__}")
    except Exception as e:
        print(f"❌ {endpoint:50} -> ERROR: {e}")

# Test View Imports
print("\n✅ VIEW IMPORTS TEST:")
print("-" * 80)

try:
    from tenantAdmin.views import (
        TenantAdminLoginView,
        TenantAdminLogoutView,
        TenantAdminDashboardView,
        AccessDeniedView
    )
    print("✅ All views imported successfully")
    print(f"   - TenantAdminLoginView: {TenantAdminLoginView}")
    print(f"   - TenantAdminLogoutView: {TenantAdminLogoutView}")
    print(f"   - TenantAdminDashboardView: {TenantAdminDashboardView}")
    print(f"   - AccessDeniedView: {AccessDeniedView}")
except Exception as e:
    print(f"❌ View import error: {e}")

# Test API View Imports
print("\n✅ API VIEW IMPORTS TEST:")
print("-" * 80)

try:
    from tenantAdmin.api.views import (
        dashboard_stats,
        recent_activity,
        system_health
    )
    print("✅ API views imported successfully")
    print(f"   - dashboard_stats: {dashboard_stats}")
    print(f"   - recent_activity: {recent_activity}")
    print(f"   - system_health: {system_health}")
except Exception as e:
    print(f"❌ API view import error: {e}")

try:
    from tenantAdmin.api.auth_views import TenantAdminAuthViewSet
    print("✅ Auth ViewSet imported successfully")
    print(f"   - TenantAdminAuthViewSet: {TenantAdminAuthViewSet}")
except Exception as e:
    print(f"❌ Auth ViewSet import error: {e}")

# Test Permission Imports
print("\n✅ PERMISSION IMPORTS TEST:")
print("-" * 80)

try:
    from tenantAdmin.permissions import (
        IsSystemAdmin,
        IsSystemAdminOrReadOnly,
        IsSuperAdminOnly
    )
    print("✅ All permissions imported successfully")
    print(f"   - IsSystemAdmin: {IsSystemAdmin}")
    print(f"   - IsSystemAdminOrReadOnly: {IsSystemAdminOrReadOnly}")
    print(f"   - IsSuperAdminOnly: {IsSuperAdminOnly}")
except Exception as e:
    print(f"❌ Permission import error: {e}")

# Test Decorator Imports
print("\n✅ DECORATOR IMPORTS TEST:")
print("-" * 80)

try:
    from tenantAdmin.decorators import (
        require_system_admin,
        require_superuser,
        audit_action
    )
    print("✅ All decorators imported successfully")
    print(f"   - require_system_admin: {require_system_admin}")
    print(f"   - require_superuser: {require_superuser}")
    print(f"   - audit_action: {audit_action}")
except Exception as e:
    print(f"❌ Decorator import error: {e}")

# Test Model Imports
print("\n✅ MODEL IMPORTS TEST:")
print("-" * 80)

try:
    from tenantAdmin.models import (
        AuditLog,
        SystemConfiguration,
        SystemAlert,
        SystemMetric
    )
    print("✅ All models imported successfully")
    print(f"   - AuditLog: {AuditLog._meta.db_table}")
    print(f"   - SystemConfiguration: {SystemConfiguration._meta.db_table}")
    print(f"   - SystemAlert: {SystemAlert._meta.db_table}")
    print(f"   - SystemMetric: {SystemMetric._meta.db_table}")
except Exception as e:
    print(f"❌ Model import error: {e}")

# Test Template Files
print("\n✅ TEMPLATE FILES TEST:")
print("-" * 80)

import os
from django.conf import settings

template_dir = os.path.join(settings.BASE_DIR, 'tenantAdmin', 'templates', 'tenantAdmin')
required_templates = ['dashboard.html', 'login.html', 'access_denied.html']

for template in required_templates:
    template_path = os.path.join(template_dir, template)
    if os.path.exists(template_path):
        size = os.path.getsize(template_path)
        print(f"✅ {template:30} exists ({size:,} bytes)")
    else:
        print(f"❌ {template:30} NOT FOUND")

# Test Static Files
print("\n✅ STATIC FILES TEST:")
print("-" * 80)

static_dir = os.path.join(settings.BASE_DIR, 'tenantAdmin', 'static', 'tenantAdmin')
required_static = [
    ('css/styles.css', os.path.join(static_dir, 'css', 'styles.css')),
    ('js/auth.js', os.path.join(static_dir, 'js', 'auth.js')),
]

for name, path in required_static:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"✅ {name:30} exists ({size:,} bytes)")
    else:
        print(f"❌ {name:30} NOT FOUND")

# Final Summary
print("\n" + "=" * 80)
print("✅ ENDPOINT VERIFICATION COMPLETE")
print("=" * 80)
print("\n📍 AVAILABLE URLS:")
print("-" * 80)
print("Dashboard:      http://127.0.0.1:8000/tenant-admin/")
print("Login:          http://127.0.0.1:8000/tenant-admin/login/")
print("API Stats:      http://127.0.0.1:8000/api/tenant-admin/dashboard-stats/")
print("API Activity:   http://127.0.0.1:8000/api/tenant-admin/recent-activity/")
print("API Health:     http://127.0.0.1:8000/api/tenant-admin/system-health/")
print("API Auth:       http://127.0.0.1:8000/api/tenant-admin/auth/login/")
print("-" * 80)
