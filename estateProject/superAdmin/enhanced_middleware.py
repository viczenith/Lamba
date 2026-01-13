"""
ENHANCED PRODUCTION MULTI-TENANT MIDDLEWARE
Implements query interception and automatic isolation
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
from estateApp.models import Company
from estateApp.isolation import set_current_tenant, clear_tenant_context, get_current_tenant
import logging

logger = logging.getLogger(__name__)


class EnhancedTenantIsolationMiddleware(MiddlewareMixin):
    """
    Enterprise-grade multi-tenant isolation middleware
    
    Features:
    1. Automatic tenant context detection
    2. Request isolation enforcement  
    3. Cross-tenant access prevention
    4. Audit logging of access attempts
    """
    
    # Paths that don't require tenant context
    EXEMPT_PATHS = [
        '/admin/',
        '/super-admin/',
        '/api/auth/',
        '/static/',
        '/media/',
        '/login/',
        '/logout/',
        '/register/',
        '/client/register/',
        '/marketer/register/',
        '/health/',
        '/api-auth/',
        # Dashboard paths for clients and marketers (they work across companies)
        '/client-dashboard',
        '/marketer-dashboard',
        '/client-dashboard-cross-company/',
        # Subscription/billing management (accessible without strict tenant context)
        '/subscription/',
        '/company-profile/',
    ]
    
    def should_exempt(self, path):
        """Check if path should be exempt from tenant checking"""
        # Check exact path matches
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return True
        
        # Check for tenant-specific login URLs: /<slug>/login/
        if path.endswith('/login/') and path.count('/') >= 2:
            return True
        
        # Check for tenant-specific logout URLs: /<slug>/logout/
        if path.endswith('/logout/') and path.count('/') >= 2:
            return True
        
        return False
    
    def process_request(self, request):
        """
        1. Identify tenant from multiple sources
        2. Validate tenant ownership
        3. Set thread-local context for query interception
        4. Enforce access control
        """
        
        # Skip exempt paths
        if self.should_exempt(request.path):
            return None
        
        # User must be authenticated (except exempt paths)
        # DO NOT redirect here - let AdvancedSecurityMiddleware handle unauthenticated access
        if not request.user.is_authenticated:
            logger.debug(f"Unauthenticated request to {request.path} - skipping tenant isolation")
            return None

        # Allow cross-company access for client and marketer roles
        # Clients and marketers are intentionally not bound to a tenant
        user_role = getattr(request.user, 'role', None)
        if user_role in ('client', 'marketer'):
            # Clear any tenant context and allow the request to proceed
            request.company = None
            try:
                clear_tenant_context()
            except Exception:
                pass
            logger.info(f"ENHANCED_MIDDLEWARE: Bypass tenant detection for {user_role} {request.user.email}")
            return None
        
        # Try to identify tenant
        company = self._identify_tenant(request)
        
        if not company:
            logger.error(
                f"Failed to identify tenant for user {request.user.email} "
                f"accessing {request.path}"
            )
            return redirect('login')
        
        # Validate user belongs to this tenant
        if not self._validate_tenant_access(request.user, company):
            logger.error(
                f"SECURITY: User {request.user.email} attempted unauthorized "
                f"access to company {company.company_name}"
            )
            return PermissionDenied("Unauthorized tenant access")
        
        # Set tenant context for this thread
        request.company = company
        set_current_tenant(company=company, user=request.user)
        
        logger.debug(
            f"Tenant context set: {request.user.email} → {company.company_name}"
        )
        
        return None
    
    def _identify_tenant(self, request):
        """
        Try multiple methods to identify tenant:
        1. URL slug (/<company-slug>/...)
        2. User's company profile
        3. Domain/subdomain
        4. API key
        """
        
        # Method 1: URL slug
        company = self._get_tenant_from_url(request)
        if company:
            return company
        
        # Method 2: User's company profile
        if hasattr(request.user, 'company_profile') and request.user.company_profile:
            return request.user.company_profile
        
        # Method 3: Domain/subdomain
        company = self._get_tenant_from_domain(request)
        if company:
            return company
        
        # Method 4: API key (for API requests)
        if request.path.startswith('/api/'):
            company = self._get_tenant_from_api_key(request)
            if company:
                return company
        
        return None
    
    def _get_tenant_from_url(self, request):
        """Extract tenant from URL slug: /<company-slug>/..."""
        parts = request.path.strip('/').split('/')
        if len(parts) > 0:
            slug = parts[0]
            try:
                return Company.objects.get(slug=slug, is_active=True)
            except Company.DoesNotExist:
                pass
        return None
    
    def _get_tenant_from_domain(self, request):
        """Extract tenant from domain: company.platform.com or company.com"""
        host = request.get_host().split(':')[0].lower()
        
        # Try exact domain match
        try:
            return Company.objects.get(
                custom_domain=host,
                is_active=True
            )
        except Company.DoesNotExist:
            pass
        
        # Try subdomain match
        if '.' in host:
            subdomain = host.split('.')[0].replace('-', ' ')
            try:
                return Company.objects.get(
                    slug=subdomain,
                    is_active=True
                )
            except Company.DoesNotExist:
                pass
        
        return None
    
    def _get_tenant_from_api_key(self, request):
        """Extract tenant from API key header"""
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        try:
            return Company.objects.get(api_key=api_key, is_active=True)
        except Company.DoesNotExist:
            logger.warning(f"Invalid API key provided")
            return None
    
    def _validate_tenant_access(self, user, company):
        """
        Verify user has access to this tenant
        
        Returns True if:
        - User is company admin for this company
        - User has any role in this company
        - User is system admin
        """
        
        # System/Super admin can access any company
        if hasattr(user, 'is_system_admin') and user.is_system_admin:
            return True
        
        if hasattr(user, 'is_super_admin') and user.is_super_admin:
            return True
        
        # Check if user belongs to this company
        if hasattr(user, 'company_profile'):
            return user.company_profile == company
        
        return False
    
    def process_response(self, request, response):
        """Clean up tenant context after request"""
        clear_tenant_context()
        return response
    
    def process_exception(self, request, exception):
        """Clean up tenant context if exception occurs"""
        clear_tenant_context()
        return None


class TenantValidationMiddleware(MiddlewareMixin):
    """
    Validates tenant integrity and detects isolation violations
    """
    
    def process_request(self, request):
        """Validate request has proper tenant context"""
        
        # Skip exempt paths and unauthenticated users
        exempt_paths = ['/admin/', '/super-admin/', '/static/', '/media/', '/login/', '/logout/', '/health/',
                       '/client-dashboard', '/marketer-dashboard', '/client-dashboard-cross-company/',
                       '/subscription/', '/company-profile/', '/api/subscription/', '/api/billing/']
        if any(request.path.startswith(p) for p in exempt_paths):
            return None
        
        if not request.user.is_authenticated:
            return None

        # Allow client/marketer users to bypass tenant validation
        user_role = getattr(request.user, 'role', None)
        if user_role in ('client', 'marketer'):
            return None
        
        # Verify tenant context is set
        current_tenant = get_current_tenant()

        if not current_tenant or not getattr(current_tenant, 'company', current_tenant):
            logger.error(
                f"SECURITY ALERT: Tenant context not set for {request.user.email}"
            )
            raise PermissionDenied("Invalid tenant context")
        
        # Additional validation: verify user still has access
        if hasattr(request, 'company'):
            if request.user.company_profile != request.company:
                logger.error(
                    f"SECURITY ALERT: User {request.user.email} attempted "
                    f"access to unauthorized company"
                )
                raise PermissionDenied("Unauthorized company access")
        
        return None


class SubscriptionEnforcementMiddleware(MiddlewareMixin):
    """
    Enforces subscription-based feature limits
    """
    
    QUOTA_PATHS = {
        '/api/': 'api_calls',
        '/export/': 'exports',
    }
    
    def process_request(self, request):
        """Check if request violates subscription limits"""

        # Skip static assets and common public paths
        path = getattr(request, 'path', '') or ''
        if path.startswith(('/static/', '/media/')) or path == '/favicon.ico':
            return None
        if path.startswith(('/login/', '/logout/', '/admin/login/', '/super-admin/', '/tenant-admin/login/', '/tenant-admin/logout/')):
            return None
        # Allow redirect handlers (these are just routing, not actual pages)
        if path in ('/admin_dashboard/', '/admin-dashboard/', '/management-dashboard/'):
            return None
        # Allow billing/subscription management pages even when inactive
        if path.startswith(('/subscription/', '/api/subscription/', '/api/billing/', '/subscription/payment/', '/company-profile/')):
            return None
        # Allow polling/AJAX endpoints to not break page functionality
        if path in ('/chat_unread_count/', '/estate-allocation-data/') or path.startswith('/api/alerts/'):
            return None
        
        # Skip if no company context (clients/marketers work across companies)
        if not hasattr(request, 'company') or request.company is None:
            return None
        
        company = request.company
        
        # Skip for super admins
        if hasattr(request.user, 'is_super_admin') and request.user.is_super_admin:
            return None
        
        # Check subscription status
        if not hasattr(company, 'subscription_details'):
            return None
        
        subscription = company.subscription_details
        
        # Check if subscription is active
        if not subscription.is_active():
            logger.info(
                f"Subscription inactive for {company.company_name}: "
                f"payment_status={getattr(subscription, 'payment_status', None)} "
                f"period_end={getattr(subscription, 'current_period_end', None)} "
                f"company_status={getattr(company, 'subscription_status', None)} "
                f"- Allowing access with subscription banner"
            )

            # ✅ ALLOW ALL USERS TO ACCESS DASHBOARD REGARDLESS OF SUBSCRIPTION STATUS
            # Set flags for templates to display subscription renewal banners
            
            # Calculate subscription state from available data
            now = timezone.now()
            
            # Determine if in grace period or fully expired
            # Grace period: 7 FULL days after subscription ends (not including the end day)
            subscription_end = getattr(subscription, 'current_period_end', None) or getattr(company, 'subscription_ends_at', None)
            grace_period_end = getattr(company, 'grace_period_ends_at', None)
            
            # Calculate grace period if not set: Add 8 days to ensure 7 FULL days
            # Example: Sub ends Jan 5 → Grace period: Jan 6-12 (7 days) → Expires Jan 13
            if subscription_end and not grace_period_end:
                grace_period_end = subscription_end + timedelta(days=8)
            
            is_in_grace_period = grace_period_end and now < grace_period_end
            is_fully_expired = grace_period_end and now >= grace_period_end
            is_trial_user = subscription.is_trial() if hasattr(subscription, 'is_trial') and callable(subscription.is_trial) else (getattr(subscription, 'billing_cycle', None) == 'trial' or getattr(company, 'subscription_status', None) == 'trial')
            
            # Set base flags for banner display
            request.subscription_expired = True
            request.subscription_needs_renewal = True
            request.subscription_status = getattr(company, 'subscription_status', 'expired')
            
            # Critical flag: Only mute features AFTER grace period expires
            request.subscription_grace_period_expired = is_fully_expired
            
            # Distinguish between trial expiration and subscription renewal
            # Trial users have never made a payment
            has_payment_history = getattr(subscription, 'last_payment_at', None) is not None
            request.is_trial_expiration = is_trial_user or not has_payment_history
            
            # Add subscription details to request for banner display
            request.subscription_end_date = subscription_end
            request.grace_period_end_date = grace_period_end
            request.company_name = company.company_name
            
            # Calculate days until grace period ends (for display)
            if grace_period_end:
                days_remaining = (grace_period_end - now).days
                request.days_until_grace_end = max(0, days_remaining)
            
            # Allow full access - banners shown, muting only after grace period
            return None
        
        # ✅ CHECK FOR ACTIVE SUBSCRIPTIONS EXPIRING SOON (2 MONTHS OR LESS)
        # This is for renewal companies to show early warnings
        if subscription.is_active():
            now = timezone.now()
            subscription_end = getattr(subscription, 'current_period_end', None) or getattr(company, 'subscription_ends_at', None)
            
            if subscription_end:
                days_until_expiration = (subscription_end - now).days
                two_months_days = 60  # Approximately 2 months
                
                # Show alert if 2 months or less remaining
                if 0 <= days_until_expiration <= two_months_days:
                    request.subscription_expiring_soon = True
                    request.days_until_expiration = days_until_expiration
                    request.subscription_end_date = subscription_end
                    request.company_name = company.company_name
        
        # TODO: Check specific quotas based on request path
        
        return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Logs all data access for audit trail and compliance
    """
    
    LOG_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_response(self, request, response):
        """Log important actions"""
        
        # Only log for authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Only log certain methods
        if request.method not in self.LOG_METHODS:
            return response
        
        # Skip admin, static, and health check
        skip_paths = ['/admin/', '/super-admin/', '/static/', '/media/', '/health/', '/login/', '/logout/', '/register/',
                     '/client-dashboard', '/marketer-dashboard', '/client-dashboard-cross-company/']
        if any(request.path.startswith(p) for p in skip_paths):
            return response
        
        try:
            from estateApp.isolation import IsolationAuditLog
            
            company = getattr(request, 'company', None)
            
            # Determine action type
            action_map = {
                'GET': 'READ',
                'POST': 'CREATE',
                'PUT': 'UPDATE',
                'PATCH': 'UPDATE',
                'DELETE': 'DELETE',
            }
            
            action = action_map.get(request.method, 'ACCESS_DENIED')
            
            # Create audit log
            IsolationAuditLog.objects.create(
                company=company,
                user=request.user,
                action=action,
                model_name=request.path.split('/')[-1],
                object_id=0,  # TODO: Extract from request
                description=f"{request.method} {request.path}",
                ip_address=self._get_client_ip(request),
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return response
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Adds security headers to prevent common attacks
    """
    
    def process_response(self, request, response):
        """Add security headers"""
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy
        # Allow common CDNs/fonts used by the UI (jsDelivr, cdnjs, Google Fonts)
        response['Content-Security-Policy'] = (
            "default-src 'self' https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Feature Policy
        response['Feature-Policy'] = (
            "geolocation 'none'; "
            "microphone 'none'; "
            "camera 'none'; "
            "payment 'none';"
        )
        
        return response
