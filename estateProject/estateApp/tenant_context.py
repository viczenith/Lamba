"""
TENANT CONTEXT PROPAGATION
Ensures tenant context flows through entire request lifecycle:
Authentication → View → Query → Database
"""

import threading
import functools
import logging
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Thread-local storage for tenant context
_tenant_context = threading.local()


class TenantContextPropagator:
    """
    Manages tenant context propagation across request lifecycle
    Ensures tenant is set at every level
    """
    
    @staticmethod
    def set_tenant(company_id, user=None):
        """Set tenant context for current thread"""
        _tenant_context.company_id = company_id
        _tenant_context.user = user
        logger.debug(f"Tenant context set: company_id={company_id}, user={user}")
    
    @staticmethod
    def get_tenant():
        """Get tenant context from current thread"""
        company_id = getattr(_tenant_context, 'company_id', None)
        user = getattr(_tenant_context, 'user', None)
        return {
            'company_id': company_id,
            'user': user,
            'is_set': company_id is not None
        }
    
    @staticmethod
    def clear_tenant():
        """Clear tenant context"""
        if hasattr(_tenant_context, 'company_id'):
            delattr(_tenant_context, 'company_id')
        if hasattr(_tenant_context, 'user'):
            delattr(_tenant_context, 'user')
        logger.debug("Tenant context cleared")
    
    @staticmethod
    def is_tenant_set():
        """Check if tenant context is set"""
        return getattr(_tenant_context, 'company_id', None) is not None


class TenantContextMiddleware:
    """
    CRITICAL: Middleware that propagates tenant context from request to thread-local storage
    
    Must run AFTER:
    - AuthenticationMiddleware (to identify user)
    - SessionMiddleware
    
    Must run BEFORE:
    - Any view that uses tenant-filtered models
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        """Propagate tenant context before view execution"""
        
        try:
            # Extract tenant from request
            tenant_info = self._extract_tenant(request)
            
            if tenant_info['company_id']:
                # Set tenant context in thread-local storage
                TenantContextPropagator.set_tenant(
                    company_id=tenant_info['company_id'],
                    user=tenant_info['user']
                )
                logger.debug(
                    f"Tenant context propagated to thread for {tenant_info['user']}"
                )
            
            # Process request
            response = self.get_response(request)
            
        finally:
            # Always clear tenant context after request
            TenantContextPropagator.clear_tenant()
        
        return response
    
    @staticmethod
    def _extract_tenant(request):
        """Extract tenant information from request"""
        
        # Try multiple sources
        # 1. From session/request (set by authentication)
        if hasattr(request, 'company'):
            return {
                'company_id': request.company.id if request.company else None,
                'user': request.user
            }
        
        # 2. From authenticated user's profile
        if request.user.is_authenticated:
            if hasattr(request.user, 'company_profile'):
                return {
                    'company_id': request.user.company_profile.id if request.user.company_profile else None,
                    'user': request.user
                }
        
        return {'company_id': None, 'user': None}


class TenantRequired:
    """
    Decorator that enforces tenant context requirement
    
    Usage:
        @tenant_required
        def my_view(request):
            # Tenant context guaranteed to be set
            pass
    """
    
    def __init__(self, view_func):
        self.view_func = view_func
        functools.update_wrapper(self, view_func)
    
    def __call__(self, request, *args, **kwargs):
        """Check tenant context before executing view"""
        
        # Verify tenant context is set
        if not TenantContextPropagator.is_tenant_set():
            logger.error(
                f"Tenant context not set for user {request.user}"
            )
            raise PermissionDenied("Tenant context not set")
        
        # Verify user belongs to this tenant
        tenant_info = TenantContextPropagator.get_tenant()
        if hasattr(request.user, 'company_profile'):
            if request.user.company_profile.id != tenant_info['company_id']:
                logger.error(
                    f"User {request.user} belongs to different company"
                )
                raise PermissionDenied("Invalid tenant context")
        
        # Execute view
        return self.view_func(request, *args, **kwargs)


class TenantContextManager:
    """
    Context manager for setting tenant context temporarily
    
    Usage:
        with TenantContextManager(company_id=5):
            # Tenant context set to 5
            PlotSize.objects.all()  # Filtered to company 5
        # Tenant context cleared
    """
    
    def __init__(self, company_id, user=None):
        self.company_id = company_id
        self.user = user
        self.previous_context = None
    
    def __enter__(self):
        """Save previous context and set new one"""
        self.previous_context = TenantContextPropagator.get_tenant()
        TenantContextPropagator.set_tenant(self.company_id, self.user)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous context"""
        if self.previous_context['company_id']:
            TenantContextPropagator.set_tenant(
                self.previous_context['company_id'],
                self.previous_context['user']
            )
        else:
            TenantContextPropagator.clear_tenant()


# Convenience functions
def set_current_tenant(company_id, user=None):
    """Set tenant context for current request"""
    TenantContextPropagator.set_tenant(company_id, user)


def get_current_tenant():
    """Get tenant context for current request"""
    return TenantContextPropagator.get_tenant()


def clear_current_tenant():
    """Clear tenant context"""
    TenantContextPropagator.clear_tenant()


def require_tenant(view_func):
    """Decorator: Require tenant context for view"""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not TenantContextPropagator.is_tenant_set():
            return JsonResponse(
                {'error': 'Tenant context not set'},
                status=403
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def with_tenant_context(company_id, user=None):
    """
    Decorator: Execute view with specific tenant context
    
    Usage:
        @with_tenant_context(company_id=5)
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            with TenantContextManager(company_id=company_id, user=user):
                return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class TenantContextVerifier:
    """
    Verifies tenant context propagation at each stage
    Used for debugging isolation issues
    """
    
    @staticmethod
    def verify_request_stage(request):
        """Verify tenant at request stage"""
        has_company = hasattr(request, 'company') and request.company is not None
        has_user = request.user.is_authenticated
        
        return {
            'stage': 'request',
            'has_company': has_company,
            'has_user': has_user,
            'company': request.company if has_company else None,
            'user': request.user if has_user else None
        }
    
    @staticmethod
    def verify_thread_stage():
        """Verify tenant in thread-local storage"""
        context = TenantContextPropagator.get_tenant()
        
        return {
            'stage': 'thread-local',
            'company_id': context['company_id'],
            'user': context['user'],
            'is_set': context['is_set']
        }
    
    @staticmethod
    def verify_query_stage():
        """Verify tenant at query execution stage"""
        context = TenantContextPropagator.get_tenant()
        
        return {
            'stage': 'query',
            'company_id': context['company_id'],
            'is_set': context['is_set'],
            'ready_for_query': context['company_id'] is not None
        }
    
    @staticmethod
    def verify_all_stages(request):
        """Verify tenant propagation through all stages"""
        
        verification = {
            'request_stage': TenantContextVerifier.verify_request_stage(request),
            'thread_stage': TenantContextVerifier.verify_thread_stage(),
            'query_stage': TenantContextVerifier.verify_query_stage(),
        }
        
        # Check for propagation gaps
        issues = []
        
        if verification['request_stage']['has_company'] and \
           not verification['thread_stage']['is_set']:
            issues.append("Company in request but not in thread-local storage")
        
        if verification['thread_stage']['is_set'] and \
           not verification['query_stage']['ready_for_query']:
            issues.append("Company in thread-local but not ready for queries")
        
        verification['issues'] = issues
        verification['status'] = 'OK' if not issues else 'ISSUES_FOUND'
        
        return verification


class TenantContextLogger:
    """
    Logs tenant context changes for debugging
    """
    
    @staticmethod
    def log_context_set(company_id, user):
        """Log when tenant context is set"""
        logger.debug(
            f"Tenant context set | company_id={company_id} | user={user}"
        )
    
    @staticmethod
    def log_context_clear():
        """Log when tenant context is cleared"""
        logger.debug("Tenant context cleared")
    
    @staticmethod
    def log_context_verify(verification):
        """Log context verification results"""
        if verification['status'] == 'OK':
            logger.debug("✅ Tenant context propagation OK")
        else:
            logger.warning(
                f"⚠️ Tenant context issues: {verification['issues']}"
            )


# Configuration
TENANT_CONTEXT_TIMEOUT = 3600  # 1 hour
TENANT_CONTEXT_VALIDATION = True  # Validate at each stage
TENANT_CONTEXT_LOGGING = True  # Log context changes
