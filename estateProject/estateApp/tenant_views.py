# FACEBOOK-STYLE DYNAMIC TENANT ROUTING IMPLEMENTATION
# File: estateApp/tenant_views.py

"""
IMPLEMENTATION GUIDE:

This provides secure, user-friendly tenant-aware routing similar to Facebook.

EXAMPLES:
  Facebook: https://web.facebook.com/victor.godwin.841340
  Our app: 
    - https://yourdomain.com/lamba-real-homes/dashboard/
    - https://yourdomain.com/lamba-real-homes/management/
    - https://yourdomain.com/lamba-real-homes/users/
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.db.models import Count, Q, Prefetch, OuterRef, Exists
from estateApp.models import (
    Company, CustomUser, Estate, PlotAllocation, Message,
    Transaction, PromotionalOffer, PropertyPrice, PlotSizeUnits
)
from decimal import Decimal
from functools import wraps

# ============================================================================
# SECURITY DECORATORS
# ============================================================================

def tenant_context_required(view_func):
    """
    SECURITY DECORATOR: Validates tenant (company) access before executing view.
    
    This decorator:
    ✅ Validates company slug exists
    ✅ Verifies user belongs to company
    ✅ Injects company into request context
    ✅ Prevents unauthorized access
    ✅ Returns 403 for access violations
    """
    @wraps(view_func)
    def wrapper(request, company_slug, *args, **kwargs):
        # Step 1: Validate company exists
        try:
            company = Company.objects.get(slug=company_slug)
        except Company.DoesNotExist:
            # Invalid slug - return 404
            return HttpResponseNotFound("Company not found")
        
        # Step 2: Check user has access to this company
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Super admin can access any company
        if request.user.role == 'superadmin':
            request.company = company
            request.company_slug = company_slug
            return view_func(request, company_slug, *args, **kwargs)
        
        # Regular users can ONLY access their own company
        if request.user.company_profile != company:
            # User trying to access other company's data - FORBIDDEN
            return HttpResponseForbidden(
                "❌ Access Denied: You can only access your own company's dashboard"
            )
        
        # Step 3: Inject company into request (available in view as request.company)
        request.company = company
        request.company_slug = company_slug
        
        # Step 4: Execute view with verified company context
        return view_func(request, company_slug, *args, **kwargs)
    
    return wrapper


# ============================================================================
# TENANT-AWARE VIEWS (Facebook-style)
# ============================================================================

@login_required
@tenant_context_required
def tenant_admin_dashboard(request, company_slug):
    """
    URL: /<company-slug>/dashboard/
    Example: /lamba-real-homes/dashboard/
    
    Shows admin dashboard for the specific company.
    SECURITY: User can ONLY see data from their own company.
    """
    company = request.company
    
    # Get company-scoped data
    total_clients = CustomUser.objects.filter(
        role='client',
        company_profile=company
    ).count()
    
    total_marketers = CustomUser.objects.filter(
        role='marketer',
        company_profile=company
    ).count()
    
    # Estates scoped to this company to prevent cross-tenant leakage
    estates = Estate.objects.prefetch_related(
        Prefetch('estate_plots__plotsizeunits',
                 queryset=PlotSizeUnits.objects.annotate(
                     allocated=Count('allocations', filter=Q(allocations__payment_type='full')),
                     reserved=Count('allocations', filter=Q(allocations__payment_type='part'))
                 ))
    ).filter(company=company)

    # Allocations should be counted only for this company
    total_allocations = PlotAllocation.objects.filter(
        estate__company=company,
        payment_type='full',
        plot_number__isnull=False
    ).count()

    pending_allocations = PlotAllocation.objects.filter(
        estate__company=company,
        payment_type='part',
        plot_number__isnull=True
    ).count()
    
    # Company-scoped messages
    global_message_count = Message.objects.filter(
        sender__company_profile=company,
        recipient=request.user, 
        is_read=False
    ).count()
    
    unread_messages = Message.objects.filter(
        sender__company_profile=company,
        recipient=request.user, 
        is_read=False
    ).order_by('-date_sent')[:5]
    
    # Build company-scoped chart data for Estate Allocation Trends (used by index.html)
    import json
    estates_names = []
    allocated_data = []
    reserved_data = []
    total_data = []

    for estate in Estate.objects.filter(company=company).order_by('name'):
        total_allocated = 0
        total_reserved = 0
        # estate_plots is related name; iterate plots then their plot size units
        for ep in estate.estate_plots.all():
            for size_unit in ep.plotsizeunits.all():
                total_allocated += getattr(size_unit, 'full_allocations', 0)
                total_reserved += getattr(size_unit, 'part_allocations', 0)

        estates_names.append(estate.name)
        allocated_data.append(total_allocated)
        reserved_data.append(total_reserved)
        total_data.append(total_allocated + total_reserved)

    chart_data = json.dumps({
        'estates': estates_names,
        'allocated': allocated_data,
        'reserved': reserved_data,
        'total': total_data,
    })

    context = {
        'company': company,
        'company_slug': company_slug,
        'company_name': company.company_name,  # For URL context
        'chart_data': chart_data,
        'total_clients': total_clients,
        'total_marketers': total_marketers,
        'estates': estates,
        'total_allocations': total_allocations,
        'pending_allocations': pending_allocations,
        'global_message_count': global_message_count,
        'unread_messages': unread_messages,
    }
    
    return render(request, 'admin_side/index.html', context)


@login_required
@tenant_context_required
def tenant_management_dashboard(request, company_slug):
    """
    URL: /<company-slug>/management/
    Example: /lamba-real-homes/management/
    
    Shows management dashboard for the specific company.
    SECURITY: Shows company-scoped clients and marketers only.
    """
    company = request.company
    from datetime import date
    from django.db.models import Prefetch, OuterRef, Exists
    from decimal import Decimal
    
    STATUSES = ['Fully Paid', 'Part Payment', 'Pending', 'Overdue']

    # ✅ SECURITY: Filter transactions by company
    transactions = Transaction.objects.select_related(
        'client', 'marketer',
        'allocation__estate',
        'allocation__plot_size_unit__plot_size'
    ).filter(
        client__company_profile=company
    ) | Transaction.objects.select_related(
        'client', 'marketer',
        'allocation__estate',
        'allocation__plot_size_unit__plot_size'
    ).filter(
        marketer__company_profile=company
    )

    txn_qs = Transaction.objects.filter(allocation_id=OuterRef('pk'))
    # Pending allocations only for this company
    pending_allocations = PlotAllocation.objects.annotate(
        has_txn=Exists(txn_qs)
    ).filter(has_txn=False, estate__company=company).select_related('client', 'estate')

    today = date.today()
    active_promos_qs = PromotionalOffer.objects.filter(
        start__lte=today, end__gte=today
    )
    # Only include estates that belong to this company
    estates = Estate.objects.prefetch_related(
        'estate_plots__plotsizeunits__plot_size',
        Prefetch('promotional_offers', queryset=active_promos_qs, to_attr='active_promos')
    ).filter(company=company)

    # Only promos affecting estates for this company
    current_promos = PromotionalOffer.objects.filter(
        start__lte=today,
        end__gte=today,
        estates__company=company
    ).prefetch_related('estates').distinct()

    # Property prices only for this company's estates
    existing_prices = {
        (pp.estate_id, pp.plot_unit_id): pp
        for pp in PropertyPrice.objects.select_related(
            'estate', 'plot_unit__plot_size'
        ).filter(estate__company=company)
    }

    rows = []
    for estate in estates:
        active = estate.active_promos[0] if getattr(estate, 'active_promos', []) else None
        for ep in estate.estate_plots.all():
            for unit in ep.plotsizeunits.all():
                key = (estate.id, unit.id)
                if key in existing_prices:
                    pp = existing_prices[key]
                    
                    # Convert current price to float for calculation
                    current_price = float(pp.current)
                    
                    # Apply promo discount if active
                    if active:
                        discount_factor = float(1 - active.discount / 100)
                        discounted_price = Decimal(str(current_price * discount_factor))
                    else:
                        discounted_price = pp.current
                    
                    # Calculate percentages using discounted price
                    if pp.previous:
                        percent_change = (float(discounted_price) - float(pp.previous)) / float(pp.previous) * 100
                        pp.percent_change = Decimal(str(percent_change))
                    if pp.presale:
                        overtime = (float(discounted_price) - float(pp.presale)) / float(pp.presale) * 100
                        pp.overtime = Decimal(str(overtime))
                    
                    # Store display values
                    pp.display_current = discounted_price
                    pp.active_promo = active
                    rows.append(pp)
                else:
                    class DummyPrice:
                        def __init__(self, est, unit, active_promo):
                            self.id = None
                            self.estate = est
                            self.plot_unit = unit
                            self.presale = None
                            self.previous = None
                            self.current = None
                            self.percent_change = None
                            self.overtime = None
                            self.display_current = None
                            self.effective = None
                            self.notes = None
                            self.active_promo = active_promo
                    rows.append(DummyPrice(estate, unit, active))

    # ✅ SECURITY: Filter clients and marketers by company
    all_clients = CustomUser.objects.filter(
        role='client',
        company_profile=company
    )
    
    all_marketers = CustomUser.objects.filter(
        role='marketer',
        company_profile=company
    )

    context = {
        'company': company,
        'company_slug': company_slug,
        'company_name': company.company_name,
        'all_clients': all_clients,
        'estates': estates,
        'marketers': all_marketers,
        'transactions': transactions,
        'pending_allocations': pending_allocations,
        'statuses': STATUSES,
        'rows': rows,
        'today': today,
        'current_promos': current_promos,
    }

    return render(request, 'admin_side/management-dashboard.html', context)


@login_required
@tenant_context_required
def tenant_user_management(request, company_slug):
    """
    URL: /<company-slug>/users/
    Example: /lamba-real-homes/users/
    
    Shows user management for the specific company.
    SECURITY: Cannot see users from other companies.
    """
    company = request.company
    
    # Get ONLY this company's users
    all_users = CustomUser.objects.filter(company_profile=company)
    
    admins = all_users.filter(role='admin')
    clients = all_users.filter(role='client')
    marketers = all_users.filter(role='marketer')
    support_staff = all_users.filter(role='support')
    
    context = {
        'company': company,
        'company_slug': company_slug,
        'company_name': company.company_name,
        'all_users': all_users,
        'admins': admins,
        'clients': clients,
        'marketers': marketers,
        'support_staff': support_staff,
    }
    
    return render(request, 'admin_side/users.html', context)


@login_required
@tenant_context_required
def tenant_company_settings(request, company_slug):
    """
    URL: /<company-slug>/settings/
    Example: /lamba-real-homes/settings/
    
    Company settings and configuration.
    """
    company = request.company
    
    context = {
        'company': company,
        'company_slug': company_slug,
        'company_name': company.company_name,
    }
    
    return render(request, 'admin_side/settings.html', context)


# ============================================================================
# BACKWARDS COMPATIBILITY REDIRECTS
# ============================================================================

@login_required
def redirect_admin_dashboard_to_tenant(request):
    """
    Redirects old route /admin_dashboard/ to new tenant-aware route.
    Example: /admin_dashboard/ → /lamba-real-homes/dashboard/
    """
    company = request.user.company_profile
    if not company:
        return redirect('login')
    
    return redirect('tenant-dashboard', company_slug=company.slug)


@login_required
def redirect_management_to_tenant(request):
    """
    Redirects old route /management-dashboard to new tenant-aware route.
    """
    company = request.user.company_profile
    if not company:
        return redirect('login')
    
    return redirect('tenant-management', company_slug=company.slug)


# ============================================================================
# HOW TO IMPLEMENT (Add to estateApp/urls.py)
# ============================================================================

"""
from .tenant_views import (
    tenant_admin_dashboard,
    tenant_management_dashboard,
    tenant_user_management,
    tenant_company_settings,
    redirect_admin_dashboard_to_tenant,
    redirect_management_to_tenant,
)

# Add these URL patterns to urlpatterns:

TENANT_AWARE_PATTERNS = [
    # Facebook-style dynamic tenant routes
    path(
        '<slug:company_slug>/dashboard/',
        tenant_admin_dashboard,
        name='tenant-dashboard'
    ),
    path(
        '<slug:company_slug>/management/',
        tenant_management_dashboard,
        name='tenant-management'
    ),
    path(
        '<slug:company_slug>/users/',
        tenant_user_management,
        name='tenant-users'
    ),
    path(
        '<slug:company_slug>/settings/',
        tenant_company_settings,
        name='tenant-settings'
    ),
    
    # Backward compatibility redirects
    path(
        'admin_dashboard/',
        redirect_admin_dashboard_to_tenant,
        name='admin-dashboard-legacy'
    ),
    path(
        'management-dashboard/',
        redirect_management_to_tenant,
        name='management-dashboard-legacy'
    ),
]

urlpatterns += TENANT_AWARE_PATTERNS
"""
