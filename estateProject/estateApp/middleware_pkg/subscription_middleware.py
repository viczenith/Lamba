"""
SubscriptionValidationMiddleware - Enforces subscription status and access controls
Handles read-only mode, grace periods, and trial expiry access restrictions
"""

import logging
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class SubscriptionValidationMiddleware:
    """
    Middleware to enforce subscription status and access controls
    
    Rules:
    1. Trial active (< 14 days): Full access
    2. Trial expired: Redirect to upgrade page (except for /login, /logout, /upgrade)
    3. Grace period active: Read-only mode + rate limiting
    4. Grace period expired: Read-only mode enforced, schedule data deletion
    5. Read-only mode: Prevent write operations
    """
    
    # Paths that bypass subscription checks
    PUBLIC_PATHS = [
        '/login/',
        '/logout/',
        '/upgrade/',
        '/pricing/',
        '/contact/',
        '/api/auth/',
        '/trial-expired/',
        '/account-suspended/',
        '/api/subscription/',
        '/billing/',
        '/api/billing/',
        '/tenant-admin/login/',
        '/tenant-admin/logout/',
        '/admin/login/',
    ]
    
    # Paths that should enforce read-only check
    PROTECTED_PATHS = [
        '/admin_dashboard/',
        '/admin-dashboard/',
        '/api/',
        '/estate/',
        '/client/',
        '/agent/',
        '/allocation/',
    ]
    
    # Write operations that require full access (not read-only)
    WRITE_OPERATIONS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip subscription validation for non-authenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Get company from request
        company = getattr(request, 'company', None)
        if not company:
            return self.get_response(request)
        
        # Check if path requires subscription validation
        if self._should_validate_path(request.path):
            # Check trial expiry
            if not self._validate_trial_status(request, company):
                return self._redirect_trial_expired(request)
            
            # Check read-only mode for write operations
            if request.method in self.WRITE_OPERATIONS:
                if not self._validate_write_access(request, company):
                    return self._reject_read_only(request)
        
        # Add subscription context to request
        request.subscription_status = company.subscription_status
        request.is_read_only_mode = company.is_read_only_mode
        
        response = self.get_response(request)
        return response
    
    def _should_validate_path(self, path):
        """Check if path requires subscription validation"""
        # Skip public paths
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                return False
        
        # Check if path is protected
        for protected_path in self.PROTECTED_PATHS:
            if path.startswith(protected_path):
                return True
        
        return False
    
    def _validate_trial_status(self, request, company):
        """Validate trial hasn't expired"""
        # If subscription is active or trial is still valid, allow access
        if company.subscription_status == 'active':
            if company.subscription_ends_at > timezone.now():
                return True
        
        elif company.subscription_status == 'trial':
            if company.trial_ends_at and company.trial_ends_at > timezone.now():
                return True
        
        # Trial has expired or no active subscription
        return False
    
    def _validate_write_access(self, request, company):
        """Validate write access (not in read-only mode)"""
        # Allow reads even in read-only mode
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Reject write operations if in read-only mode
        if company.is_read_only_mode:
            logger.warning(f"Write operation rejected for {company.company_name} - read-only mode active")
            return False
        
        return True
    
    def _redirect_trial_expired(self, request):
        """Redirect to trial expired page"""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Trial expired',
                'detail': 'Your trial has expired. Please upgrade to continue.',
                'code': 'TRIAL_EXPIRED'
            }, status=402)
        else:
            return redirect('trial_expired')
    
    def _reject_read_only(self, request):
        """Reject write operation in read-only mode"""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Read-only mode',
                'detail': 'Your account is in read-only mode. Please upgrade to make changes.',
                'code': 'READ_ONLY_MODE'
            }, status=403)
        else:
            from django.contrib import messages
            messages.error(request, 'Your account is in read-only mode. Please upgrade to make changes.')
            return redirect('admin_dashboard')


class SubscriptionRateLimitMiddleware:
    """
    Rate limiting middleware based on subscription tier during grace period
    
    Grace period (days 15-17): 10% of normal rate limit
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        company = getattr(request, 'company', None)
        
        if company and company.grace_period_ends_at:
            # During grace period, apply stricter rate limiting
            if company.grace_period_ends_at > timezone.now():
                # Mark request for rate limiter
                request.grace_period_active = True
                request.rate_limit_multiplier = 0.1  # 10% of normal limit
        
        response = self.get_response(request)
        return response
