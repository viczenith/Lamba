"""
Enhanced Multi-Tenant Middleware
Complete tenant isolation for the SaaS platform
"""
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from estateApp.models import Company
import logging

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Ensures complete data isolation between tenants
    Attaches current tenant/company to every request
    """
    
    # URLs that don't require tenant context
    EXEMPT_URLS = [
        '/admin/',
        '/super-admin/',
        '/api/auth/',
        '/static/',
        '/media/',
        '/login/',
        '/logout/',
        '/register/',
        '/api/company/register/',
    ]
    
    def process_request(self, request):
        """Attach company to request based on user or domain"""
        
        # Skip exempt URLs
        if any(request.path.startswith(url) for url in self.EXEMPT_URLS):
            return None
        
        # Skip if user not authenticated
        if not request.user.is_authenticated:
            return None
        
        # Super admins can access everything
        if hasattr(request.user, 'super_admin_profile'):
            request.is_super_admin = True
            # Super admins can switch companies via query param
            company_id = request.GET.get('company_id')
            if company_id:
                try:
                    request.company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    pass
            return None
        
        # Get company from user profile
        if hasattr(request.user, 'company_profile') and request.user.company_profile:
            request.company = request.user.company_profile
            
            # Check if company subscription is active
            if hasattr(request.company, 'subscription_details'):
                subscription = request.company.subscription_details
                
                # Check if trial expired
                if subscription.billing_cycle == 'trial' and subscription.trial_ends_at:
                    if subscription.trial_ends_at < timezone.now():
                        if not request.path.startswith('/subscription/'):
                            return redirect('subscription_expired')
                
                # Check if subscription expired
                if subscription.payment_status in ['past_due', 'cancelled', 'suspended']:
                    if not request.path.startswith('/subscription/'):
                        return redirect('subscription_suspended')
        else:
            # User without company - might be system admin or incomplete profile
            logger.warning(f"User {request.user.email} has no company profile")
            request.company = None
        
        return None
    
    def process_template_response(self, request, response):
        """Add tenant context to all templates"""
        if hasattr(request, 'company'):
            if hasattr(response, 'context_data') and response.context_data is not None:
                response.context_data['tenant_company'] = request.company
        return response


class QuerysetIsolationMiddleware(MiddlewareMixin):
    """
    Automatically filter all querysets by current tenant
    This is a safety layer to prevent cross-tenant data leaks
    """
    
    def process_request(self, request):
        """Store current company in thread-local for queryset filtering"""
        from threading import current_thread
        
        if hasattr(request, 'company'):
            # Store company in thread local
            current_thread().current_company = request.company
        
        return None
    
    def process_response(self, request, response):
        """Clean up thread local"""
        from threading import current_thread
        
        if hasattr(current_thread(), 'current_company'):
            delattr(current_thread(), 'current_company')
        
        return response


class APITenantMiddleware(MiddlewareMixin):
    """
    Handles tenant identification for API requests
    Supports multiple methods: domain, subdomain, API key, JWT token
    """
    
    def process_request(self, request):
        """Identify tenant for API requests"""
        
        # Skip non-API requests
        if not request.path.startswith('/api/'):
            return None
        
        # Already handled by user authentication
        if hasattr(request, 'company'):
            return None
        
        # Method 1: API Key in header
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            try:
                company = Company.objects.get(api_key=api_key, is_active=True)
                request.company = company
                return None
            except Company.DoesNotExist:
                pass
        
        # Method 2: Custom domain
        host = request.get_host().split(':')[0]
        try:
            company = Company.objects.get(custom_domain=host, is_active=True)
            request.company = company
            return None
        except Company.DoesNotExist:
            pass
        
        # Method 3: Subdomain (e.g., companyname.platform.com)
        if '.' in host:
            subdomain = host.split('.')[0]
            try:
                company = Company.objects.get(
                    company_name__iexact=subdomain.replace('-', ' '),
                    is_active=True
                )
                request.company = company
                return None
            except Company.DoesNotExist:
                pass
        
        return None


class SubscriptionEnforcementMiddleware(MiddlewareMixin):
    """
    Enforces subscription limits (plots, agents, API calls, etc.)
    """
    
    def process_request(self, request):
        """Check and enforce subscription limits"""
        
        # Skip if no company
        if not hasattr(request, 'company') or not request.company:
            return None
        
        company = request.company
        
        # Skip if super admin
        if hasattr(request, 'is_super_admin') and request.is_super_admin:
            return None
        
        # Get subscription
        if not hasattr(company, 'subscription_details'):
            return None
        
        subscription = company.subscription_details
        plan = subscription.plan
        
        # Store limits in request for easy access
        request.subscription_limits = {
            'max_plots': plan.max_plots,
            'max_agents': plan.max_agents,
            'max_admins': plan.max_admins,
            'max_api_calls_daily': plan.max_api_calls_daily,
            'max_storage_gb': plan.max_storage_gb,
        }
        
        # Check API call limits for API requests
        if request.path.startswith('/api/'):
            # TODO: Implement API call tracking and limiting
            pass
        
        return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Logs all important actions for audit trail
    """
    
    # Actions to log
    LOG_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def process_response(self, request, response):
        """Log important actions"""
        
        # Only log for authenticated users
        if not request.user.is_authenticated:
            return response
        
        # Only log certain methods
        if request.method not in self.LOG_METHODS:
            return response
        
        # Only log successful requests
        if response.status_code >= 400:
            return response
        
        # Skip admin and static files
        if request.path.startswith(('/admin/', '/static/', '/media/')):
            return response
        
        # Log the action
        try:
            from superAdmin.models import SystemAuditLog
            
            # Determine action type
            action_type = 'other'
            if 'company' in request.path:
                action_type = 'company_modified'
            elif 'user' in request.path:
                action_type = 'user_modified'
            elif 'subscription' in request.path:
                action_type = 'subscription_changed'
            
            # Create log entry
            SystemAuditLog.objects.create(
                admin_user=getattr(request.user, 'super_admin_profile', None),
                action_type=action_type,
                target_company=getattr(request, 'company', None),
                description=f"{request.method} {request.path}",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                metadata={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                }
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        return response
