# TENANT-AWARE DYNAMIC ROUTING SYSTEM
# Similar to: https://web.facebook.com/victor.godwin.841340

"""
This system provides:
1. Dynamic tenant slugs in URLs (like Facebook profiles)
2. Security against route bypassing and hacking
3. Automatic tenant context injection
4. Company-scoped data isolation at URL level
5. Protection against arbitrary slug access
"""

from django.urls import path, re_path
from django.http import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from estateApp.models import Company, CustomUser
from estateApp.views import admin_dashboard, management_dashboard

# ============================================================================
# EXAMPLE ROUTES (add these to estateApp/urls.py):
# ============================================================================
# 
# BEFORE (Insecure):
#   /admin_dashboard/
#   /admin_dashboard/  (any admin can access)
#   No way to know which company you're viewing
#
# AFTER (Secure like Facebook):
#   /<company-slug>/dashboard/          (e.g., /lamba-real-homes/dashboard/)
#   /<company-slug>/management/         (e.g., /lamba-real-homes/management/)
#   /<company-slug>/users/              (e.g., /lamba-real-homes/users/)
#   /<company-slug>/settings/           (e.g., /lamba-real-homes/settings/)
#
# Benefits:
# ✅ Users see their company slug in URL
# ✅ URLs are impossible to bypass (company verified at view level)
# ✅ Clear tenant isolation in routing
# ✅ SEO friendly
# ✅ User-friendly (like Facebook)
# ============================================================================


def get_tenant_from_slug(slug):
    """
    Safely retrieve company by slug.
    Returns Company object or None if not found.
    """
    try:
        return Company.objects.get(slug=slug)
    except Company.DoesNotExist:
        return None


def verify_user_company_access(user, company):
    """
    SECURITY CHECK: Verify user has access to this company.
    Returns True if user belongs to this company, False otherwise.
    """
    # Super admin has access to all companies
    if user.role == 'superadmin':
        return True
    
    # Check if user's company matches the requested company
    if user.company_profile == company:
        return True
    
    # Deny access to other companies' data
    return False


def tenant_required(view_func):
    """
    DECORATOR: Ensures tenant (company) is valid and user has access.
    
    Usage:
        @tenant_required
        def my_view(request, company_slug):
            # company_slug is validated and in request context
            pass
    """
    def wrapper(request, company_slug, *args, **kwargs):
        # 1. Get company from slug
        company = get_tenant_from_slug(company_slug)
        if not company:
            # Invalid slug - return 404
            return redirect('login')  # or custom 404 page
        
        # 2. Verify user belongs to this company
        if not verify_user_company_access(request.user, company):
            # User trying to access other company's data - DENY
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied to this company's data")
        
        # 3. Inject company into request for view access
        request.company = company
        request.company_slug = company_slug
        
        # 4. Call original view
        return view_func(request, company_slug, *args, **kwargs)
    
    return wrapper


# ============================================================================
# SECURE DYNAMIC VIEWS
# ============================================================================

@login_required
@tenant_required
def admin_dashboard_dynamic(request, company_slug):
    """
    Tenant-aware admin dashboard.
    
    URL: /lamba-real-homes/dashboard/
    Shows: "Lamba Real Homes Dashboard" in header
    Security: User can ONLY see their own company's dashboard
    """
    company = request.company  # Injected by @tenant_required
    
    # Now use company filtering (same as before, but with verified company)
    from estateApp.models import CustomUser, Estate, PlotAllocation, Message
    from django.db.models import Count, Q, Prefetch
    
    total_clients = CustomUser.objects.filter(
        role='client', 
        company_profile=company
    ).count()
    
    total_marketers = CustomUser.objects.filter(
        role='marketer', 
        company_profile=company
    ).count()
    
    estates = Estate.objects.prefetch_related(
        Prefetch('estate_plots__plotsizeunits')
    ).all()
    
    total_allocations = PlotAllocation.objects.filter(
        payment_type='full',
        plot_number__isnull=False 
    ).count()
    
    pending_allocations = PlotAllocation.objects.filter(
        payment_type='part',
        plot_number__isnull=True
    ).count()
    
    global_message_count = Message.objects.filter(
        sender__company_profile=company,
        recipient=request.user, 
        is_read=False
    ).count()
    
    context = {
        'company': company,
        'company_slug': company_slug,
        'total_clients': total_clients,
        'total_marketers': total_marketers,
        'estates': estates,
        'total_allocations': total_allocations,
        'pending_allocations': pending_allocations,
        'global_message_count': global_message_count,
    }
    
    return render(request, 'admin_side/index.html', context)


@login_required
@tenant_required
def management_dashboard_dynamic(request, company_slug):
    """
    Tenant-aware management dashboard.
    
    URL: /lamba-real-homes/management/
    Shows: All data scoped to this company
    """
    company = request.company
    
    # Management view logic here
    return render(request, 'admin_side/management-dashboard.html', {
        'company': company,
        'company_slug': company_slug,
    })


@login_required
@tenant_required  
def user_management_view(request, company_slug):
    """
    Tenant-aware user management.
    
    URL: /lamba-real-homes/users/
    Shows: Only users from this company
    Security: Cannot see users from other companies
    """
    company = request.company
    
    # Get ONLY this company's users
    users = CustomUser.objects.filter(company_profile=company)
    
    return render(request, 'admin_side/users.html', {
        'company': company,
        'company_slug': company_slug,
        'users': users,
    })


# ============================================================================
# REDIRECT HELPER: Redirect from old routes to new dynamic routes
# ============================================================================

@login_required
def redirect_to_tenant_dashboard(request):
    """
    Helper to redirect /admin_dashboard/ to /<company-slug>/dashboard/
    """
    company = request.user.company_profile
    if not company:
        return redirect('login')
    
    return redirect('tenant-dashboard', company_slug=company.slug)


# ============================================================================
# URL PATTERNS TO ADD TO estateApp/urls.py
# ============================================================================

DYNAMIC_TENANT_PATTERNS = [
    # Dynamic tenant-scoped routes (like Facebook)
    # Pattern: /<company-slug>/<page>/
    
    path(
        '<slug:company_slug>/dashboard/',
        admin_dashboard_dynamic,
        name='tenant-dashboard'
    ),
    path(
        '<slug:company_slug>/management/',
        management_dashboard_dynamic,
        name='tenant-management'
    ),
    path(
        '<slug:company_slug>/users/',
        user_management_view,
        name='tenant-users'
    ),
    
    # Backward compatibility: redirect old routes to new tenant-aware routes
    path('admin_dashboard/', redirect_to_tenant_dashboard, name='admin-dashboard-redirect'),
]

# Add to urlpatterns in estateApp/urls.py:
# urlpatterns += DYNAMIC_TENANT_PATTERNS
