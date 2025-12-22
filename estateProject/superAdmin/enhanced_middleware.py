"""
ENHANCED PRODUCTION MULTI-TENANT MIDDLEWARE
Implements query interception and automatic isolation
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.utils import timezone
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
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated request to {request.path}")
            return redirect('login')

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
        exempt_paths = ['/admin/', '/static/', '/media/', '/login/', '/logout/', '/health/',
                       '/client-dashboard', '/marketer-dashboard', '/client-dashboard-cross-company/']
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
        
        if not hasattr(request, 'company'):
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
            logger.warning(
                f"Subscription inactive for {company.company_name}: "
                f"{subscription.payment_status}"
            )
            # Return 402 Payment Required
            from django.http import JsonResponse
            return JsonResponse(
                {'error': 'Subscription inactive'},
                status=402
            )
        
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
        skip_paths = ['/admin/', '/static/', '/media/', '/health/', '/login/', '/logout/', '/register/',
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
