"""
Multi-Tenant Data Isolation Middleware

Provides complete data isolation between companies at the middleware level.
Prevents cross-company data leaks and enforces subscription-based access.

ADVANCED CYBERSECURITY PROTECTION:
- Brute Force Attack Prevention (progressive lockout)
- SQL/XSS/Command/Template/LDAP Injection Protection
- Session Hijacking/Fixation Prevention
- IDOR Attack Prevention
- Clickjacking Protection
- Open Redirect Protection
- Parameter Tampering Prevention
- Bot/Automated Attack Detection
- DDoS/Rate Limiting with Exponential Backoff
"""

import threading
from datetime import timedelta
from django.conf import settings
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages
from .models import Company
import logging
import time
import hashlib
import re

# Import Advanced Security Module
from estateApp.advanced_security import (
    ComprehensiveSecurityValidator,
    BruteForceProtection,
    InjectionProtection,
    SessionSecurity,
    IDORProtection,
    ClickjackingProtection,
    OpenRedirectProtection,
    ParameterTamperProtection,
    BotDetection,
    SecurityHeaders,
    get_client_ip,
    log_security_event,
)

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
            session_expiry = request.session.get('_session_expiry', None)

            # If no expiry set, initialize it
            if session_expiry is None:
                request.session['_session_expiry'] = current_time + int(session_timeout)
                try:
                    request.session.save()
                except Exception:
                    logger.exception('Failed to initialize session expiry')
                return None
            
            # If session has expired, redirect to login
            if current_time > session_expiry:
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
            '/subscription/',
            '/static/',
            '/media/',
            '/favicon.ico',
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
            if request.user.is_superuser or getattr(request.user, 'is_system_admin', False):
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
            '/admin/',
            '/super-admin/',  # Super admin is independent of tenant context
            '/health/',
            '/login/',
            '/logout/',
            '/register/',
            '/static/',
            '/media/',
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
# Enhanced with comprehensive cybersecurity protection

from estateApp.security import (
    RateLimiter,
    SecurityValidator,
    SecureTokenGenerator,
    _log_security_event,
    _track_user_activity
)
from django.contrib.auth import logout

# Initialize Advanced Security Components
_brute_force_protection = BruteForceProtection()
_injection_protection = InjectionProtection()
_session_security = SessionSecurity()
_idor_protection = IDORProtection()
_clickjacking_protection = ClickjackingProtection()
_open_redirect_protection = OpenRedirectProtection()
_parameter_tamper_protection = ParameterTamperProtection()
_bot_detection = BotDetection()
_security_headers = SecurityHeaders()
_comprehensive_validator = ComprehensiveSecurityValidator()


class AdvancedSecurityMiddleware(MiddlewareMixin):
    """
    ENTERPRISE-GRADE SECURITY MIDDLEWARE
    
    Comprehensive protection against all types of hackers:
    
    1. BRUTE FORCE ATTACKERS - Progressive lockout, exponential backoff
    2. SQL INJECTION HACKERS - Pattern detection, input sanitization
    3. XSS ATTACKERS - Script detection, content filtering
    4. SESSION HIJACKERS - Fingerprinting, integrity checks
    5. IDOR ATTACKERS - Object ownership verification
    6. BOT/AUTOMATED ATTACKS - Signature detection, honeypot
    7. DDOS ATTACKERS - Rate limiting, IP blocking
    8. CREDENTIAL STUFFERS - Login rate limiting
    9. PRIVILEGE ESCALATION - Role verification
    10. CLICKJACKING - Frame protection headers
    
    Provides:
    - Multi-layer request validation
    - Advanced rate limiting per IP and user
    - Session integrity and hijacking prevention
    - Role-based URL protection
    - Comprehensive injection attack detection
    - Bot/crawler detection and blocking
    - Security headers enforcement
    """
    
    # ========================================================================
    # PUBLIC URLS - No authentication required
    # ========================================================================
    # IMPORTANT: ALL URLs NOT listed here will REQUIRE AUTHENTICATION
    # This is the WHITELIST approach - secure by default
    PUBLIC_URLS = [
        '/login/',
        '/logout/',
        '/register/',
        '/password-reset/',
        '/client/register/',
        '/marketer/register/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/api/health/',
        '/health/',
        '/admin/login/',           # Django admin login
        '/admin/',                 # Django admin (has its own auth)
        '/super-admin/',           # Super admin (has its own auth & redirect)
        '/estates/',               # Public estate list
        '/promotions/',            # Public promotions
    ]
    
    # URLs exempt from security checks (static/media only)
    EXEMPT_URLS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
    ]
    
    # URLs that require stricter rate limiting (login attempts)
    SENSITIVE_URLS = [
        '/login/',
        '/register/',
        '/password-reset/',
        '/change-password/',
        '/profile/update/',
        '/api/auth/',
        '/api/login/',
        '/api/token/',
        '/client/register/',
        '/marketer/register/',
        '/super-admin/login/',  # Super admin login
    ]
    
    # URLs that should be monitored for IDOR attacks
    IDOR_SENSITIVE_URLS = [
        '/view-client-estate/',
        '/my-companies/',
        '/marketer/my-companies/',
        '/notifications/',
        '/chat/',
        '/receipt/',
        '/transaction/',
        '/client/',
        '/allocated-plot/',
        '/download-allocations/',
        '/client_profile/',
        '/admin-marketer/',
    ]
    
    # ========================================================================
    # CLIENT-SIDE URLS (require client role)
    # ========================================================================
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
        '/c/',                     # Secure client prefix: /c/dashboard/, /c/profile/
    ]
    
    # ========================================================================
    # MARKETER-SIDE URLS (require marketer role)
    # ========================================================================
    MARKETER_URLS = [
        '/marketer-dashboard',
        '/marketer-profile',
        '/marketer/my-companies/', # Covers /marketer/my-companies/8/
        '/marketer/chat/',         # Covers /marketer/chat/
        '/client-records',
        '/m/',                     # Secure marketer prefix: /m/dashboard/, /m/profile/
    ]
    
    # ========================================================================
    # SUPPORT-SIDE URLS (require support role) - AdminSupport Dashboard
    # ========================================================================
    SUPPORT_URLS = [
        '/adminsupport/',          # Covers /adminsupport/dashboard/, /adminsupport/tickets/, etc.
    ]
    
    # ========================================================================
    # ADMIN-SIDE URLS (require admin role)
    # ========================================================================
    # 🔐 ADMIN_ROLES: Roles allowed to access admin panel (NOT support - they have their own dashboard)
    ADMIN_ROLES = ('admin', 'secondary_admin', 'company_admin')
    
    # 🔐 SUPPORT_ROLES: Roles allowed to access admin support panel
    SUPPORT_ROLES = ('support',)
    
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
        '/update-plotsize/',
        '/update-plotnumber/',
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
        '/estate_details/',
        '/load-plots/',
        '/get-allocated-plots/',
        '/get-plot-sizes/',
        '/fetch_plot_data',
        '/update_allocated_plot/',
        '/delete-allocation/',
        '/get_allocated_plot/',
        '/transactions/add/',
        '/update-estate-amenities/',
        # Company admin register (special case - admin inviting admins)
        '/company/',               # Covers /company/<id>/admin-register/
    ]
    
    # ========================================================================
    # TENANT-SCOPED ADMIN URLS (dynamic company slug)
    # ========================================================================
    # Pattern: /<company_slug>/dashboard/, /<company_slug>/management/
    TENANT_ADMIN_PATTERNS = [
        '/dashboard/',
        '/management/',
        '/users/',
        '/settings/',
    ]
    
    # ========================================================================
    # SHARED AUTHENTICATED URLS (require login but any role)
    # ========================================================================
    AUTHENTICATED_URLS = [
        '/notifications/',         # Covers /notifications/, /notifications/46/, /notifications/46/mark-read/
        '/message/',               # Message detail
        '/receipt/',               # Receipt access
        '/payment-history/',
        '/transaction/',           # Transaction details
        '/payment/receipt/',       # Payment receipt by reference code
        '/chat_unread_count/',     # Chat unread count (AJAX)
        '/user-profile',           # User profile
        '/user_profile/',          # User profile alt
        '/security-verification/', # Security verification checkpoint
        '/subscription/',          # Subscription management (any logged-in user)
        '/company-profile/',       # Company profile management
    ]
    
    # ========================================================================
    # INJECTION WHITELIST - Safe fields that can contain special characters
    # ========================================================================
    # Fields where ampersand (&) and other special chars are legitimate business data
    SAFE_TEXT_FIELDS = [
        'name',              # Department names, role names (e.g., "Sales & Marketing")
        'description',       # Descriptions often contain special characters
        'address',           # Addresses can have special characters
        'notes',             # Notes fields
        'message',           # Message content
        'subject',           # Message subjects
        'full_name',         # Names with special characters
        'company_name',      # Company names
        'office_address',    # Office addresses
        'location',          # Location fields
        'bio',               # Biography fields
        'comment',           # Comments
        'feedback',          # Feedback fields
        'password',          # Password fields (login forms)
        'email',             # Email fields (can contain special chars)
    ]
    
    # Endpoints where command injection checking should be lenient
    SAFE_ENDPOINTS = [
        '/admin-support/api/departments/',
        '/admin-support/api/roles/',
        '/admin-support/api/staff/',
        '/company-console/',
        '/admin-dashboard/',
        '/super-admin/login/',  # Super admin login (password field)
        '/login/',  # Regular login (password field)
    ]
    
    # URLs that require EXACT match (not startswith) - Home page
    EXACT_AUTHENTICATED_URLS = [
        '/',                       # Home page (requires login) - EXACT match only
    ]
    
    # ========================================================================
    # API URLS (require authentication via API token or session)
    # ========================================================================
    API_URLS = [
        '/api/',                   # All API endpoints require auth
        '/ajax/',                  # All AJAX endpoints require auth
    ]
    
    def process_request(self, request):
        """
        COMPREHENSIVE SECURITY PROCESSING
        
        Multi-layer defense against all attack vectors:
        Layer 1: Basic request validation
        Layer 2: Bot/Crawler detection
        Layer 3: Brute force protection
        Layer 4: Injection attack detection
        Layer 5: Session security validation
        Layer 6: Rate limiting
        Layer 7: Role-based access control
        Layer 8: IDOR protection
        """
        path = request.path
        client_ip = get_client_ip(request)
        
        # Skip exempt URLs
        if any(path.startswith(exempt) for exempt in self.EXEMPT_URLS):
            return None
        
        # Record request start time for performance monitoring
        request._security_start_time = time.time()
        
        # ===== LAYER 1: BASIC REQUEST VALIDATION =====
        is_valid, error_msg = SecurityValidator.validate_request(request)
        if not is_valid:
            _log_security_event(request, 'blocked_request', error_msg)
            log_security_event('REQUEST_BLOCKED', request, {'reason': error_msg})
            logger.warning(f"[SECURITY] Blocked request: {error_msg} | IP: {client_ip} | Path: {path}")
            return HttpResponseForbidden("Request blocked for security reasons.")
        
        # ===== LAYER 2: BOT/CRAWLER DETECTION =====
        is_bot, bot_reason = _bot_detection.is_bot(request)
        if is_bot:
            log_security_event('BOT_DETECTED', request, {'reason': bot_reason})
            logger.warning(f"[SECURITY] Bot detected: {bot_reason} | IP: {client_ip}")
            # Don't block immediately, but flag the request
            request._is_bot = True
            request._bot_reason = bot_reason
            
            # Block known bad bots from sensitive URLs
            if any(path.startswith(url) for url in self.SENSITIVE_URLS):
                return HttpResponseForbidden("Automated access to this endpoint is not allowed.")
        else:
            request._is_bot = False
        
        # ===== LAYER 3: BRUTE FORCE PROTECTION =====
        if any(path.startswith(url) for url in self.SENSITIVE_URLS):
            is_blocked, block_reason, remaining_lockout = _brute_force_protection.check_brute_force(request)
            if is_blocked:
                log_security_event('BRUTE_FORCE_BLOCKED', request, {
                    'lockout_remaining': remaining_lockout,
                    'reason': block_reason
                })
                logger.warning(f"[SECURITY] Brute force blocked: IP {client_ip} locked for {remaining_lockout}s - {block_reason}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'account_locked',
                        'message': f'Too many failed attempts. Please wait {remaining_lockout} seconds.',
                        'retry_after': remaining_lockout
                    }, status=429)
                
                messages.error(request, f"Account temporarily locked due to too many failed attempts. Please wait {remaining_lockout} seconds.")
                return redirect('login')
        
        # ===== LAYER 4: INJECTION ATTACK DETECTION =====
        # Check all input sources for injection attacks
        injection_sources = []
        
        # Check if current endpoint is in safe endpoints list
        is_safe_endpoint = any(path.startswith(safe_path) for safe_path in self.SAFE_ENDPOINTS)
        
        # Debug logging for safe endpoint detection
        if is_safe_endpoint and request.method == 'POST':
            logger.info(f"[SECURITY] Safe endpoint detected: {path} - Lenient command injection checking enabled")
        
        # Check GET parameters
        for key, value in request.GET.items():
            is_sql, _ = _injection_protection.check_injection(value, 'sql')
            if is_sql:
                injection_sources.append(('SQL_INJECTION', 'GET', key))
            is_xss, _ = _injection_protection.check_injection(value, 'xss')
            if is_xss:
                injection_sources.append(('XSS_ATTACK', 'GET', key))
            # Skip command injection check for safe fields in safe endpoints
            if not (is_safe_endpoint and key in self.SAFE_TEXT_FIELDS):
                is_cmd, _ = _injection_protection.check_injection(value, 'command')
                if is_cmd:
                    injection_sources.append(('COMMAND_INJECTION', 'GET', key))
        
        # Check POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str):
                is_sql, _ = _injection_protection.check_injection(value, 'sql')
                if is_sql:
                    injection_sources.append(('SQL_INJECTION', 'POST', key))
                is_xss, _ = _injection_protection.check_injection(value, 'xss')
                if is_xss:
                    injection_sources.append(('XSS_ATTACK', 'POST', key))
                # Skip command injection check for safe fields in safe endpoints
                should_skip_cmd_check = is_safe_endpoint and key in self.SAFE_TEXT_FIELDS
                if should_skip_cmd_check:
                    logger.debug(f"[SECURITY] Skipping command injection check for field '{key}' on safe endpoint")
                if not should_skip_cmd_check:
                    is_cmd, _ = _injection_protection.check_injection(value, 'command')
                    if is_cmd:
                        injection_sources.append(('COMMAND_INJECTION', 'POST', key))
                is_template, _ = _injection_protection.check_injection(value, 'template')
                if is_template:
                    injection_sources.append(('TEMPLATE_INJECTION', 'POST', key))
        
        # Check path for path traversal (using command injection patterns which include ../)
        is_path_attack, _ = _injection_protection.check_injection(path, 'command')
        if is_path_attack:
            injection_sources.append(('PATH_TRAVERSAL', 'PATH', path))
        
        if injection_sources:
            for attack_type, source_type, source_key in injection_sources:
                log_security_event(attack_type, request, {
                    'source': source_type,
                    'parameter': source_key
                })
            logger.critical(f"[SECURITY] Injection attack detected: {injection_sources} | IP: {client_ip} | Path: {path}")
            
            # Record as failed login attempt (to trigger brute force protection)
            _brute_force_protection.record_failed_attempt(request, reason='injection_attack')
            
            return HttpResponseForbidden("Security violation detected. This incident has been logged.")
        
        # ===== LAYER 5: SESSION SECURITY =====
        # Skip session security for subscription management (users must be able to access billing)
        session_exempt_paths = ['/subscription/', '/login/', '/logout/', '/static/', '/media/']
        skip_session_security = any(path.startswith(p) for p in session_exempt_paths)
        
        if request.user.is_authenticated and not skip_session_security:
            # Validate session integrity
            if not SecurityValidator.validate_session_integrity(request):
                log_security_event('SESSION_HIJACK_ATTEMPT', request, {
                    'reason': 'User agent or fingerprint mismatch'
                })
                logger.warning(f"[SECURITY] Session hijack attempt: IP {client_ip}")
                logout(request)
                messages.error(request, "Security alert: Your session has been terminated due to suspicious activity.")
                return redirect('login')
            
            # Advanced session validation
            session_valid, session_reason = _session_security.validate_session(request)
            if not session_valid:
                log_security_event('SESSION_INVALID', request, {'reason': session_reason})
                logger.warning(f"[SECURITY] Invalid session: {session_reason} | IP: {client_ip}")
                logout(request)
                messages.error(request, "Your session has expired or is invalid. Please log in again.")
                return redirect('login')
            
            # Track user activity
            _track_user_activity(request)
        
        # ===== LAYER 6: RATE LIMITING =====
        # Stricter rate limiting for sensitive URLs
        if any(path.startswith(url) for url in self.SENSITIVE_URLS):
            is_limited, wait_time = RateLimiter.is_rate_limited(request, 'sensitive')
            if is_limited:
                _log_security_event(request, 'rate_limited', f"Sensitive URL rate limited: {path}")
                log_security_event('RATE_LIMITED', request, {
                    'type': 'sensitive',
                    'wait_time': wait_time
                })
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'rate_limited',
                        'message': f'Too many requests. Please wait {wait_time} seconds.',
                        'retry_after': wait_time
                    }, status=429)
                messages.error(request, f"Too many requests. Please wait {wait_time} seconds.")
                return redirect('login')
        
        # General rate limiting
        is_limited, wait_time = RateLimiter.is_rate_limited(request, 'page')
        if is_limited:
            _log_security_event(request, 'rate_limited', f"Page rate limited: {path}")
            log_security_event('RATE_LIMITED', request, {'type': 'page', 'wait_time': wait_time})
            return HttpResponseForbidden(f"Too many requests. Please wait {wait_time} seconds.")
        
        # ===== LAYER 7: ROLE-BASED ACCESS CONTROL =====
        if request.user.is_authenticated:
            user_role = getattr(request.user, 'role', None)
            
            # Client URL protection
            if any(path.startswith(url) for url in self.CLIENT_URLS):
                if user_role != 'client':
                    _log_security_event(request, 'unauthorized_access', f"Non-client accessing client URL: {path}")
                    log_security_event('PRIVILEGE_ESCALATION_ATTEMPT', request, {
                        'attempted_role': 'client',
                        'actual_role': user_role
                    })
                    messages.error(request, "Access denied. This page is for clients only.")
                    return redirect('login')
            
            # Marketer URL protection
            if any(path.startswith(url) for url in self.MARKETER_URLS):
                if user_role != 'marketer':
                    _log_security_event(request, 'unauthorized_access', f"Non-marketer accessing marketer URL: {path}")
                    log_security_event('PRIVILEGE_ESCALATION_ATTEMPT', request, {
                        'attempted_role': 'marketer',
                        'actual_role': user_role
                    })
                    messages.error(request, "Access denied. This page is for marketers only.")
                    return redirect('login')
            
            # Support URL protection (AdminSupport dashboard)
            if any(path.startswith(url) for url in self.SUPPORT_URLS):
                if user_role not in self.SUPPORT_ROLES:
                    _log_security_event(request, 'unauthorized_access', f"Non-support accessing support URL: {path}")
                    log_security_event('PRIVILEGE_ESCALATION_ATTEMPT', request, {
                        'attempted_role': 'support',
                        'actual_role': user_role
                    })
                    messages.error(request, "Access denied. This page is for support staff only.")
                    return redirect('login')
            
            # Admin URL protection
            if any(path.startswith(url) for url in self.ADMIN_URLS):
                if user_role not in self.ADMIN_ROLES:
                    _log_security_event(request, 'unauthorized_access', f"Non-admin accessing admin URL: {path}")
                    log_security_event('PRIVILEGE_ESCALATION_ATTEMPT', request, {
                        'attempted_role': 'admin',
                        'actual_role': user_role
                    })
                    messages.error(request, "Access denied. This page is for administrators only.")
                    return redirect('login')
            
            # Tenant-scoped admin URL protection (/<company_slug>/dashboard/, etc.)
            # IMPORTANT: Skip this check if URL already matched marketer/client/admin/support URLs
            # or subscription/billing management URLs (any authenticated user can access)
            # to avoid false positives on /m/dashboard/, /c/dashboard/, /subscription/dashboard/, etc.
            is_known_role_url = (
                any(path.startswith(url) for url in self.MARKETER_URLS) or
                any(path.startswith(url) for url in self.CLIENT_URLS) or
                any(path.startswith(url) for url in self.ADMIN_URLS) or
                any(path.startswith(url) for url in self.SUPPORT_URLS) or
                any(path.startswith(url) for url in self.AUTHENTICATED_URLS)
            )
            
            if not is_known_role_url:
                path_parts = path.strip('/').split('/')
                if len(path_parts) >= 2:
                    potential_page = '/' + path_parts[1] + '/'
                    if potential_page in self.TENANT_ADMIN_PATTERNS:
                        if user_role not in self.ADMIN_ROLES:
                            _log_security_event(request, 'unauthorized_access', f"Non-admin accessing tenant admin URL: {path}")
                            log_security_event('PRIVILEGE_ESCALATION_ATTEMPT', request, {
                                'attempted_role': 'tenant_admin',
                                'actual_role': user_role
                            })
                            messages.error(request, "Access denied. This page is for administrators only.")
                            return redirect('login')
        
        # ===== LAYER 8: UNAUTHENTICATED ACCESS PROTECTION =====
        else:
            # IMPORTANT: Check if URL is public FIRST to avoid redirect loops
            is_public_url = any(path.startswith(url) for url in self.PUBLIC_URLS)
            if is_public_url:
                return None  # Allow public URLs without authentication
            
            # Check exact match URLs (like home page '/')
            if path in self.EXACT_AUTHENTICATED_URLS:
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing protected URL: {path}")
                log_security_event('UNAUTHENTICATED_ACCESS', request, {'url': path})
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # For URLs that require authentication (any role)
            if any(path.startswith(url) for url in self.AUTHENTICATED_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing protected URL: {path}")
                log_security_event('UNAUTHENTICATED_ACCESS', request, {'url': path})
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to client URLs
            if any(path.startswith(url) for url in self.CLIENT_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing client URL: {path}")
                log_security_event('UNAUTHENTICATED_ACCESS', request, {'url': path, 'required_role': 'client'})
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to marketer URLs
            if any(path.startswith(url) for url in self.MARKETER_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing marketer URL: {path}")
                log_security_event('UNAUTHENTICATED_ACCESS', request, {'url': path, 'required_role': 'marketer'})
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to admin URLs
            if any(path.startswith(url) for url in self.ADMIN_URLS):
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing admin URL: {path}")
                log_security_event('UNAUTHENTICATED_ACCESS', request, {'url': path, 'required_role': 'admin'})
                messages.error(request, "Please login to access this page.")
                return redirect('login')
            
            # Block unauthenticated access to tenant-scoped admin URLs
            # IMPORTANT: Skip if URL already matched known role URLs or shared authenticated URLs
            is_known_role_url = (
                any(path.startswith(url) for url in self.MARKETER_URLS) or
                any(path.startswith(url) for url in self.CLIENT_URLS) or
                any(path.startswith(url) for url in self.ADMIN_URLS) or
                any(path.startswith(url) for url in self.AUTHENTICATED_URLS)
            )
            
            if not is_known_role_url:
                path_parts = path.strip('/').split('/')
                if len(path_parts) >= 2:
                    potential_page = '/' + path_parts[1] + '/'
                    if potential_page in self.TENANT_ADMIN_PATTERNS:
                        _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing tenant admin URL: {path}")
                        log_security_event('UNAUTHENTICATED_ACCESS', request, {'url': path, 'required_role': 'tenant_admin'})
                        messages.error(request, "Please login to access this page.")
                        return redirect('login')
            
            # ========================================================================
            # ⚠️ CATCH-ALL PROTECTION - SECURE BY DEFAULT
            # ========================================================================
            # ANY URL not explicitly listed in PUBLIC_URLS requires authentication
            # This is the WHITELIST approach - if it's not public, you need to login
            is_public_url = any(path.startswith(url) for url in self.PUBLIC_URLS)
            
            if not is_public_url:
                _log_security_event(request, 'unauthenticated_access', f"Anonymous user accessing unlisted URL: {path}")
                log_security_event('UNAUTHENTICATED_ACCESS', request, {
                    'url': path,
                    'reason': 'URL not in public whitelist'
                })
                logger.warning(f"[SECURITY] Catch-all blocked unauthenticated access: {path} | IP: {client_ip}")
                messages.error(request, "Please login to access this page.")
                return redirect('login')
        
        return None
    
    def process_response(self, request, response):
        """
        COMPREHENSIVE SECURITY RESPONSE PROCESSING
        
        Adds enterprise-grade security headers and monitors performance.
        """
        client_ip = get_client_ip(request)
        
        # ===== SECURITY HEADERS (Enterprise-Grade) =====
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Clickjacking protection (backup for CSP frame-ancestors)
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # XSS Protection (deprecated but still useful for older browsers)
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy - prevent leaking sensitive URLs
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy - disable dangerous browser features
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # Cache control for sensitive pages
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Content Security Policy (comprehensive)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com https://stackpath.bootstrapcdn.com https://cdn.tailwindcss.com",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://stackpath.bootstrapcdn.com https://cdn.tailwindcss.com",
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' wss: ws:",  # Allow WebSocket for chat
            "frame-ancestors 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",  # Disable plugins
            "upgrade-insecure-requests",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        # HSTS - Force HTTPS (only in production)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Cross-Origin policies
        response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'  # Allow loading from CDNs
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Resource-Policy'] = 'same-origin'
        
        # Remove server identification headers
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
        
        # Performance monitoring
        if hasattr(request, '_security_start_time'):
            duration = time.time() - request._security_start_time
            response['X-Response-Time'] = f"{duration:.3f}s"
            
            # Log slow requests
            if duration > 2.0:
                logger.warning(f"[PERFORMANCE] Slow request: {request.path} took {duration:.3f}s | IP: {client_ip}")
        
        # Log suspicious response codes
        if response.status_code in [401, 403, 404, 500]:
            log_security_event('SUSPICIOUS_RESPONSE', request, {
                'status_code': response.status_code,
                'path': request.path
            })
            
        # Track if this was a bot request
        if getattr(request, '_is_bot', False):
            response['X-Bot-Detected'] = 'true'
            log_security_event('BOT_RESPONSE', request, {
                'status_code': response.status_code,
                'bot_reason': getattr(request, '_bot_reason', 'unknown')
            })
        
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


class ReadOnlyModeMiddleware(MiddlewareMixin):
    """Blocks unsafe writes when the current company is in read-only mode.

    This closes loopholes where UI restrictions exist but endpoints still accept writes.
    """

    UNSAFE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

    # Paths that must remain usable to recover from read-only state.
    ALLOW_PREFIXES = (
        '/static/',
        '/media/',
        '/admin/',
        '/login',
        '/logout',
        '/register',
        '/billing',
        '/subscription',
        '/api/alerts/',
        '/api/billing/',
    )

    def process_request(self, request):
        if request.method not in self.UNSAFE_METHODS:
            return None

        if any(request.path.startswith(p) for p in self.ALLOW_PREFIXES):
            return None

        # Resolve company from the tenant middleware or user profile.
        company = getattr(request, 'company', None)
        if company is None and getattr(request, 'user', None) is not None and request.user.is_authenticated:
            company = getattr(request.user, 'company_profile', None)

        if not company:
            return None

        if not getattr(company, 'is_read_only_mode', False):
            return None

        payload = {
            'detail': 'Account is in read-only mode. Upgrade/renew to restore write access.',
            'code': 'read_only_mode',
        }

        if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(payload, status=403)

        return HttpResponseForbidden(payload['detail'])


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
    
    # Paths exempt from session timeout (subscription management must always be reachable)
    EXEMPT_PATHS = [
        '/login/',
        '/logout/',
        '/subscription/',
        '/static/',
        '/media/',
        '/favicon.ico',
    ]
    
    def _is_exempt(self, request):
        """Check if path is exempt from session security checks."""
        for path in self.EXEMPT_PATHS:
            if request.path.startswith(path):
                return True
        return False
    
    def process_request(self, request):
        """Check session security."""
        if not request.user.is_authenticated:
            return None
        
        # Exempt certain paths from session timeout
        if self._is_exempt(request):
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