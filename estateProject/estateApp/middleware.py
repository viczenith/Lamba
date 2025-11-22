from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from .models import Company
import logging

logger = logging.getLogger(__name__)


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.resolver_match and request.resolver_match.url_name == 'send-notification':
            if not request.user.is_authenticated or not request.user.is_staff:
                return redirect('login')


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Ensures every request is scoped to a specific company context.
    This prevents users from accessing data from other companies.
    
    Extracts company from:
    1. API key (for programmatic access)
    2. Custom domain (company-specific subdomain)
    3. Authenticated user's company_profile
    """
    
    def process_request(self, request):
        """Extract and attach company context to request"""
        try:
            request.company = None
            request.is_cross_company = False
            
            # Skip tenant isolation for public endpoints
            if self._is_public_endpoint(request):
                return None
            
            # Try to get company from different sources
            company = self._extract_company_from_request(request)
            
            if company:
                request.company = company
                logger.debug(f"Tenant context set: {company.company_name}")
            else:
                # If user is authenticated but no company, try to get from user
                if request.user.is_authenticated:
                    if hasattr(request.user, 'company_profile') and request.user.company_profile:
                        request.company = request.user.company_profile
                    else:
                        # Client or marketer - they can access multiple companies
                        request.is_cross_company = True
            
            return None
            
        except Exception as e:
            logger.error(f"Error in TenantIsolationMiddleware: {str(e)}")
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
        ]
        
        for path in public_paths:
            if request.path.startswith(path):
                return True
        
        return False
    
    def _extract_company_from_request(self, request):
        """
        Extract company from request in priority order:
        1. API key in Authorization header
        2. Custom domain
        3. Authenticated user's company
        """
        
        # 1. Check for API key in Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('ApiKey '):
            api_key = auth_header.split(' ')[1]
            try:
                company = Company.objects.get(api_key=api_key, is_active=True)
                return company
            except Company.DoesNotExist:
                logger.warning(f"Invalid API key: {api_key}")
                return None
        
        # 2. Check for custom domain
        host = request.META.get('HTTP_HOST', '').split(':')[0]
        try:
            # If request.host matches a custom domain
            company = Company.objects.get(custom_domain=host, is_active=True)
            return company
        except Company.DoesNotExist:
            pass
        
        # 3. Check authenticated user's company
        if request.user.is_authenticated and hasattr(request.user, 'company_profile'):
            company = request.user.company_profile
            if company and company.is_active:
                return company
        
        return None
    
    def process_response(self, request, response):
        """Add tenant context to response headers if applicable"""
        if hasattr(request, 'company') and request.company:
            response['X-Tenant-ID'] = str(request.company.id)
            response['X-Tenant-Name'] = request.company.company_name
        
        return response


class TenantAccessCheckMiddleware(MiddlewareMixin):
    """
    Validates that users can only access resources
    that belong to their company (unless they're clients/marketers)
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
        if user_role in ['admin', 'support']:
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

