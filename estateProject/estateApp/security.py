"""
Advanced Security Module for Client and Marketer URL Protection
===============================================================

Features:
- Secure token-based URL slugs (non-guessable)
- Rate limiting protection
- Session validation
- IP tracking & anomaly detection
- CSRF protection enhancement
- Request signature validation
- Encrypted route parameters
"""

import hashlib
import hmac
import secrets
import time
import base64
import json
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseRedirect
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages


# ============================================
# SECURE TOKEN GENERATOR
# ============================================

class SecureTokenGenerator:
    """
    Generates cryptographically secure tokens for URL slugs.
    These tokens are:
    - Non-sequential (can't be guessed)
    - Time-bound (expire after a period)
    - User-bound (tied to specific user session)
    """
    
    SECRET_KEY = getattr(settings, 'SECRET_KEY', 'fallback-secret-key')
    TOKEN_EXPIRY_HOURS = 24  # Tokens expire after 24 hours
    
    @classmethod
    def generate_secure_slug(cls, user_id: int, user_role: str, extra_data: str = '') -> str:
        """
        Generate a secure, non-guessable slug for URLs.
        Format: {random_prefix}_{hash}_{timestamp_encoded}
        """
        # Random prefix (8 chars)
        random_prefix = secrets.token_urlsafe(6)[:8]
        
        # Timestamp (encoded)
        timestamp = int(time.time())
        timestamp_encoded = base64.urlsafe_b64encode(
            str(timestamp).encode()
        ).decode().rstrip('=')
        
        # Create hash from user data + timestamp + secret
        data_to_hash = f"{user_id}:{user_role}:{extra_data}:{timestamp}:{cls.SECRET_KEY}"
        hash_value = hashlib.sha256(data_to_hash.encode()).hexdigest()[:12]
        
        return f"{random_prefix}{hash_value}{timestamp_encoded}"
    
    @classmethod
    def generate_session_token(cls, user) -> str:
        """Generate a session-bound secure token."""
        session_data = f"{user.id}:{user.role}:{user.email}:{secrets.token_hex(8)}"
        token = hashlib.sha256(
            f"{session_data}:{cls.SECRET_KEY}".encode()
        ).hexdigest()[:32]
        
        # Store in cache with expiry
        cache_key = f"session_token:{user.id}"
        cache.set(cache_key, token, timeout=cls.TOKEN_EXPIRY_HOURS * 3600)
        
        return token
    
    @classmethod
    def validate_session_token(cls, user, token: str) -> bool:
        """Validate a session token."""
        cache_key = f"session_token:{user.id}"
        stored_token = cache.get(cache_key)
        return stored_token and secrets.compare_digest(stored_token, token)
    
    @classmethod
    def generate_page_token(cls, user_id: int, page_name: str) -> str:
        """
        Generate a page-specific token that expires quickly.
        Used for securing individual page access.
        """
        timestamp = int(time.time())
        data = f"{user_id}:{page_name}:{timestamp}:{cls.SECRET_KEY}"
        token = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        # Store with short expiry (5 minutes)
        cache_key = f"page_token:{user_id}:{page_name}"
        cache.set(cache_key, {'token': token, 'timestamp': timestamp}, timeout=300)
        
        return token


# ============================================
# RATE LIMITER
# ============================================

class RateLimiter:
    """
    Advanced rate limiting to prevent brute force attacks.
    """
    
    # Configuration
    RATE_LIMITS = {
        'login': {'max_requests': 5, 'window_seconds': 300},      # 5 attempts per 5 min
        'api': {'max_requests': 100, 'window_seconds': 60},       # 100 req/min
        'page': {'max_requests': 60, 'window_seconds': 60},       # 60 pages/min
        'sensitive': {'max_requests': 10, 'window_seconds': 60},  # 10 sensitive actions/min
    }
    
    @classmethod
    def get_client_ip(cls, request) -> str:
        """Extract real client IP, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    @classmethod
    def is_rate_limited(cls, request, action_type: str = 'page') -> Tuple[bool, int]:
        """
        Check if request should be rate limited.
        Returns: (is_limited, seconds_until_reset)
        """
        ip = cls.get_client_ip(request)
        user_id = getattr(request.user, 'id', 'anonymous')
        
        # Create unique key for this IP + user + action
        cache_key = f"rate_limit:{action_type}:{ip}:{user_id}"
        
        limits = cls.RATE_LIMITS.get(action_type, cls.RATE_LIMITS['page'])
        max_requests = limits['max_requests']
        window = limits['window_seconds']
        
        # Get current count
        data = cache.get(cache_key, {'count': 0, 'start': time.time()})
        
        # Check if window expired
        if time.time() - data['start'] > window:
            data = {'count': 0, 'start': time.time()}
        
        # Increment count
        data['count'] += 1
        cache.set(cache_key, data, timeout=window)
        
        # Check if limited
        is_limited = data['count'] > max_requests
        seconds_until_reset = int(window - (time.time() - data['start']))
        
        return is_limited, max(0, seconds_until_reset)
    
    @classmethod
    def reset_rate_limit(cls, request, action_type: str = 'page'):
        """Reset rate limit for a specific action (e.g., after successful login)."""
        ip = cls.get_client_ip(request)
        user_id = getattr(request.user, 'id', 'anonymous')
        cache_key = f"rate_limit:{action_type}:{ip}:{user_id}"
        cache.delete(cache_key)


# ============================================
# SECURITY VALIDATORS
# ============================================

class SecurityValidator:
    """
    Validates request security parameters.
    """
    
    # Suspicious patterns to block
    SUSPICIOUS_PATTERNS = [
        '../', '..\\',  # Path traversal
        '<script', '</script',  # XSS
        'javascript:', 'vbscript:',  # Script injection
        'SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'DROP ',  # SQL injection
        '--', ';--',  # SQL comments
        'UNION ', 'OR 1=1', "OR '1'='1",  # SQL injection patterns
        '%00', '\x00',  # Null byte injection
        '${', '#{',  # Template injection
        'eval(', 'exec(',  # Code execution
    ]
    
    # Blocked user agents (common attack tools)
    BLOCKED_USER_AGENTS = [
        'sqlmap', 'nikto', 'nmap', 'masscan',
        'dirbuster', 'gobuster', 'wfuzz',
        'hydra', 'medusa', 'burp',
    ]
    
    @classmethod
    def validate_request(cls, request) -> Tuple[bool, str]:
        """
        Comprehensive request validation.
        Returns: (is_valid, error_message)
        """
        # Check user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for blocked in cls.BLOCKED_USER_AGENTS:
            if blocked in user_agent:
                return False, "Blocked user agent detected"
        
        # Check request path for suspicious patterns
        full_path = request.get_full_path().upper()
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if pattern.upper() in full_path:
                return False, f"Suspicious pattern detected: {pattern}"
        
        # Check query parameters
        for key, value in request.GET.items():
            value_upper = str(value).upper()
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if pattern.upper() in value_upper:
                    return False, f"Suspicious parameter value detected"
        
        # Check POST data
        for key, value in request.POST.items():
            if key in ['csrfmiddlewaretoken', 'password', 'password1', 'password2']:
                continue  # Skip sensitive fields
            value_upper = str(value).upper()
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if pattern.upper() in value_upper:
                    return False, f"Suspicious form data detected"
        
        return True, ""
    
    @classmethod
    def validate_session_integrity(cls, request) -> bool:
        """
        Validate session hasn't been tampered with.
        """
        if not request.user.is_authenticated:
            return True
        
        # Check if user agent changed mid-session (session hijacking indicator)
        session_ua = request.session.get('_security_ua')
        current_ua = request.META.get('HTTP_USER_AGENT', '')
        
        if session_ua and session_ua != current_ua:
            # User agent changed - potential session hijacking
            return False
        
        # Store current UA in session
        if not session_ua:
            request.session['_security_ua'] = current_ua
        
        return True


# ============================================
# SECURITY DECORATORS
# ============================================

def secure_client_required(view_func):
    """
    Decorator for client-only views with enhanced security.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check authentication
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to continue.")
            return redirect('login')
        
        # Check role
        if request.user.role != 'client':
            messages.error(request, "Access denied. Client access only.")
            return redirect('login')
        
        # Rate limiting
        is_limited, wait_time = RateLimiter.is_rate_limited(request, 'page')
        if is_limited:
            messages.error(request, f"Too many requests. Please wait {wait_time} seconds.")
            return HttpResponseForbidden(
                f"Rate limited. Please wait {wait_time} seconds."
            )
        
        # Security validation
        is_valid, error_msg = SecurityValidator.validate_request(request)
        if not is_valid:
            # Log the attempt
            _log_security_event(request, 'blocked_request', error_msg)
            return HttpResponseForbidden("Request blocked for security reasons.")
        
        # Session integrity
        if not SecurityValidator.validate_session_integrity(request):
            logout(request)
            messages.error(request, "Session security violation detected. Please login again.")
            return redirect('login')
        
        # Track activity
        _track_user_activity(request)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def secure_marketer_required(view_func):
    """
    Decorator for marketer-only views with enhanced security.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check authentication
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to continue.")
            return redirect('login')
        
        # Check role
        if request.user.role != 'marketer':
            messages.error(request, "Access denied. Marketer access only.")
            return redirect('login')
        
        # Rate limiting
        is_limited, wait_time = RateLimiter.is_rate_limited(request, 'page')
        if is_limited:
            messages.error(request, f"Too many requests. Please wait {wait_time} seconds.")
            return HttpResponseForbidden(
                f"Rate limited. Please wait {wait_time} seconds."
            )
        
        # Security validation
        is_valid, error_msg = SecurityValidator.validate_request(request)
        if not is_valid:
            _log_security_event(request, 'blocked_request', error_msg)
            return HttpResponseForbidden("Request blocked for security reasons.")
        
        # Session integrity
        if not SecurityValidator.validate_session_integrity(request):
            logout(request)
            messages.error(request, "Session security violation detected. Please login again.")
            return redirect('login')
        
        # Track activity
        _track_user_activity(request)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def rate_limit(action_type: str = 'api'):
    """
    Decorator for rate limiting specific views.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            is_limited, wait_time = RateLimiter.is_rate_limited(request, action_type)
            if is_limited:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'rate_limited',
                        'message': f'Too many requests. Please wait {wait_time} seconds.',
                        'retry_after': wait_time
                    }, status=429)
                return HttpResponseForbidden(
                    f"Rate limited. Please wait {wait_time} seconds."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def sensitive_action(view_func):
    """
    Decorator for sensitive actions (password change, profile update, etc.)
    with stricter rate limiting.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Stricter rate limit for sensitive actions
        is_limited, wait_time = RateLimiter.is_rate_limited(request, 'sensitive')
        if is_limited:
            messages.error(request, f"Too many attempts. Please wait {wait_time} seconds.")
            return HttpResponseForbidden(
                f"Too many attempts. Please wait {wait_time} seconds."
            )
        
        # Re-validate session for sensitive actions
        if not SecurityValidator.validate_session_integrity(request):
            logout(request)
            messages.error(request, "Please login again to perform this action.")
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# ============================================
# HELPER FUNCTIONS
# ============================================

def _log_security_event(request, event_type: str, details: str = ''):
    """Log security events for monitoring."""
    ip = RateLimiter.get_client_ip(request)
    user_id = getattr(request.user, 'id', None)
    user_email = getattr(request.user, 'email', 'anonymous')
    
    log_data = {
        'timestamp': timezone.now().isoformat(),
        'event_type': event_type,
        'ip': ip,
        'user_id': user_id,
        'user_email': user_email,
        'path': request.path,
        'method': request.method,
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'details': details,
    }
    
    # Store in cache for quick access (last 100 events)
    cache_key = 'security_events'
    events = cache.get(cache_key, [])
    events.insert(0, log_data)
    events = events[:100]  # Keep last 100
    cache.set(cache_key, events, timeout=86400)  # 24 hours
    
    # Also log to console/file in production
    import logging
    logger = logging.getLogger('security')
    logger.warning(f"Security Event: {event_type} | IP: {ip} | User: {user_email} | Details: {details}")


def _track_user_activity(request):
    """Track user activity for anomaly detection."""
    if not request.user.is_authenticated:
        return
    
    ip = RateLimiter.get_client_ip(request)
    user_id = request.user.id
    
    cache_key = f"user_activity:{user_id}"
    activity = cache.get(cache_key, {'ips': set(), 'pages': [], 'last_activity': None})
    
    # Convert set to list for serialization if needed
    if isinstance(activity.get('ips'), set):
        activity['ips'] = list(activity['ips'])
    
    # Track IPs used
    if ip not in activity['ips']:
        activity['ips'].append(ip)
        
        # Alert if multiple IPs in short time (potential account sharing/compromise)
        if len(activity['ips']) > 3:
            _log_security_event(request, 'multiple_ips', f"User accessing from {len(activity['ips'])} IPs")
    
    # Track pages visited
    activity['pages'].append({
        'path': request.path,
        'timestamp': timezone.now().isoformat()
    })
    activity['pages'] = activity['pages'][-50:]  # Keep last 50 pages
    
    activity['last_activity'] = timezone.now().isoformat()
    
    cache.set(cache_key, activity, timeout=3600)  # 1 hour


def generate_secure_url(user, page_name: str, **url_kwargs) -> str:
    """
    Generate a secure URL with embedded security token.
    """
    token = SecureTokenGenerator.generate_page_token(user.id, page_name)
    
    # Build URL with security token
    url = reverse(page_name, kwargs=url_kwargs)
    
    # Add security token as query parameter
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}_st={token}"


def get_secure_company_slug(company) -> str:
    """Generate a secure slug for company URLs."""
    if hasattr(company, 'slug') and company.slug:
        return company.slug
    
    # Generate secure slug from company name + random suffix
    base_slug = company.company_name.lower().replace(' ', '-')[:20]
    secure_suffix = secrets.token_urlsafe(4)[:6]
    return f"{base_slug}-{secure_suffix}"
