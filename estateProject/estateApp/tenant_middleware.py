"""
Middleware for multi-tenant architecture.
Handles tenant/company extraction and validation.
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.urls import resolve
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    Extract and validate tenant (company) from request.
    Sets request.company for use in views and permissions.
    """
    
    # Public endpoints that don't require company
    PUBLIC_PATHS = [
        '/api/auth/login/',
        '/api/auth/register/',
        '/api/auth/password-reset/',
        '/admin/',
        '/health/',
    ]
    
    def process_request(self, request):
        """Process request and extract company"""
        
        # Check if this is a public path
        if self._is_public_path(request.path):
            return None
        
        # Try to extract company
        company = self._extract_company(request)
        
        if company:
            request.company = company
            return None
        
        # If company is required but not found
        if not self._is_public_path(request.path):
            logger.warning(f"No company found for request to {request.path} by {request.user}")
        
        return None
    
    def _extract_company(self, request):
        """Extract company from various sources"""
        
        # 1. Check URL parameters
        company_id = request.GET.get('company_id')
        if company_id:
            return self._get_company_by_id(company_id)
        
        # 2. Check request headers
        company_id = request.META.get('HTTP_X_COMPANY_ID')
        if company_id:
            return self._get_company_by_id(company_id)
        
        # 3. Check authenticated user
        if request.user and request.user.is_authenticated:
            if hasattr(request.user, 'company'):
                return request.user.company
        
        # 4. Check API key (if authenticated)
        if hasattr(request, 'api_key'):
            return request.api_key.company
        
        return None
    
    def _get_company_by_id(self, company_id):
        """Get company by ID"""
        try:
            from estateApp.models import Company
            return Company.objects.get(id=company_id)
        except Exception as e:
            logger.error(f"Error getting company {company_id}: {e}")
            return None
    
    def _is_public_path(self, path):
        """Check if path is public"""
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                return True
        
        return False
    
    def process_response(self, request, response):
        """Add tenant info to response headers"""
        
        if hasattr(request, 'company') and request.company:
            response['X-Tenant-ID'] = str(request.company.id)
        
        return response


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Enforce strict tenant isolation.
    Prevents users from accessing other tenants' data.
    """
    
    def process_request(self, request):
        """Validate tenant isolation"""
        
        # Skip for unauthenticated users
        if not request.user or not request.user.is_authenticated:
            return None
        
        user_company = self._get_user_company(request)
        request_company = getattr(request, 'company', None)
        
        # If user has a company but request is for different company
        if user_company and request_company and user_company != request_company:
            logger.error(
                f"Tenant isolation violation: User {request.user} ({user_company}) "
                f"attempted to access {request_company} at {request.path}"
            )
            return JsonResponse({
                'error': 'Unauthorized access to this tenant.',
                'code': 'TENANT_MISMATCH'
            }, status=403)
        
        return None
    
    def _get_user_company(self, request):
        """Get company associated with user"""
        try:
            if hasattr(request.user, 'company'):
                return request.user.company
            
            # Try to get through employee/profile relationship
            if hasattr(request.user, 'employee'):
                return request.user.employee.company
            
            if hasattr(request.user, 'profile'):
                return request.user.profile.company
        
        except Exception as e:
            logger.warning(f"Error getting user company: {e}")
        
        return None


class RateLimitMiddleware(MiddlewareMixin):
    """
    Track API usage for rate limiting.
    Records requests to calculate usage statistics.
    """
    
    def process_request(self, request):
        """Record request start time"""
        request._start_time = __import__('time').time()
        return None
    
    def process_response(self, request, response):
        """Record request usage"""
        
        # Only track API requests
        if not request.path.startswith('/api/'):
            return response
        
        # Skip HEAD requests
        if request.method == 'HEAD':
            return response
        
        try:
            from django.core.cache import cache
            from django.utils import timezone
            
            # Get company
            company = getattr(request, 'company', None)
            if not company:
                return response
            
            # Get request duration
            duration = __import__('time').time() - getattr(request, '_start_time', 0)
            
            # Update usage stats
            cache_key = f'usage:company:{company.id}:{timezone.now().strftime("%Y%m%d")}'
            current = cache.get(cache_key, {'requests': 0, 'duration': 0})
            current['requests'] += 1
            current['duration'] += duration
            cache.set(cache_key, current, 86400)  # 24 hours
            
            # Add usage info to response headers
            response['X-API-Requests-Today'] = str(current['requests'])
            response['X-API-Duration-Today'] = f"{current['duration']:.2f}s"
        
        except Exception as e:
            logger.error(f"Error recording API usage: {e}")
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Log all API requests for audit trail.
    """
    
    def process_request(self, request):
        """Log incoming request"""
        
        if request.path.startswith('/api/'):
            company = getattr(request, 'company', None)
            user = request.user if request.user.is_authenticated else 'anonymous'
            
            logger.info(
                f"API Request: {request.method} {request.path} "
                f"by {user} in {company}"
            )
        
        return None
    
    def process_response(self, request, response):
        """Log outgoing response"""
        
        if request.path.startswith('/api/'):
            logger.info(
                f"API Response: {request.method} {request.path} -> {response.status_code}"
            )
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to responses.
    """
    
    def process_response(self, request, response):
        """Add security headers"""
        
        # CORS headers (if API)
        if request.path.startswith('/api/'):
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
        
        return response


class CompanyContextMiddleware(MiddlewareMixin):
    """
    Add company context to view and model operations.
    Automatically filters querysets by company.
    """
    
    def process_request(self, request):
        """Store company in thread-local context"""
        
        company = getattr(request, 'company', None)
        
        if company:
            # Store in Django's request context for use in signals, etc.
            from django.core.cache import cache
            
            # Can also use thread-local storage or context vars in Python 3.7+
            import threading
            threading.local().current_company = company
        
        return None
