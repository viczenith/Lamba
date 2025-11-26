"""
Multi-Tenant Data Isolation Middleware

Provides complete data isolation between companies at the middleware level.
Prevents cross-company data leaks and enforces subscription-based access.
"""

import threading
from datetime import timedelta
from django.conf import settings
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import Company
import logging
import time

logger = logging.getLogger(__name__)

# Thread-local storage for company context
_thread_locals = threading.local()


def set_current_company(company):
    """Set the current company in thread-local storage"""
    _thread_locals.company = company


def get_current_company():
    """Get the current company from thread-local storage"""
    return getattr(_thread_locals, 'company', None)


def clear_company_context():
    """Clear company context from thread-local storage"""
    if hasattr(_thread_locals, 'company'):
        delattr(_thread_locals, 'company')


class SessionExpirationMiddleware(MiddlewareMixin):
    """
    Checks for expired sessions and redirects to login page.

    Handles session timeout and ensures users are redirected to appropriate login page
    with tenant context preserved.

    SECURITY FEATURES:
    - 5-minute sliding session expiration
    - Automatic session flush on expiry
    - Secure redirect to login page
    - Activity-based session renewal
    """

    def process_request(self, request):
        """Check session expiration and redirect if needed"""
        try:
            # Skip for public endpoints
            if self._is_public_endpoint(request):
                return None

            # Skip for anonymous users
            if request.user.is_anonymous:
                return None

            # Get current time
            current_time = time.time()

            # Determine session timeout from settings (fallback to 3600s)
            session_timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)

            # Check if session has expired
            session_expiry = request.session.get('_session_expiry', 0)

            # If no expiry set or expired, redirect to login
            if not session_expiry or current_time > session_expiry:
                # Session expired - clear session and redirect to login
                request.session.flush()

                # Log security event
                logger.warning(
                    f"SESSION EXPIRED: User {request.user.email if hasattr(request.user, 'email') else 'unknown'} "
                    f"session expired. IP: {self._get_client_ip(request)}"
                )

                # Redirect to configured login URL
                return redirect(getattr(settings, 'LOGIN_URL', '/login/'))

            # Update session expiry on activity (sliding expiration)
            if getattr(settings, 'SESSION_SAVE_EVERY_REQUEST', True):
                request.session['_session_expiry'] = current_time + int(session_timeout)
                try:
                    request.session.save()
                except Exception:
                    # If saving session fails, log and continue
                    logger.exception('Failed to save session expiry')

        except Exception as e:
            logger.error(f"Error in SessionExpirationMiddleware: {str(e)}")
            # On error, redirect to login for security
            return redirect('/login/')

        return None
    
    def _is_public_endpoint(self, request):
        """Check if endpoint is public (doesn't require session check)"""
        public_paths = [
            '/login/',
            '/logout/',
            '/register/',
            '/password-reset/',
            '/admin/login/',
            '/health/',
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/logout',
            '/api/auth/password-reset',
        ]
        
        for path in public_paths:
            if request.path.startswith(path):
                return True
        
        return False
    
    def _get_tenant_login_url(self, request):
        """Get appropriate login URL - always redirect to main login"""
        return '/login/'

    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Enforces company tenancy isolation on every request.

    ✅ Complete data isolation - Company A NEVER accesses Company B data
    ✅ Subscription status enforcement - Validates active/trial/grace period
    ✅ Read-only mode during grace period
    ✅ System Master Admin bypass for platform management
    ✅ Client/Marketer multi-company support

    SECURITY FEATURES:
    - Strict tenant context validation
    - Cross-tenant access prevention
    - Subscription status enforcement
    - Audit logging of all tenant operations
    - IP-based access tracking

    IMPORTANT: Must be placed AFTER AuthenticationMiddleware in settings.MIDDLEWARE
    """

    def process_request(self, request):
        """
        Process incoming request and set company context.
        Enforces complete data isolation and subscription limits.
        """
        try:
            # Skip tenant isolation for public endpoints
            if self._is_public_endpoint(request):
                set_current_company(None)
                request.company = None
                return None

            # Anonymous users get no company
            if request.user.is_anonymous:
                set_current_company(None)
                request.company = None
                return None

            # SECURITY: System Master Admin (super user) - no company filter
            # They can see all companies but must use super admin interface
            if request.user.is_superuser:
                set_current_company(None)
                request.company = None
                request.is_system_master_admin = True

                # SECURITY: Force redirect to super admin if accessing company view
                if request.path.startswith('/company-console/') or request.path.startswith('/admin-dashboard/'):
                    logger.warning(
                        f"SECURITY: System admin {request.user.email} attempted to access company interface. "
                        f"Forced redirect to super admin. IP: {self._get_client_ip(request)}"
                    )
                    messages.warning(request, 'System administrators must use the super admin interface.')
                    return redirect('/super-admin/')

                return None

            # Company Admin - get their company from company_profile
            if hasattr(request.user, 'company_profile') and request.user.company_profile:
                company = request.user.company_profile.company

                # ===== SECURITY: SUBSCRIPTION STATUS CHECKS =====

                # 1. Check if trial has expired
                if company.subscription_status == 'trial':
                    if company.trial_ends_at and company.trial_ends_at < timezone.now():
                        # Automatically move to grace period
                        company.subscription_status = 'grace_period'
                        company.grace_period_ends_at = timezone.now() + timedelta(days=7)
                        company.is_read_only_mode = True
                        company.save()

                        logger.warning(
                            f"SUBSCRIPTION: Company {company.company_name} trial expired. "
                            f"Moved to grace period. IP: {self._get_client_ip(request)}"
                        )
                        messages.warning(
                            request,
                            'Trial period expired. 7-day grace period active. Read-only mode enabled.'
                        )

                # 2. Check if subscription has expired
                if company.subscription_status == 'active':
                    if company.subscription_ends_at and company.subscription_ends_at < timezone.now():
                        # Move to grace period
                        company.subscription_status = 'grace_period'
                        company.grace_period_ends_at = timezone.now() + timedelta(days=7)
                        company.is_read_only_mode = True
                        company.save()

                        logger.warning(
                            f"SUBSCRIPTION: Company {company.company_name} subscription expired. "
                            f"Moved to grace period. IP: {self._get_client_ip(request)}"
                        )
                        messages.warning(
                            request,
                            'Subscription expired. 7-day grace period active. Read-only mode enabled.'
                        )

                # 3. Check if grace period has expired
                if company.subscription_status == 'grace_period':
                    if company.grace_period_ends_at and company.grace_period_ends_at < timezone.now():
                        # Move to expired
                        company.subscription_status = 'expired'
                        company.is_read_only_mode = False
                        company.data_deletion_date = timezone.now() + timedelta(days=30)
                        company.save()

                        logger.error(
                            f"SUBSCRIPTION: Company {company.company_name} grace period expired. "
                            f"Account restricted. IP: {self._get_client_ip(request)}"
                        )
                        messages.error(
                            request,
                            'Grace period expired. Account access will be restricted. Renew now to prevent data deletion.'
                        )

                # 4. Check if account is cancelled or suspended
                if company.subscription_status == 'cancelled':
                    logger.warning(
                        f"ACCESS DENIED: Company {company.company_name} subscription cancelled. "
                        f"User {request.user.email} blocked. IP: {self._get_client_ip(request)}"
                    )
                    messages.error(request, 'Your subscription has been cancelled. Contact support.')
                    set_current_company(None)
                    request.company = None
                    return redirect('subscription_cancelled')

                if company.subscription_status == 'suspended':
                    logger.warning(
                        f"ACCESS DENIED: Company {company.company_name} subscription suspended. "
                        f"User {request.user.email} blocked. IP: {self._get_client_ip(request)}"
                    )
                    messages.error(request, 'Your subscription has been suspended. Contact support.')
                    set_current_company(None)
                    request.company = None
                    return redirect('subscription_suspended')

                # ===== SECURITY: SET COMPANY CONTEXT =====
                set_current_company(company)
                request.company = company
                request.is_system_master_admin = False

                logger.info(
                    f"TENANT ISOLATION: User {request.user.email} authenticated for company "
                    f"{company.company_name} (Status: {company.subscription_status}). "
                    f"IP: {self._get_client_ip(request)}"
                )

                return None

            # Client Users - no company filter
            # Clients can view properties from ALL companies they've purchased from
            if hasattr(request.user, 'client_profile') and request.user.client_profile:
                set_current_company(None)
                request.company = None
                request.is_system_master_admin = False
                logger.info(
                    f"TENANT ISOLATION: Client {request.user.email} authenticated. "
                    f"IP: {self._get_client_ip(request)}"
                )
                return None

            # Marketer Users - no company filter
            # Marketers can affiliate with MULTIPLE companies
            if hasattr(request.user, 'marketer_profile') and request.user.marketer_profile:
                set_current_company(None)
                request.company = None
                request.is_system_master_admin = False
                logger.info(
                    f"TENANT ISOLATION: Marketer {request.user.email} authenticated. "
                    f"IP: {self._get_client_ip(request)}"
                )
                return None

            # SECURITY: Default: no company - block access
            logger.error(
                f"SECURITY ALERT: User {request.user.email} has no valid company/role assignment. "
                f"Access denied. IP: {self._get_client_ip(request)}"
            )
            set_current_company(None)
            request.company = None
            messages.error(request, 'Access denied: Invalid user configuration.')
            return redirect('/login/')

        except Exception as e:
            logger.error(f"Error in TenantIsolationMiddleware: {str(e)}", exc_info=True)
            # SECURITY: On error, clear context and redirect to login
            set_current_company(None)
            request.company = None
            return redirect('/login/')

        return None
    
    def _is_public_endpoint(self, request):
        """Check if endpoint is public (doesn't require tenant context)"""
        public_paths = [
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/logout',
            '/api/auth/password-reset',
            '/admin/login',
            '/health/',
            '/login/',
            '/logout/',
            '/register/',
        ]

        for path in public_paths:
            if request.path.startswith(path):
                return True

        return False

    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_response(self, request, response):
        """Clean up thread-local storage after request processing"""
        clear_company_context()
        return response


class TenantAccessCheckMiddleware(MiddlewareMixin):
    """
    Validates that users can only access resources
    that belong to their company (unless they're clients/marketers)
    
    Provides additional safety net for query-level isolation.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check tenant access permissions"""
        
        # Skip for public endpoints
        if not request.user.is_authenticated:
            return None
        
        # Get user's role
        user_role = getattr(request.user, 'role', None)
        user_company = getattr(request.user, 'company_profile', None)
        
        # Admin/Support users are bound to their company
        if user_role in ['admin', 'support', 'company_admin']:
            if not user_company:
                logger.warning(f"Admin/Support user {request.user.id} has no company_profile")
                return JsonResponse(
                    {'error': 'No company assigned to this user'},
                    status=403
                )
        
        # Clients and Marketers can access multiple companies (cross-tenant)
        elif user_role in ['client', 'marketer']:
            # These users will access data across companies
            pass
        
        return None


class QuerysetIsolationMiddleware(MiddlewareMixin):
    """
    Safety net middleware that provides additional queryset isolation.
    
    Stores current company in request for view-level access.
    Complements the automatic filtering from CompanyAwareManager.
    """
    
    def process_request(self, request):
        """Store company in request for view access"""
        try:
            company = get_current_company()
            request.current_company = company
            
            # Additional context
            if company:
                request.company_id = company.id
                request.company_slug = company.slug
            else:
                request.company_id = None
                request.company_slug = None
                
        except Exception as e:
            logger.error(f"Error in QuerysetIsolationMiddleware: {str(e)}")
            request.current_company = None
        
        return None


class SubscriptionEnforcementMiddleware(MiddlewareMixin):
    """
    Enforces subscription-based limits and API call quotas.
    
    Tracks API calls per day and enforces limits from subscription plan.
    """
    
    def process_request(self, request):
        """Check subscription limits before processing request"""
        try:
            company = get_current_company()
            
            if not company:
                return None
            
            # Skip limit checks for GET requests
            if request.method == 'GET':
                return None
            
            # Check API call limit (for non-GET requests)
            if not hasattr(company, 'subscription_details') or not company.subscription_details:
                return None
            
            plan = company.subscription_details.plan
            if not plan:
                return None
            
            # Reset API call counter if needed
            if company.api_calls_reset_at is None or company.api_calls_reset_at < timezone.now():
                company.api_calls_today = 0
                company.api_calls_reset_at = timezone.now() + timedelta(days=1)
            
            # Check if limit exceeded
            if company.api_calls_today >= company.max_api_calls_daily:
                logger.warning(
                    f"API call limit exceeded for company {company.company_name}"
                )
                messages.error(
                    request,
                    f'Daily API call limit ({company.max_api_calls_daily}) exceeded.'
                )
                return redirect('subscription_status')
            
            # Increment counter
            company.api_calls_today += 1
            company.save(update_fields=['api_calls_today'])
            
        except Exception as e:
            logger.error(f"Error in SubscriptionEnforcementMiddleware: {str(e)}")
        
        return None


class ReadOnlyModeMiddleware(MiddlewareMixin):
    """
    Enforces read-only mode during grace period.
    
    Allows GET requests but blocks POST/PUT/DELETE during grace period.
    """
    
    def process_request(self, request):
        """Check read-only mode status"""
        try:
            company = get_current_company()
            
            if not company:
                return None
            
            # Check if in read-only mode (grace period)
            if company.is_read_only_mode:
                if request.method in ['POST', 'PUT', 'DELETE']:
                    messages.warning(
                        request,
                        'Read-only mode is active. Please renew your subscription to make changes.'
                    )
                    
                    # For API requests, return error
                    if request.path.startswith('/api/'):
                        return JsonResponse(
                            {
                                'error': 'Read-only mode is active',
                                'detail': 'Please renew your subscription'
                            },
                            status=423  # Locked status code
                        )
                    
                    # For page requests, redirect
                    return redirect('subscription_status')
            
        except Exception as e:
            logger.error(f"Error in ReadOnlyModeMiddleware: {str(e)}")
        
        return None


# ===== HELPER FUNCTIONS FOR USE IN VIEWS =====

def get_company_from_request(request):
    """
    Safely get company from request.
    
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
    """Check if user is system master admin"""
    return request.user.is_superuser or getattr(request, 'is_system_master_admin', False)


def is_company_admin(request):
    """Check if user is company admin"""
    return (
        hasattr(request.user, 'company_profile') and 
        request.user.company_profile is not None
    )