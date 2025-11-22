"""
Advanced Security Middleware for SuperAdmin
Provides rate limiting, IP whitelisting, and security headers
"""
import time
import ipaddress
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from .models import SystemAuditLog


class SuperAdminRateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting for super admin login attempts
    Prevents brute force attacks
    """
    
    def process_request(self, request):
        # Only apply to super admin login
        if not request.path.startswith('/super-admin/') or 'login' not in request.path:
            return None
        
        if request.method != 'POST':
            return None
        
        ip_address = self.get_client_ip(request)
        cache_key = f'superadmin_login_attempts_{ip_address}'
        lockout_key = f'superadmin_lockout_{ip_address}'
        
        # Check if IP is locked out
        if cache.get(lockout_key):
            lockout_until = cache.get(lockout_key)
            remaining = int(lockout_until - time.time())
            
            # Log lockout attempt
            try:
                SystemAuditLog.objects.create(
                    user=None,
                    action='LOGIN_BLOCKED',
                    resource='platform_admin_login',
                    status='FAILED',
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'reason': 'Rate limit exceeded',
                        'remaining_seconds': remaining
                    }
                )
            except Exception:
                pass
            
            return render(request, 'superAdmin/rate_limited.html', {
                'remaining_minutes': remaining // 60,
                'remaining_seconds': remaining % 60
            }, status=429)
        
        # Get current attempts
        attempts = cache.get(cache_key, [])
        current_time = time.time()
        
        # Remove old attempts outside the window
        window = getattr(settings, 'SECURITY_RATE_LIMIT_LOGIN_WINDOW', 300)
        attempts = [t for t in attempts if current_time - t < window]
        
        # Check if exceeded limit
        max_attempts = getattr(settings, 'SECURITY_RATE_LIMIT_LOGIN_ATTEMPTS', 5)
        if len(attempts) >= max_attempts:
            # Lock out the IP
            lockout_duration = getattr(settings, 'SECURITY_RATE_LIMIT_LOCKOUT_DURATION', 900)
            cache.set(lockout_key, current_time + lockout_duration, lockout_duration)
            
            # Log lockout
            try:
                SystemAuditLog.objects.create(
                    user=None,
                    action='IP_LOCKED_OUT',
                    resource='platform_admin_login',
                    status='FAILED',
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'reason': 'Too many failed login attempts',
                        'attempts': len(attempts),
                        'lockout_duration': lockout_duration
                    }
                )
            except Exception:
                pass
            
            return render(request, 'superAdmin/rate_limited.html', {
                'remaining_minutes': lockout_duration // 60,
                'remaining_seconds': lockout_duration % 60
            }, status=429)
        
        # Add current attempt
        attempts.append(current_time)
        cache.set(cache_key, attempts, window)
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Extract real client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SuperAdminIPWhitelistMiddleware(MiddlewareMixin):
    """
    IP Whitelisting for super admin access
    Only allows access from specified IP addresses/ranges
    """
    
    def process_request(self, request):
        # Only apply to super admin routes
        if not request.path.startswith('/super-admin/'):
            return None
        
        # Skip if no whitelist configured
        whitelist = getattr(settings, 'SUPERADMIN_IP_WHITELIST', [])
        if not whitelist:
            return None
        
        client_ip = self.get_client_ip(request)
        
        # Check if IP is whitelisted
        if not self.is_ip_whitelisted(client_ip, whitelist):
            # Log blocked access
            try:
                SystemAuditLog.objects.create(
                    user=None,
                    action='IP_BLOCKED',
                    resource='platform_admin_access',
                    status='FAILED',
                    ip_address=client_ip,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    details={
                        'reason': 'IP not in whitelist',
                        'path': request.path
                    }
                )
            except Exception:
                pass
            
            return render(request, 'superAdmin/ip_blocked.html', status=403)
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Extract real client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def is_ip_whitelisted(client_ip, whitelist):
        """Check if IP is in whitelist (supports CIDR notation)"""
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            
            for allowed in whitelist:
                try:
                    # Check if it's a network range (CIDR)
                    if '/' in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client_ip_obj in network:
                            return True
                    else:
                        # Single IP address
                        if client_ip_obj == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    continue
            
            return False
        except ValueError:
            return False


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all super admin responses
    """
    
    def process_response(self, request, response):
        # Only apply to super admin routes
        if not request.path.startswith('/super-admin/'):
            return response
        
        # Security headers
        response['X-Frame-Options'] = 'DENY'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        return response
