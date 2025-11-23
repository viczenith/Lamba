"""
Subscription-Based Feature Access Control
Decorators and middleware to enforce subscription limits and restrictions
"""

from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DECORATORS FOR VIEWS
# ============================================================================

def subscription_required(feature='general'):
    """
    Decorator to require active subscription for a view
    Redirects to subscription/upgrade if not active
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                company = request.user.company
                billing = company.billing
                billing.refresh_status()
                
                # Check if subscription is active
                if not billing.is_active():
                    return redirect('subscription_upgrade', company_slug=company.slug)
                
                return view_func(request, *args, **kwargs)
            except Exception as e:
                logger.error(f"Subscription check failed: {str(e)}")
                return redirect('dashboard')
        
        return wrapper
    return decorator


def can_create_client_required(view_func):
    """Require permission to create clients"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        company = request.user.company
        
        # Check if can create client
        can_create, message = company.can_add_client()
        if not can_create:
            raise PermissionDenied(message)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def can_create_allocation_required(view_func):
    """Require permission to create allocations"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        company = request.user.company
        
        # Check if can create allocation
        can_create, message = company.can_create_allocation()
        if not can_create:
            raise PermissionDenied(message)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def read_only_if_grace_period(view_func):
    """
    Allow GET requests in grace period, but block POST/PUT/DELETE
    Used for views that should be read-only during grace period
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            company = request.user.company
            billing = company.billing
            
            if billing.is_grace_period():
                # Allow read-only operations
                if request.method not in ['GET', 'HEAD', 'OPTIONS']:
                    return HttpResponseForbidden(
                        "Service is in read-only mode. "
                        "Please renew your subscription to continue."
                    )
        except:
            pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def api_access_required(view_func):
    """Require active subscription for API access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            company = request.user.company
            billing = company.billing
            
            if not billing.can_use_api():
                return JsonResponse({
                    'error': 'API access requires active subscription',
                    'status': billing.status
                }, status=403)
        except:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def trial_active_or_paid_required(view_func):
    """Allow access only during trial or active paid subscription"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        company = request.user.company
        billing = company.billing
        billing.refresh_status()
        
        if not billing.is_active():
            messages.warning(
                request,
                f"Your subscription has {billing.get_access_restrictions()['message']}"
            )
            return redirect('subscription_upgrade', company_slug=company.slug)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# ============================================================================
# MIDDLEWARE - GLOBAL SUBSCRIPTION CHECKING
# ============================================================================

class SubscriptionMiddleware:
    """
    Middleware to check subscription status and inject context
    into all authenticated requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add subscription context if user is authenticated
        if request.user.is_authenticated:
            try:
                company = request.user.company
                billing = company.billing
                billing.refresh_status()
                
                # Inject into request object
                request.subscription = billing
                request.can_access_features = billing.can_access_features()
                request.access_restrictions = billing.get_access_restrictions()
                
                # Check for expired subscription and set warning
                if billing.get_warning_level() > 0:
                    warning = billing.get_warning_message()
                    if warning:
                        request.subscription_warning = warning
            except Exception as e:
                logger.warning(f"Subscription context error: {str(e)}")
        
        response = self.get_response(request)
        return response


# ============================================================================
# CONTEXT PROCESSOR - INJECT INTO ALL TEMPLATES
# ============================================================================

def subscription_context(request):
    """
    Context processor to inject subscription data into all templates
    Add to TEMPLATES['OPTIONS']['context_processors'] in settings.py:
    'estateApp.subscription_access.subscription_context'
    """
    context = {}
    
    if request.user.is_authenticated:
        try:
            company = request.user.company
            billing = company.billing
            billing.refresh_status()
            
            context['user_company'] = company
            context['user_subscription'] = billing
            context['is_trial'] = billing.is_trial()
            context['is_active'] = billing.is_active()
            context['is_grace_period'] = billing.is_grace_period()
            context['is_expired'] = billing.is_expired()
            context['warning_message'] = billing.get_warning_message()
            context['days_remaining'] = billing.get_days_remaining()
            context['should_show_warning'] = billing.should_show_warning_banner()
        except:
            pass
    
    return context


# ============================================================================
# CLASS-BASED VIEW MIXINS
# ============================================================================

class SubscriptionRequiredMixin:
    """
    Mixin for class-based views that require active subscription
    Usage: class MyView(SubscriptionRequiredMixin, ListView): ...
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        billing = request.user.company.billing
        billing.refresh_status()
        
        if not billing.is_active():
            return redirect('subscription_upgrade', 
                          company_slug=request.user.company.slug)
        
        return super().dispatch(request, *args, **kwargs)


class GracePeriodReadOnlyMixin:
    """
    Mixin to make views read-only during grace period
    """
    
    def dispatch(self, request, *args, **kwargs):
        billing = request.user.company.billing
        
        if billing.is_grace_period():
            if request.method not in ['GET', 'HEAD', 'OPTIONS']:
                raise PermissionDenied(
                    "Service is in read-only mode. "
                    "Please renew your subscription."
                )
        
        return super().dispatch(request, *args, **kwargs)


class FeatureLimitMixin:
    """
    Mixin to check feature limits before creating objects
    Override get_feature_limit() to specify which limit to check
    """
    
    def get_feature_limit(self):
        """Override this to specify feature to check"""
        raise NotImplementedError("Subclasses must implement get_feature_limit()")
    
    def check_feature_access(self, request):
        """Check if user can access this feature"""
        company = request.user.company
        feature = self.get_feature_limit()
        
        can_create, message = getattr(company, f'can_{feature}')()
        if not can_create:
            raise PermissionDenied(message)
    
    def post(self, request, *args, **kwargs):
        self.check_feature_access(request)
        return super().post(request, *args, **kwargs)


# ============================================================================
# USAGE TRACKING & ENFORCEMENT
# ============================================================================

def track_usage(feature_type):
    """
    Decorator to track feature usage and enforce limits
    Usage: @track_usage('clients')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            company = request.user.company
            
            # Get current usage
            usage_stats = company.get_usage_stats()
            limits = company.get_feature_limits()
            
            current_usage = usage_stats.get(feature_type, 0)
            limit = limits.get(feature_type, float('inf'))
            
            # Inject into request for view to use
            request.feature_usage = {
                'type': feature_type,
                'current': current_usage,
                'limit': limit,
                'remaining': max(0, limit - current_usage)
            }
            
            # Log usage
            logger.info(
                f"Feature usage tracked: {feature_type} "
                f"({current_usage}/{limit}) for {company.company_name}"
            )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# USAGE ENFORCEMENT IN VIEWS
# ============================================================================

def check_client_limit(company):
    """
    Check if company can add new client
    Returns: (can_add, message, current_usage, limit)
    """
    from .models import ClientUser
    
    usage = ClientUser.objects.filter(company=company).count()
    limit = company.max_clients
    
    can_add = usage < limit
    message = f"Client limit reached ({usage}/{limit})" if not can_add else ""
    
    return can_add, message, usage, limit


def check_allocation_limit(company):
    """
    Check if company can create allocation
    Returns: (can_add, message, current_usage, limit)
    """
    from .models import PlotAllocation
    from django.utils import timezone
    from datetime import timedelta
    
    # Count allocations in current month
    today = timezone.now()
    month_start = today.replace(day=1)
    
    usage = PlotAllocation.objects.filter(
        company=company,
        created_at__gte=month_start
    ).count()
    limit = company.max_allocations
    
    can_add = usage < limit
    message = f"Monthly allocation limit reached ({usage}/{limit})" if not can_add else ""
    
    return can_add, message, usage, limit


def get_api_call_remaining(company):
    """
    Get remaining API calls for today
    """
    from django.utils import timezone
    from .models import APIUsageLog
    
    today = timezone.now().date()
    
    usage_today = APIUsageLog.objects.filter(
        company=company,
        created_at__date=today
    ).count()
    
    limit = company.max_api_calls_daily
    remaining = max(0, limit - usage_today)
    
    return remaining, limit, usage_today


# ============================================================================
# SETTINGS TO ADD
# ============================================================================

"""
Add to settings.py:

# Subscription Middleware
MIDDLEWARE = [
    # ... existing middleware ...
    'estateApp.subscription_access.SubscriptionMiddleware',
]

# Subscription Context Processor
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # ... existing context processors ...
                'estateApp.subscription_access.subscription_context',
            ],
        },
    },
]

# Grace Period Configuration
SUBSCRIPTION_SETTINGS = {
    'TRIAL_DAYS': 14,
    'GRACE_PERIOD_DAYS': 7,
    'WARNING_THRESHOLDS': [7, 4, 2],  # Days before expiry to warn
    'AUTO_RENEW_ENABLED': True,
    'MAX_PAYMENT_RETRIES': 3,
}
"""
