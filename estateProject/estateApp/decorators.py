"""
Company Admin Tenancy Decorators & Data Isolation Enforcement

Decorators for enforcing complete data isolation, subscription requirements,
and role-based access control in Django views and API endpoints.

These decorators work in conjunction with middleware.py to provide:
  ✅ Complete company data isolation
  ✅ Subscription-based feature access
  ✅ Role-based permission checking
  ✅ Read-only mode enforcement
  ✅ Grace period handling
  ✅ Audit logging of access attempts
"""

import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .middleware import get_current_company

logger = logging.getLogger(__name__)


# ===== ROLE-BASED ACCESS CONTROL DECORATORS =====

# Allowed admin roles for admin panel access (NOT support - they have their own dashboard)
ADMIN_ROLES = ('admin', 'secondary_admin', 'company_admin')

# Support roles for admin support dashboard
SUPPORT_ROLES = ('support',)


def admin_required(view_func):
    """
    🔐 SECURITY DECORATOR: Ensures only admin-level users can access admin views.
    
    This decorator provides role-based access control for admin panel pages,
    preventing clients, marketers, AND support users from accessing admin functions.
    Support users have their own AdminSupport dashboard at /adminsupport/.
    
    Enforces:
    ✅ User must be authenticated
    ✅ User role must be admin, secondary_admin, or company_admin
    ✅ Blocks client, marketer, AND support roles
    ✅ Logs unauthorized access attempts for security monitoring
    
    Usage:
        @login_required
        @admin_required
        def add_estate(request):
            # Only admin users can access
            pass
    
    Security:
        - Works with @login_required for authentication
        - Complements TenantIsolationMiddleware for company isolation
        - Provides defense-in-depth against privilege escalation
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated (should already be handled by @login_required)
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to continue.')
            return redirect('login')
        
        # Get user role
        user_role = getattr(request.user, 'role', None)
        
        # Allow superadmin bypass (System Master Admin)
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has admin role
        if user_role not in ADMIN_ROLES:
            # Log security event
            logger.warning(
                f"🚫 SECURITY: Unauthorized admin access attempt by user {request.user.id} "
                f"(email: {request.user.email}, role: {user_role}) to {request.path}"
            )
            
            # Show user-friendly error
            messages.error(
                request, 
                '⛔ Access Denied: You do not have permission to access this admin page.'
            )
            
            # Redirect based on user role
            if user_role == 'client':
                return redirect('client-dashboard')
            elif user_role == 'marketer':
                return redirect('marketer_dashboard')
            elif user_role == 'support':
                # Support users have their own dashboard at /adminsupport/
                return redirect('adminsupport:support_dashboard')
            else:
                return redirect('login')
        
        # User is authorized - proceed to view
        return view_func(request, *args, **kwargs)
    
    return wrapper


def support_required(view_func):
    """
    🔐 SECURITY DECORATOR: Ensures only support staff can access AdminSupport views.
    
    This decorator provides role-based access control for AdminSupport pages.
    
    Enforces:
    ✅ User must be authenticated
    ✅ User role must be 'support'
    ✅ Blocks admin, client, and marketer roles
    
    Usage:
        @login_required
        @support_required
        def support_ticket_view(request):
            # Only support users can access
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to continue.')
            return redirect('login')
        
        user_role = getattr(request.user, 'role', None)
        
        # Allow superadmin bypass
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if user_role not in SUPPORT_ROLES:
            logger.warning(
                f"🚫 SECURITY: Unauthorized support access attempt by user {request.user.id} "
                f"(email: {request.user.email}, role: {user_role}) to {request.path}"
            )
            messages.error(request, '⛔ Access Denied: This page is for support staff only.')
            
            if user_role in ADMIN_ROLES:
                return redirect('admin-dashboard')
            elif user_role == 'client':
                return redirect('client-dashboard')
            elif user_role == 'marketer':
                return redirect('marketer_dashboard')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_or_support_required(view_func):
    """
    🔐 SECURITY DECORATOR: Allows only admin or support staff access.
    
    Similar to admin_required but explicitly for admin/support only (no secondary_admin).
    
    Usage:
        @login_required
        @admin_or_support_required
        def sensitive_admin_function(request):
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        user_role = getattr(request.user, 'role', None)
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if user_role not in ('admin', 'support'):
            logger.warning(
                f"🚫 SECURITY: Unauthorized access attempt by {request.user.email} "
                f"(role: {user_role}) to {request.path}"
            )
            messages.error(request, '⛔ Access Denied: Admin or support access required.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# ===== PRIMARY DECORATORS FOR VIEWS =====

def company_required(view_func):
    """
    Decorator to ensure only company admins can access company views.
    
    Enforces:
    ✅ User has company_profile (is company admin)
    ✅ Company context is set in middleware
    ✅ User belongs to current company
    ✅ Subscription is not cancelled/suspended
    ✅ Blocks expired subscriptions (post-grace period)
    
    Usage:
        @company_required
        def my_company_view(request):
            company = request.company
            # All data automatically filtered to this company
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Must have company profile (not client, not marketer)
        if not hasattr(request.user, 'company_profile') or not request.user.company_profile:
            messages.error(request, 'You must be a company admin to access this page.')
            return redirect('login')
        
        # Get company from context (set by TenantIsolationMiddleware)
        company = get_current_company()
        if not company:
            messages.error(request, 'Company context not found.')
            return redirect('login')
        
        # Verify user belongs to this company
        if request.user.company_profile.company != company:
            logger.warning(
                f"Security: User {request.user.id} attempted unauthorized access to {company.id}"
            )
            messages.error(request, 'You do not have access to this company.')
            return redirect('dashboard')
        
        # Check subscription status
        if company.subscription_status == 'cancelled':
            messages.error(request, 'Your subscription has been cancelled.')
            return redirect('subscription_status')
        
        if company.subscription_status == 'suspended':
            messages.error(request, 'Your subscription has been suspended.')
            return redirect('subscription_status')
        
        if company.subscription_status == 'expired':
            messages.error(
                request, 
                'Your subscription has expired. Please renew to continue.'
            )
            return redirect('subscription_status')
        
        # Pass company to view
        request.company = company
        return view_func(request, *args, **kwargs)
    
    return wrapper


def subscription_required(view_func):
    """
    Decorator to ensure subscription is active (not trial, not grace period).
    
    Enforces:
    ✅ Active or trial subscription status only
    ✅ Blocks grace period, expired, cancelled subscriptions
    ✅ Prevents feature access without paid subscription
    
    Usage for premium features:
        @company_required
        @subscription_required
        def upgrade_plan_view(request):
            # Both free trial and paid subscribers can access
    
    Note: Use @company_required first, then @subscription_required
    """
    @wraps(view_func)
    @company_required
    def wrapper(request, *args, **kwargs):
        company = request.company
        
        if company.subscription_status not in ['trial', 'active']:
            messages.error(
                request, 
                'This feature requires an active or trial subscription.'
            )
            return redirect('subscription_status')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def active_subscription_required(view_func):
    """
    Decorator to ensure subscription is ACTIVE (paid, not trial).
    
    Enforces:
    ✅ Active subscription status only
    ✅ Blocks trial users, grace period, and expired
    ✅ For premium features only available to paid subscribers
    
    Usage for premium-only features:
        @company_required
        @active_subscription_required
        def premium_feature_view(request):
            # Only paid subscribers can access
    """
    @wraps(view_func)
    @company_required
    def wrapper(request, *args, **kwargs):
        company = request.company
        
        if company.subscription_status != 'active':
            messages.error(
                request, 
                'This feature requires an active subscription. Please upgrade.'
            )
            return redirect('subscription_status')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def superadmin_required(view_func):
    """
    Decorator to ensure only System Master Admin can access.
    
    Enforces:
    ✅ Blocks company admins completely
    ✅ Only allows super users / System Master Admin
    ✅ Completely bypasses company isolation
    ✅ For platform management only
    
    Usage for platform management:
        @superadmin_required
        def manage_all_companies_view(request):
            # Only system admin can access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            logger.warning(
                f"Security: Non-super user {request.user.id} attempted to access super admin view {request.path}"
            )
            messages.error(request, 'Super admin access required.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def read_only_safe(view_func):
    """
    Decorator to allow GET but block write operations in grace period.
    
    Enforces:
    ✅ Allows GET requests always
    ✅ Blocks POST/PUT/DELETE if in read-only mode (grace period)
    ✅ Shows warning message for write attempts
    
    Usage:
        @company_required
        @read_only_safe
        def edit_plot_view(request):
            if request.method == 'POST':
                # Won't reach here if grace period active
                pass
    """
    @wraps(view_func)
    @company_required
    def wrapper(request, *args, **kwargs):
        company = request.company
        
        # Allow reads
        if request.method == 'GET':
            return view_func(request, *args, **kwargs)
        
        # Block writes in grace period
        if company.is_read_only_mode:
            messages.warning(
                request,
                'Read-only mode is active. Please renew your subscription to make changes.'
            )
            return redirect('subscription_status')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def permission_required_company(permission):
    """
    Decorator to check specific company admin permission.
    
    Checks if user has specific permission from CompanyProfile.permissions.
    
    Usage:
        @company_required
        @permission_required_company('can_manage_clients')
        def manage_clients_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @company_required
        def wrapper(request, *args, **kwargs):
            if not request.user.company_profile.has_permission(permission):
                logger.warning(
                    f"User {request.user.id} attempted action without permission: {permission}"
                )
                messages.error(
                    request,
                    f'You do not have permission to access this feature.'
                )
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


# ===== API ENDPOINT DECORATORS =====

def api_company_required(view_func):
    """
    Decorator for API endpoints requiring company context.
    
    Returns:
    ✅ JSON error if no company context (403 Forbidden)
    ✅ Validates company admin access
    ✅ Checks subscription status
    ✅ Proper HTTP status codes
    
    Usage:
        @api_view(['GET'])
        @api_company_required
        def api_get_plots(request):
            company = request.company
            # ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        company = get_current_company()
        
        if not company:
            return JsonResponse(
                {
                    'error': 'Company context not found',
                    'detail': 'Must be logged in as company admin'
                },
                status=403
            )
        
        # Verify user belongs to company
        if not hasattr(request.user, 'company_profile') or request.user.company_profile.company != company:
            logger.warning(
                f"Security: API access attempt by user {request.user.id} to wrong company"
            )
            return JsonResponse(
                {
                    'error': 'Unauthorized',
                    'detail': 'You do not have access to this company'
                },
                status=403
            )
        
        # Check subscription
        if company.subscription_status in ['cancelled', 'suspended', 'expired']:
            return JsonResponse(
                {
                    'error': 'Subscription required',
                    'detail': f'Subscription status: {company.subscription_status}'
                },
                status=402  # Payment required
            )
        
        request.company = company
        return view_func(request, *args, **kwargs)
    
    return wrapper


def api_subscription_required(view_func):
    """
    Decorator for API endpoints requiring active subscription.
    
    Returns:
    ✅ 402 Payment Required if no active subscription
    ✅ Allows trial subscriptions
    ✅ Blocks grace period, expired, cancelled
    
    Usage:
        @api_view(['GET'])
        @api_company_required
        @api_subscription_required
        def api_premium_endpoint(request):
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        company = request.company if hasattr(request, 'company') else get_current_company()
        
        if not company:
            return JsonResponse(
                {'error': 'Company context not found'},
                status=403
            )
        
        if company.subscription_status not in ['trial', 'active']:
            return JsonResponse(
                {
                    'error': 'Subscription required',
                    'detail': f'Current status: {company.subscription_status}'
                },
                status=402
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def api_read_only_check(view_func):
    """
    Decorator for API endpoints to check read-only mode.
    
    Returns:
    ✅ 423 Locked if in read-only mode and trying write operation
    ✅ Allows GET requests always
    ✅ Blocks POST/PUT/DELETE during grace period
    
    Usage:
        @api_view(['POST'])
        @api_company_required
        @api_read_only_check
        def api_create_plot(request):
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        company = request.company if hasattr(request, 'company') else get_current_company()
        
        if not company:
            return JsonResponse(
                {'error': 'Company context not found'},
                status=403
            )
        
        # Block write operations in grace period
        if company.is_read_only_mode and request.method in ['POST', 'PUT', 'DELETE']:
            return JsonResponse(
                {
                    'error': 'Read-only mode active',
                    'detail': 'Subscription in grace period. Please renew.',
                    'grace_period_ends_at': company.grace_period_ends_at.isoformat() if company.grace_period_ends_at else None
                },
                status=423  # Locked
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# ===== HELPER FUNCTIONS =====

def get_company_from_request(request):
    """
    Safely get company from request.
    
    Returns current company if set, otherwise None.
    
    Usage in views:
        company = get_company_from_request(request)
        if not company:
            return redirect('login')
    """
    company = get_current_company()
    if not company and hasattr(request, 'company'):
        company = request.company
    
    return company


def is_system_master_admin(request):
    """Check if user is system master admin (super user)"""
    return request.user.is_superuser or getattr(request, 'is_system_master_admin', False)


def is_company_admin(request):
    """Check if user is company admin"""
    return (
        hasattr(request.user, 'company_profile') and 
        request.user.company_profile is not None
    )



def require_system_admin(view_func):
    """
    Decorator to require system admin access for Django views.
    Redirects unauthorized users to login or access denied page.
    
    Usage:
        @require_system_admin
        def tenant_admin_view(request):
            pass
    """
    @wraps(view_func)
    @login_required(login_url='tenant-admin-login')
    def wrapped_view(request, *args, **kwargs):
        # Check if user is system admin
        is_system_admin = getattr(request.user, 'is_system_admin', False)
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if not is_system_admin or admin_level != 'system':
            # Log unauthorized access attempt
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_unauthorized_access(
                user=request.user,
                action='denied_tenant_admin_access',
                resource='tenant_admin_dashboard',
                request=request,
                reason='Not a system administrator'
            )
            
            # Return error response
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: System admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return JsonResponse(
                    {
                        'error': 'Access Denied: System admin access required',
                        'status': 'unauthorized'
                    },
                    status=403
                )
        
        # Log successful access
        from estateApp.audit_logging import AuditLogger
        AuditLogger.log_admin_access(
            user=request.user,
            action='tenant_admin_access',
            resource='tenant_admin_dashboard',
            request=request
        )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def require_admin_level(required_level='system'):
    """
    Decorator to check specific admin level.
    
    Args:
        required_level: 'system' (only system admins) or 'company' (system or company admins)
    
    Usage:
        @require_admin_level('system')
        def system_only_view(request):
            pass
        
        @require_admin_level('company')
        def company_admin_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def wrapped_view(request, *args, **kwargs):
            user_level = getattr(request.user, 'admin_level', 'none')
            
            # Check if user has required level
            if required_level == 'system':
                has_access = user_level == 'system'
            elif required_level == 'company':
                has_access = user_level in ['system', 'company']
            else:
                has_access = False
            
            if not has_access:
                # Log unauthorized access
                from estateApp.audit_logging import AuditLogger
                AuditLogger.log_unauthorized_access(
                    user=request.user,
                    action=f'denied_{required_level}_admin_access',
                    resource=f'{required_level}_admin_view',
                    request=request,
                    reason=f'Required level: {required_level}, User level: {user_level}'
                )
                
                error_msg = f'Access Denied: {required_level.title()} admin access required'
                
                if request.path.startswith('/api/'):
                    return Response(
                        {'error': error_msg},
                        status=status.HTTP_403_FORBIDDEN
                    )
                else:
                    return JsonResponse({'error': error_msg}, status=403)
            
            # Log successful access
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_admin_action(
                user=request.user,
                action=f'accessed_{required_level}_admin_view',
                resource=f'{required_level}_admin_view',
                request=request
            )
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def require_company_admin(view_func):
    """
    Decorator to require company admin access.
    Allows both system admins and company admins (for their own company).
    
    Usage:
        @require_company_admin
        def company_admin_view(request):
            pass
    """
    @wraps(view_func)
    @login_required(login_url='login')
    def wrapped_view(request, *args, **kwargs):
        admin_level = getattr(request.user, 'admin_level', 'none')
        
        if admin_level not in ['system', 'company']:
            # Log unauthorized access
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_unauthorized_access(
                user=request.user,
                action='denied_company_admin_access',
                resource='company_admin_view',
                request=request,
                reason='Not an admin'
            )
            
            if request.path.startswith('/api/'):
                return Response(
                    {'error': 'Access Denied: Admin access required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return JsonResponse({'error': 'Access Denied: Admin access required'}, status=403)
        
        # Log successful access
        from estateApp.audit_logging import AuditLogger
        AuditLogger.log_admin_action(
            user=request.user,
            action='accessed_company_admin_view',
            resource='company_admin_view',
            request=request
        )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def verify_jwt_scope(required_scope='tenant_admin'):
    """
    Decorator to verify JWT scope claim.
    Used for API endpoints that require specific JWT scope.
    
    Usage:
        @verify_jwt_scope('tenant_admin')
        def tenant_admin_api_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Get token from request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if not auth_header.startswith('Bearer '):
                return Response(
                    {'error': 'Missing or invalid authorization header'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            token = auth_header.split(' ')[1]
            
            try:
                # Decode JWT
                from estateApp.utils import decode_jwt_token
                decoded = decode_jwt_token(token)
                
                # Check scope
                if decoded.get('scope') != required_scope:
                    return Response(
                        {'error': f'Invalid scope: required {required_scope}'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Attach decoded token to request for use in view
                request.token_claims = decoded
                
            except Exception as e:
                return Response(
                    {'error': f'Invalid token: {str(e)}'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def check_company_ownership(view_func):
    """
    Decorator to verify user owns the company being accessed.
    Company ID should be in request.POST, request.GET, or kwargs.
    
    Usage:
        @check_company_ownership
        def company_view(request, company_id):
            pass
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Get company_id from various sources
        company_id = (
            kwargs.get('company_id') or
            request.POST.get('company_id') or
            request.GET.get('company_id')
        )
        
        if not company_id:
            return Response(
                {'error': 'Company ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # System admins can access any company
        if getattr(request.user, 'is_system_admin', False):
            return view_func(request, *args, **kwargs)
        
        # Company admins can only access their own company
        user_company_id = getattr(request.user.company_profile, 'id', None)
        
        if not user_company_id or str(user_company_id) != str(company_id):
            from estateApp.audit_logging import AuditLogger
            AuditLogger.log_unauthorized_access(
                user=request.user,
                action='denied_company_access',
                resource=f'company_{company_id}',
                request=request,
                reason='Company ownership mismatch'
            )
            
            return Response(
                {'error': 'You can only access your own company'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def audit_action(action_type='unknown', resource='unknown'):
    """
    Decorator to automatically log admin actions to audit trail.
    
    Usage:
        @audit_action('create', 'user')
        def create_user_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            from estateApp.audit_logging import AuditLogger
            
            try:
                # Execute the view
                response = view_func(request, *args, **kwargs)
                
                # Log successful action
                status_code = getattr(response, 'status_code', 200)
                
                if 200 <= status_code < 300:
                    AuditLogger.log_admin_action(
                        user=request.user,
                        action=action_type,
                        resource=resource,
                        request=request,
                        status='success',
                        details={'status_code': status_code}
                    )
                else:
                    AuditLogger.log_admin_action(
                        user=request.user,
                        action=action_type,
                        resource=resource,
                        request=request,
                        status='failure',
                        details={'status_code': status_code}
                    )
                
                return response
            
            except Exception as e:
                # Log error
                AuditLogger.log_admin_action(
                    user=request.user,
                    action=action_type,
                    resource=resource,
                    request=request,
                    status='error',
                    details={'error': str(e)}
                )
                raise
        
        return wrapped_view
    return decorator
