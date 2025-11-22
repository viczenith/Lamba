"""
API Rate Limiting (Throttles) based on subscription tier.
Enforces API call limits per subscription plan.
"""
import logging
from rest_framework.throttling import UserRateThrottle, BaseThrottle
from rest_framework.exceptions import Throttled
from django.core.cache import cache
from django.utils import timezone
from estateApp.models import Company

logger = logging.getLogger(__name__)


class SubscriptionTierThrottle(BaseThrottle):
    """
    Rate limiting based on company subscription tier.
    Different tiers have different limits.
    
    Starter:      100 requests/hour
    Professional: 1,000 requests/hour
    Enterprise:   10,000 requests/hour (custom)
    """
    
    # Default limits per tier (requests per hour)
    TIER_LIMITS = {
        'starter': 100,
        'professional': 1000,
        'enterprise': 10000,
        'trial': 500,  # Trial tier gets 500/hour
    }
    
    def get_cache_key(self, request, view):
        """Generate cache key for throttling"""
        if request.user and request.user.is_authenticated:
            # Get company from request context
            company = getattr(request, 'company', None)
            if company:
                return f'throttle:company:{company.pk}'
        
        # Fall back to IP-based throttling for anonymous users
        if request.META.get('REMOTE_ADDR'):
            return f'throttle:ip:{request.META.get("REMOTE_ADDR")}'
        
        return None
    
    def throttle_success(self, request, view):
        """Called when throttle succeeds. Increment counter."""
        cache_key = self.get_cache_key(request, view)
        if not cache_key:
            return True
        
        # Get current count
        now = timezone.now()
        hour_key = f'{cache_key}:{now.strftime("%Y%m%d%H")}'
        
        try:
            current = cache.get(hour_key, 0)
            cache.set(hour_key, current + 1, 3600)  # Expire after 1 hour
        except Exception as e:
            logger.error(f"Error incrementing throttle counter: {e}")
        
        return True
    
    def throttle_failure(self, request, view):
        """Called when throttle fails. Check if limit exceeded."""
        cache_key = self.get_cache_key(request, view)
        if not cache_key:
            return False
        
        # Determine rate limit
        rate_limit = 100  # Default
        
        if request.user and request.user.is_authenticated:
            company = getattr(request, 'company', None)
            if company:
                # Get tier-based limit
                tier = getattr(company, 'subscription_tier', 'starter')
                rate_limit = self.TIER_LIMITS.get(tier, 100)
                
                # Also check company's max_api_calls_daily field
                if hasattr(company, 'max_api_calls_daily'):
                    # Convert daily limit to hourly (divide by 24)
                    daily_limit = company.max_api_calls_daily
                    hourly_from_daily = daily_limit // 24
                    rate_limit = min(rate_limit, hourly_from_daily)
        
        # Get current count
        now = timezone.now()
        hour_key = f'{cache_key}:{now.strftime("%Y%m%d%H")}'
        current = cache.get(hour_key, 0)
        
        if current >= rate_limit:
            self.throttle_rate = rate_limit
            return True
        
        return False
    
    def allow_request(self, request, view):
        """Check if request should be allowed"""
        cache_key = self.get_cache_key(request, view)
        if not cache_key:
            return True
        
        # Check if over limit
        if self.throttle_failure(request, view):
            return False
        
        # Update counter
        self.throttle_success(request, view)
        return True
    
    def get_rate_limit_info(self, request):
        """Get current rate limit info for response headers"""
        cache_key = self.get_cache_key(request, view=None)
        if not cache_key:
            return {}
        
        rate_limit = 100
        if request.user and request.user.is_authenticated:
            company = getattr(request, 'company', None)
            if company:
                tier = getattr(company, 'subscription_tier', 'starter')
                rate_limit = self.TIER_LIMITS.get(tier, 100)
        
        now = timezone.now()
        hour_key = f'{cache_key}:{now.strftime("%Y%m%d%H")}'
        current = cache.get(hour_key, 0)
        remaining = max(0, rate_limit - current)
        
        return {
            'limit': rate_limit,
            'remaining': remaining,
            'reset_at': (now.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)).isoformat(),
        }


class AnonymousUserThrottle(UserRateThrottle):
    """
    Rate limit for anonymous users (IP-based).
    50 requests per hour for anonymous users.
    """
    scope = 'anon'
    rate = '50/hour'
    
    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None  # Only throttle anonymous users
        
        return f'throttle:anon:{request.META.get("REMOTE_ADDR", "unknown")}'


class APILimitExceededHandler:
    """Handler to send email when API limits exceeded"""
    
    @staticmethod
    def handle_limit_exceeded(company, current_usage, limit):
        """Send notification when company hits API limit"""
        try:
            from estateApp.notifications.email_service import EmailService
            
            EmailService.send_api_limit_exceeded_email(
                company,
                current_usage=current_usage,
                limit=limit
            )
            
            logger.info(f"API limit notification sent to {company.company_name}")
            
        except Exception as e:
            logger.error(f"Failed to send API limit notification: {e}", exc_info=True)
