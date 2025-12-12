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
from django.http import JsonResponse, HttpResponseForbidden
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


# ===== ADVANCED SECURITY MIDDLEWARE =====

from estateApp.security import (
    RateLimiter,
    SecurityValidator,
    SecureTokenGenerator,
    _log_security_event,
    _track_user_activity
)
from django.contrib.auth import logout


class AdvancedSecurityMiddleware(MiddlewareMixin):
    """
    Comprehensive security middleware for all requests.
    
    Provides:
    - Request validation and sanitization
    - Rate limiting per IP and user
    - Session integrity checking
    - Role-based URL protection
    - Suspicious activity detection
    """
    
    # URLs that don't require full security checks
    EXEMPT_URLS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/api/health/',
        '/chat_unread_count/',  # AJAX polling endpoint - high frequency
    ]
    
    # URLs that require stricter rate limiting
    SENSITIVE_URLS = [
        '/login/',
        '/register/',
        '/password-reset/',
        '/change-password/',
        '/profile/update/',
    ]
    
    # Client-side URLs (require client role)
    # Uses startswith() so /my-companies/8/ is covered by /my-companies/
    CLIENT_URLS = [
        '/client-dashboard',
        '/my-client-profile',
        '/my-companies/',          # Covers /my-companies/8/, /my-companies/slug/
        '/chat/',                  # Covers /chat/, /chat/delete/1/, /chat/dashboard/
        '/property-list',
        '/view-all-requests',
        '/view-client-estate/',    # Covers /view-client-estate/6/28/
        '/client-new-property-request',
        '/client-dashboard-cross-company',
        '/c/',                     # Secure client prefix
    ]
    
    # Marketer-side URLs (require marketer role)
    MARKETER_URLS = [
        '/marketer-dashboard',
        '/marketer-profile',
        '/marketer/my-companies/', # Covers /marketer/my-companies/8/
        '/marketer/chat/',         # Covers /marketer/chat/
        '/client-records',
        '/m/',                     # Secure marketer prefix
    ]
    
    # Admin-side URLs (require admin role)
    ADMIN_URLS = [
        '/chat-admin/',            # Covers /chat-admin/chat/1/, /chat-admin/marketer-chat/1/
        '/admin-dashboard',
        '/admin_dashboard',
        '/admin_home',
        '/company-profile',        # Covers all company profile operations
        '/marketer-list',
        '/client/',                # Admin client management (not client self-service)
        '/admin-marketer/',        # Admin marketer profile view
        '/add-estate',
        '/add-plotsize',
        '/add-plotnumber',
        '/delete-plotsize/',
        '/delete-plotnumber/',
        '/plot-allocation',
        '/view-estate',
        '/allocated-plot/',
        '/allocate-units/',
        '/estate-plots/',
        '/delete-estate/',
        '/edit-estate/',
        '/add-floor-plan',
        '/add-prototypes/',
        '/add-estate-layout/',
        '/add-estate-map/',
        '/add-progress-status/',
        '/user-registration',
        '/send-announcement',
        '/marketer-performance/',
        '/sales-volume-metrics/',
        '/management-dashboard',
        '/download-allocations/',
        '/download-estate-pdf/',
    ]
    
    # Tenant-scoped admin URLs (dynamic company slug)
    # Pattern: /<company_slug>/dashboard/, /<company_slug>/management/
    TENANT_ADMIN_PATTERNS = [
        '/dashboard/',
        '/management/',
        '/users/',
        '/settings/',
    ]
    
    # Shared authenticated URLs (require login but any role)
    AUTHENTICATED_URLS = [
        '/notifications/',         # Covers /notifications/, /notifications/46/, /notifications/46/mark-read/
        '/message/',               # Message detail
        '/receipt/',               # Receipt access
        '/payment-history/',
        '/transaction/',           # Transaction details
    ]
    
    def process_request(self, request):
        """Process incoming request for security."""
        path = request.path
        
        # Skip exempt URLs
        if any(path.startswith(exempt) for exempt in self.EXEMPT_URLS):
            return None
        
        # Record request start time for performance monitoring
        request._security_start_time = time.time()
        
        # 1. Basic security validation
        is_valid, error_msg = SecurityValidator.validate_request(request)
        if not is_valid:
            _log_security_event(request, 'blocked_request', error_msg)
            logger.warning(f"Blocked request: {error_msg} | Path: {path}")
            return HttpResponseForbidden("Request blocked for security reasons.")
        
        # 2. Rate limiting for sensitive URLs
        if any(path.startswith(url) for url in self.SENSITIVE_URLS):
            is_limited, wait_time = RateLimiter.is_rate_limited(request, 'sensitive')
            if is_limited:
                _log_security_event(request, 'rate_limited', f"Sensitive URL rate limited: {path}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'rate_limited',
                        'message': f'Too many requests. Please wait {wait_time} seconds.',
                        'retry_after': wait_time
                    }, status=429)
                messages.error(request, f"Too many requests. Please wait {wait_time} seconds.")
                return redirect('login')
        
        # 3. General rate limiting
        is_limited, wait_time = RateLimiter.is_rate_limited(request, 'page')
        if is_limited:
            _log_security_event(request, 'rate_limited', f"Page rate limited: {path}")
            return HttpResponseForbidden(f"Too many requests. Please wait {wait_time} seconds.")
        
        # 4. Session integrity check for authenticated users
        if request.user.is_authenticated:
            if not SecurityValidator.validate_session_integrity(request):
                _log_security_event(request, 'session_hijack_attempt', 'User agent changed mid-session')
                logout(request)
                messages.error(request, "Security alert: Your session has been terminated for security reasons.")
                return redirect('login')
            
            # Track user activity
            _track_user_activity(request)
            
            # 5. Role-based URL protection
            user_role = getattr(request.user, 'role', None)
            
            # Client URL protection
            if any(path.startswith(url) for url in self.CLIENT_URLS):
                if user_role != 'client':
                    _log_security_event(request, 'unauthorized_access', f"Non-client accessing client URL: {path}")
                    messages.error(request, "Access denied. This page is for clients only.")
                    return redirect('login')
            
            # Marketer URL protection
            if any(path.startswith(url) for url in self.MARKETER_URLS):
                if user_role != 'marketer':
                    _log_security_event(request, 'unauthorized_access', f"Non-marketer accessing marketer URL: {path}")
                    messages.error(request, "Access denied. This page is for marketers only.")
                    return redirect('login')
            
            # Admin URL protection
            if any(path.startswith(url) for url in self.ADMIN_URLS):
                if user_role != 'admin':
                    _log_security_event(request, 'unauthorized_access', f"Non-admin accessing admin URL: {path}")
                    messages.error(request, "Access denied. This page is for administrators only.")
                    return redirect('login')
            
            # Tenant-scoped admin URL protection (/<company_slug>/dashboard/, etc.)
            # Check if path matches pattern like /company-slug/dashboard/
            path_parts = path.strip('/').split('/')
            if len(path_parts) >= 2:
                potential_page = '/' + path_parts[1] + '/'
                if potential_page in self.TENANT_ADMIN_PATTERNS:
                    if user_role != 'admin':
                        _log_security_event(request, 'unauthorized_access', f"Non-admin accessing tenant admin URL: {path}")
                        messages.error(request, "Access denied. This page is for administrators only.")
                        return redirect('login')
        
        # 6. Authenticated URL protection (any logged-in user)
        else:
            # For URLs that require authentication (any role)
            if any(path.startswith(url) for url in self.AUTHENTICATED_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing protected URL: {path}")
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to client URLs
            if any(path.startswith(url) for url in self.CLIENT_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing client URL: {path}")
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to marketer URLs
            if any(path.startswith(url) for url in self.MARKETER_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing marketer URL: {path}")
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to admin URLs
            if any(path.startswith(url) for url in self.ADMIN_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing admin URL: {path}")
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to tenant-scoped admin URLs
            path_parts = path.strip('/').split('/')
            if len(path_parts) >= 2:
                potential_page = '/' + path_parts[1] + '/'
                if potential_page in self.TENANT_ADMIN_PATTERNS:
                    _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing tenant admin URL: {path}")
                    messages.error(request, "Please login to access this page.")
                    return redirect('login')
        
        return None
    
    def process_response(self, request, response):
        """Add security headers and monitor performance."""
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy (adjust based on your needs)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "img-src 'self' data: https: blob:",
            "connect-src 'self'",
            "frame-ancestors 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # Performance monitoring
        if hasattr(request, '_security_start_time'):
            duration = time.time() - request._security_start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
            
            # Log slow requests
            if duration > 2.0:
                logger.warning(f"Slow request: {request.path} took {duration:.3f}s")
        
        return response


class PageLoadOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware to optimize page load times.
    
    Adds appropriate cache headers for different content types.
    """
    
    def process_response(self, request, response):
        """Add cache headers for optimization."""
        path = request.path
        
        # Static files - long cache
        if path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=86400, immutable'
            return response
        
        # Media files - moderate cache
        if path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=3600'
            return response
        
        # API responses
        if '/api/' in path:
            response['Cache-Control'] = 'private, no-cache, must-revalidate'
            return response
        
        # Dynamic pages - no cache for security
        response['Cache-Control'] = 'private, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced session security middleware.
    
    Features:
    - 30-minute inactivity timeout
    - 24-hour maximum session age
    - IP change monitoring
    - Security event logging
    """
    
    # Session timeout in seconds (30 minutes of inactivity)
    SESSION_TIMEOUT = 1800
    
    # Maximum session lifetime (24 hours)
    MAX_SESSION_AGE = 86400
    
    def process_request(self, request):
        """Check session security."""
        if not request.user.is_authenticated:
            return None
        
        now = time.time()
        
        # Check last activity
        last_activity = request.session.get('_security_last_activity')
        if last_activity:
            if now - last_activity > self.SESSION_TIMEOUT:
                _log_security_event(request, 'session_timeout', 'Session expired due to inactivity')
                logout(request)
                messages.info(request, "Your session has expired due to inactivity. Please login again.")
                return redirect('login')
        
        # Check session creation time
        session_created = request.session.get('_security_session_created')
        if session_created:
            if now - session_created > self.MAX_SESSION_AGE:
                _log_security_event(request, 'session_expired', 'Session exceeded maximum age')
                logout(request)
                messages.info(request, "Your session has expired. Please login again.")
                return redirect('login')
        else:
            # Set session creation time
            request.session['_security_session_created'] = now
        
        # Update last activity
        request.session['_security_last_activity'] = now
        
        # Store user IP for monitoring
        ip = RateLimiter.get_client_ip(request)
        session_ip = request.session.get('_security_ip')
        if session_ip and session_ip != ip:
            # IP changed - could be mobile network or VPN, or session hijacking
            # Log but don't block immediately
            _log_security_event(request, 'ip_change', f"IP changed from {session_ip} to {ip}")
        request.session['_security_ip'] = ip
        
        return None


class AntiCSRFEnhancementMiddleware(MiddlewareMixin):
    """
    Enhanced CSRF protection beyond Django's built-in protection.
    
    Features:
    - Origin/Referer verification for AJAX requests
    - Additional header checks
    - Security event logging
    """
    
    def process_request(self, request):
        """Additional CSRF checks."""
        if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            return None
        
        # Check Origin/Referer for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            origin = request.META.get('HTTP_ORIGIN', '')
            referer = request.META.get('HTTP_REFERER', '')
            host = request.get_host()
            
            # Verify origin/referer matches host
            if origin:
                from urllib.parse import urlparse
                origin_host = urlparse(origin).netloc
                if origin_host and origin_host != host:
                    _log_security_event(request, 'csrf_origin_mismatch', f"Origin: {origin}, Host: {host}")
                    return HttpResponseForbidden("CSRF verification failed.")
            elif referer:
                from urllib.parse import urlparse
                referer_host = urlparse(referer).netloc
                if referer_host and referer_host != host:
                    _log_security_event(request, 'csrf_referer_mismatch', f"Referer: {referer}, Host: {host}")
                    return HttpResponseForbidden("CSRF verification failed.")
        
        return None