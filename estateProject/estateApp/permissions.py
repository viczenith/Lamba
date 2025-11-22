"""
Advanced permission classes for multi-tenant API.
Includes subscription-based access control and feature gates.
"""
import logging
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class IsAuthenticated(BasePermission):
    """Only authenticated users can access"""
    message = "You must be authenticated to access this resource."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsCompanyOwnerOrAdmin(BasePermission):
    """
    User must be the company owner or an admin.
    """
    message = "You do not have permission to access this company."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        company = getattr(request, 'company', None)
        if not company:
            return False
        
        # Check if user is owner
        return request.user == company.created_by or request.user.is_staff


class IsCompanyMember(BasePermission):
    """User must be a member of the company"""
    message = "You are not a member of this company."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        company = getattr(request, 'company', None)
        if not company:
            return False
        
        # Check if user is in company members
        if hasattr(company, 'members'):
            return request.user in company.members.all()
        
        return False


class SubscriptionRequiredPermission(BasePermission):
    """
    Verify subscription is active before allowing access.
    """
    message = "Your subscription is not active. Please upgrade or renew your subscription."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        company = getattr(request, 'company', None)
        if not company:
            return False
        
        # Check subscription status
        if not hasattr(company, 'subscription_status'):
            return True  # No subscription field, allow access
        
        status = company.subscription_status
        if status not in ['active', 'trial']:
            return False
        
        # Check if trial is expired
        if status == 'trial' and hasattr(company, 'trial_end_date'):
            if company.trial_end_date < timezone.now():
                return False
        
        return True


class FeatureAccessPermission(BasePermission):
    """
    Check if user's subscription tier has access to specific feature.
    """
    message = "Your subscription tier does not have access to this feature."
    
    # Map features to minimum tier required
    FEATURE_TIERS = {
        'advanced_analytics': 'professional',
        'api_access': 'professional',
        'custom_branding': 'professional',
        'bulk_operations': 'professional',
        'automation': 'enterprise',
        'sso': 'enterprise',
        'advanced_reporting': 'enterprise',
        'white_label': 'enterprise',
    }
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        company = getattr(request, 'company', None)
        if not company:
            return False
        
        # Get required feature from view
        required_feature = getattr(view, 'required_feature', None)
        if not required_feature:
            return True  # No feature check needed
        
        # Get company tier
        tier = getattr(company, 'subscription_tier', 'starter')
        min_tier_required = self.FEATURE_TIERS.get(required_feature, 'starter')
        
        # Tier hierarchy
        tier_hierarchy = ['starter', 'professional', 'enterprise']
        
        company_tier_index = tier_hierarchy.index(tier) if tier in tier_hierarchy else 0
        required_tier_index = tier_hierarchy.index(min_tier_required)
        
        return company_tier_index >= required_tier_index


class RateLimitedActionPermission(BasePermission):
    """
    Check if user has exceeded daily action limits (e.g., emails sent, SMS sent).
    """
    message = "You have exceeded the daily limit for this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True  # Only enforce on authenticated requests
        
        company = getattr(request, 'company', None)
        if not request.method in ['POST', 'PUT', 'DELETE']:
            return True  # Only check on write operations
        
        # This would be implemented based on specific action tracking
        return True


class APIKeyPermission(BasePermission):
    """
    Check if API key is valid and not revoked.
    """
    message = "Invalid or expired API key."
    
    def has_permission(self, request, view):
        # API key authentication handled by authentication class
        return True
    
    def has_object_permission(self, request, view, obj):
        company = getattr(request, 'company', None)
        if not company:
            return False
        
        # Check if object belongs to company
        if hasattr(obj, 'company'):
            return obj.company == company
        
        return False


class ReadOnlyPermission(BasePermission):
    """Allow only read operations (GET, HEAD, OPTIONS)"""
    
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Allow owner to edit, others can only read.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in SAFE_METHODS:
            return True
        
        # Write permissions only for owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class SubscriptionTierPermission(BasePermission):
    """
    Advanced permission based on subscription tier with custom limits.
    """
    message = "Your subscription plan does not allow this action."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return request.method in SAFE_METHODS
        
        company = getattr(request, 'company', None)
        if not company:
            return False
        
        # Get tier from company
        tier = getattr(company, 'subscription_tier', 'starter')
        
        # Check view's tier requirements
        required_tier = getattr(view, 'required_tier', None)
        if required_tier:
            tier_hierarchy = {
                'starter': 0,
                'trial': 1,
                'professional': 2,
                'enterprise': 3,
            }
            
            user_tier_level = tier_hierarchy.get(tier, 0)
            required_level = tier_hierarchy.get(required_tier, 0)
            
            if user_tier_level < required_level:
                return False
        
        # Check API call limits
        if request.method not in SAFE_METHODS:
            if hasattr(company, 'check_api_limit'):
                return company.check_api_limit()
        
        return True


class TenantIsolationPermission(BasePermission):
    """
    Ensure strict tenant isolation - users can only access their own tenant's data.
    """
    message = "You do not have access to this tenant's data."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user's company (tenant)
        user_company = getattr(request, 'company', None)
        if not user_company:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        user_company = getattr(request, 'company', None)
        
        # Check if object's company matches user's company
        obj_company = getattr(obj, 'company', None)
        if obj_company:
            return obj_company == user_company
        
        # Check by owner's company
        if hasattr(obj, 'created_by') and hasattr(obj.created_by, 'company'):
            return obj.created_by.company == user_company
        
        return False
