# FACEBOOK-STYLE DYNAMIC TENANT URL CONFIGURATION
# File: estateApp/tenant_urls.py

"""
IMPLEMENTATION: Add these URL patterns to estateApp/urls.py

This creates Facebook-like URLs with company slugs.

EXAMPLES:
========

OLD ROUTES (Insecure):
  /admin_dashboard/          (any admin sees all data)
  /management-dashboard/     (no company context)
  
NEW ROUTES (Secure & User-Friendly):
  /lamba-real-homes/dashboard/      (Admin sees "Lamba Real Homes" in URL)
  /lamba-real-homes/management/     (User knows exactly which company)
  /lamba-real-homes/users/          (Clear tenant context)
  /property-plus/dashboard/         (Different company)
  /enterprise-corp/users/           (Another company)

BENEFITS:
=========
✅ Clear tenant identification (like Facebook)
✅ User-friendly and readable URLs
✅ Security: Cannot access other company's data
✅ SEO friendly with slug
✅ Prevents URL hacking (company verified at view level)
✅ Automatic redirect from old routes
"""

from django.urls import path
from .tenant_views import (
    tenant_admin_dashboard,
    tenant_management_dashboard,
    tenant_user_management,
    tenant_company_settings,
    redirect_admin_dashboard_to_tenant,
    redirect_management_to_tenant,
)

# Dynamic tenant-aware URL patterns (add to estateApp/urls.py)
tenant_patterns = [
    # ========================================================================
    # PRIMARY ROUTES (Facebook-style with company slug)
    # Pattern: /<company-slug>/<page>/
    # ========================================================================
    
    path(
        '<slug:company_slug>/dashboard/',
        tenant_admin_dashboard,
        name='tenant-dashboard'
        # Example: /lamba-real-homes/dashboard/
    ),
    
    path(
        '<slug:company_slug>/management/',
        tenant_management_dashboard,
        name='tenant-management'
        # Example: /lamba-real-homes/management/
    ),
    
    path(
        '<slug:company_slug>/users/',
        tenant_user_management,
        name='tenant-users'
        # Example: /lamba-real-homes/users/
    ),
    
    path(
        '<slug:company_slug>/settings/',
        tenant_company_settings,
        name='tenant-settings'
        # Example: /lamba-real-homes/settings/
    ),
    
    # ========================================================================
    # BACKWARD COMPATIBILITY REDIRECTS
    # (Redirect old routes to new tenant-aware routes)
    # ========================================================================
    
    path(
        'admin_dashboard/',
        redirect_admin_dashboard_to_tenant,
        name='admin-dashboard-redirect'
        # Old: /admin_dashboard/ → /lamba-real-homes/dashboard/
    ),
    
    path(
        'management-dashboard/',
        redirect_management_to_tenant,
        name='management-dashboard-redirect'
        # Old: /management-dashboard/ → /lamba-real-homes/management/
    ),
]

# ============================================================================
# IMPLEMENTATION INSTRUCTIONS
# ============================================================================

"""
STEP 1: Add tenant_views.py to your estateApp
   ✅ Already created as estateApp/tenant_views.py

STEP 2: Update estateApp/urls.py
   Add at the END of urlpatterns in estateApp/urls.py:
   
   from .tenant_urls import tenant_patterns
   
   # Add tenant-aware routes (must be last to avoid conflicts)
   urlpatterns += tenant_patterns

STEP 3: Update templates to use new routes
   
   OLD:
     <a href="{% url 'admin-dashboard' %}">Dashboard</a>
   
   NEW:
     <a href="{% url 'tenant-dashboard' company_slug=request.company.slug %}">
       Dashboard
     </a>

STEP 4: Test the routes
   
   1. Login to /lamba-real-homes/login/
   2. Navigate to /lamba-real-homes/dashboard/
   3. URL shows your company name
   4. Try accessing /other-company/dashboard/ → DENIED ✅

SECURITY FEATURES:
   ✅ Company slug verified in URL
   ✅ User authorization checked per company
   ✅ Access denied to other companies
   ✅ Company context auto-injected
   ✅ Backward compatibility maintained
"""

# ============================================================================
# ROUTE MAPPING REFERENCE
# ============================================================================

ROUTE_MAPPINGS = """
ADMIN DASHBOARD:
  Old: /admin_dashboard/
  New: /<company-slug>/dashboard/
  Redirect: Automatic ✅
  Example: /lamba-real-homes/dashboard/

MANAGEMENT DASHBOARD:
  Old: /management-dashboard/
  New: /<company-slug>/management/
  Redirect: Automatic ✅
  Example: /lamba-real-homes/management/

USER MANAGEMENT:
  Old: None (new feature)
  New: /<company-slug>/users/
  Example: /lamba-real-homes/users/

COMPANY SETTINGS:
  Old: None (new feature)
  New: /<company-slug>/settings/
  Example: /lamba-real-homes/settings/
"""

# ============================================================================
# SECURITY FEATURES
# ============================================================================

SECURITY_FEATURES = """
1. COMPANY SLUG VALIDATION
   - Verifies slug exists in database
   - Returns 404 if invalid
   - Prevents arbitrary slug access

2. USER AUTHORIZATION CHECK
   - Verifies user belongs to company
   - Returns 403 Forbidden if unauthorized
   - Super admins can access any company

3. CONTEXT INJECTION
   - request.company auto-populated
   - Views always know which company is active
   - No way to bypass company context

4. URL PROTECTION AGAINST HACKING
   - Slugs are database-verified
   - No wildcard patterns
   - No SQL injection via slug
   - No path traversal possible

5. BACKWARD COMPATIBILITY
   - Old routes still work
   - Automatic redirect to new routes
   - No broken links

ATTACK PREVENTION:
   ✅ /random-slug/dashboard/        → 404 Not Found
   ✅ /other-company/dashboard/      → 403 Forbidden (wrong company)
   ✅ /lamba-real-homes/../admin/    → 404 (path traversal blocked)
   ✅ /lamba-real-homes/dashboard/../login/ → 404 (normalized)
"""

# ============================================================================
# USAGE IN TEMPLATES
# ============================================================================

TEMPLATE_USAGE = """
NAVIGATION LINK:
   <a href="{% url 'tenant-dashboard' company_slug=request.user.company_profile.slug %}">
     Dashboard
   </a>

BREADCRUMB:
   <ol class="breadcrumb">
     <li>{{ request.user.company_profile.company_name }}</li>
     <li>Dashboard</li>
   </ol>

CONTEXT DISPLAY:
   <h1>{{ request.company.company_name }} Dashboard</h1>
   <!-- Available because @tenant_context_required injects request.company -->

DYNAMIC URL IN HEADER:
   Current: /lamba-real-homes/dashboard/
   Shows user they're in: Lamba Real Homes
"""

# ============================================================================
# INTEGRATION CHECKLIST
# ============================================================================

INTEGRATION_CHECKLIST = """
□ Copy tenant_views.py to estateApp/
□ Copy tenant_urls.py (or add patterns to estateApp/urls.py)
□ Add import in estateApp/urls.py:
    from .tenant_urls import tenant_patterns
□ Add to urlpatterns at END of estateApp/urls.py:
    urlpatterns += tenant_patterns
□ Update templates to use {% url 'tenant-dashboard' ... %}
□ Test login flow
□ Test dashboard access
□ Test access denial for other companies
□ Test backward compatibility redirects
□ Test URL validation and 404s
□ Deploy to production
"""
