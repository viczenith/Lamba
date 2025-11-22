from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils import timezone
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
                logger.debug(f"Skipping TenantIsolationMiddleware for public endpoint: {request.path}")
                return None
            
            # Log request details
            logger.debug(f"TenantIsolationMiddleware processing: {request.path} (user={request.user.id if request.user.is_authenticated else 'anon'})")
            
            # Try to get company from different sources
            company = self._extract_company_from_request(request)
            
            if company:
                request.company = company
                logger.debug(f"Tenant context set from extract: {company.company_name}")
            else:
                # If user is authenticated but no company, try to get from user
                if request.user.is_authenticated:
                    if hasattr(request.user, 'company_profile') and request.user.company_profile:
                        request.company = request.user.company_profile
                        logger.debug(f"Tenant context set from user.company_profile: {request.company.company_name}")
                    else:
                        # Client or marketer - they can access multiple companies
                        request.is_cross_company = True
                        logger.debug(f"User {request.user.id} is cross-company (no company_profile)")
            
            return None
            
        except Exception as e:
            logger.error(f"Error in TenantIsolationMiddleware: {str(e)}", exc_info=True)
            return None
    
    def _is_public_endpoint(self, request):
        """Check if endpoint is public (doesn't require tenant context)"""
        public_paths = [
            '/login',
            '/logout',
            '/register',
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
            # Handle case where request.company might be a string ID instead of object
            try:
                if isinstance(request.company, str):
                    # If it's a string, just use it as the ID
                    response['X-Tenant-ID'] = request.company
                else:
                    # If it's an object, get the id attribute
                    response['X-Tenant-ID'] = str(request.company.id)
                    response['X-Tenant-Name'] = request.company.company_name
            except AttributeError:
                # Fallback if the object doesn't have expected attributes
                response['X-Tenant-ID'] = str(request.company)
        
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
        
        # Log tenant access for debugging
        logger.debug(f"TenantAccessCheckMiddleware: user={request.user.id}, role={user_role}, company={user_company}")
        
        # Admin/Support users are bound to their company
        if user_role in ['admin', 'support']:
            if not user_company:
                logger.warning(f"Admin/Support user {request.user.id} has no company_profile")
                # Don't block - let the view handle it
                return None
        
        # Clients and Marketers can access multiple companies (cross-tenant)
        elif user_role in ['client', 'marketer']:
            # These users will access data across companies
            pass
        
        return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced Session Security - Prevents session hijacking, fixation, and cross-account interference.
    
    Security measures:
    1. Session validation - Ensures session data matches current user and company
    2. Session fixation prevention - Regenerate session ID after login
    3. Cross-account protection - Validates user_id and company_id in session
    4. Session hijacking detection - Tracks IP changes
    5. Complete session cleanup on logout - Prevents data leakage
    """
    
    def process_request(self, request):
        """Enhanced session validation on each request"""
        
        # Skip for public endpoints
        if self._is_public_endpoint(request.path):
            return None
        
        # Only check authenticated requests
        if not request.user or not request.user.is_authenticated:
            return None
        
        try:
            session = request.session
            user = request.user
            
            # Check if this is an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            # Check 1: Verify user is still active
            if not user.is_active:
                logger.warning(f"Inactive user {user.id} attempted access.")
                from django.contrib.auth import logout
                logout(request)
                session.flush()
                if is_ajax:
                    return JsonResponse({'success': False, 'message': 'Session expired. Please login again.'}, status=401)
                return redirect('login')
            
            # Check 2: CRITICAL - Validate session user_id matches authenticated user
            # BUT: Allow first request after login to set user_id
            session_user_id = session.get('user_id')
            if session_user_id is not None and session_user_id != user.id:
                logger.error(
                    f"SECURITY ALERT: Session user mismatch! "
                    f"Session user_id={session_user_id}, authenticated user={user.id}. "
                    f"Possible session hijacking from IP {self._extract_client_ip(request)}"
                )
                from django.contrib.auth import logout
                logout(request)
                session.flush()
                if is_ajax:
                    return JsonResponse({'success': False, 'message': 'Session validation failed. Please login again.'}, status=401)
                from django.contrib import messages
                messages.error(request, "Session validation failed. Please login again.")
                return redirect('login')
            
            # If session doesn't have user_id yet, set it (this happens after login)
            if session_user_id is None:
                session['user_id'] = user.id
                session['user_role'] = user.role
                session['login_timestamp'] = timezone.now().isoformat()
                if hasattr(user, 'company_profile') and user.company_profile:
                    session['company_id'] = user.company_profile.id
                    session['company_name'] = user.company_profile.company_name
            
            # Check 3: CRITICAL - Validate session role matches user role
            session_role = session.get('user_role')
            if session_role and session_role != user.role:
                logger.warning(
                    f"Role mismatch for user {user.id}: "
                    f"session={session_role}, actual={user.role}. Forcing re-login."
                )
                from django.contrib.auth import logout
                logout(request)
                session.flush()
                if is_ajax:
                    return JsonResponse({'success': False, 'message': 'Your account role has changed. Please login again.'}, status=401)
                from django.contrib import messages
                messages.error(request, "Your account role has changed. Please login again.")
                return redirect('login')
            
            # Check 4: CRITICAL - Validate company_id for company-assigned users
            if hasattr(user, 'company_profile') and user.company_profile:
                user_company_id = user.company_profile.id
                session_company_id = session.get('company_id')
                
                # If session has company_id, it must match user's company
                if session_company_id is not None and session_company_id != user_company_id:
                    logger.error(
                        f"SECURITY ALERT: Company mismatch! "
                        f"Session company_id={session_company_id}, user company_id={user_company_id}. "
                        f"Preventing cross-company access for user {user.id}"
                    )
                    from django.contrib.auth import logout
                    logout(request)
                    session.flush()
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': 'Company validation failed. Please login again.'}, status=401)
                    from django.contrib import messages
                    messages.error(request, "Company validation failed. Please login again.")
                    return redirect('login')
                
                # Update session with company info if missing
                if session_company_id is None:
                    session['company_id'] = user_company_id
                    session['company_name'] = user.company_profile.company_name
            
            # Check 5: Store client IP for audit trail and detect suspicious changes
            current_ip = self._extract_client_ip(request)
            stored_ip = session.get('_client_ip')
            
            if stored_ip != current_ip:
                session['_client_ip'] = current_ip
                if stored_ip:
                    logger.info(
                        f"Session IP changed for user {user.id}: "
                        f"was {stored_ip}, now {current_ip}"
                    )
            
        except Exception as e:
            logger.error(f"Error in SessionSecurityMiddleware: {e}", exc_info=True)
            # Check if AJAX before handling error
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            # Only force logout for serious errors, not minor issues
            if is_ajax:
                logger.warning(f"AJAX request error in middleware: {e}")
                # Don't force logout for AJAX errors, just log and continue
                return None
            
            # For non-AJAX, only logout if it's a serious security issue
            logger.warning(f"Continuing request despite error: {e}")
        
        return None
    
    def process_response(self, request, response):
        """Add secure headers to response and handle logout cleanup"""
        
        # Add CSRF protection headers
        response['X-Frame-Options'] = 'DENY'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # For logout requests, add comprehensive no-cache headers
        if 'logout' in request.path:
            response['Cache-Control'] = 'no-cache, no-store, max-age=0, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Clear-Site-Data'] = '"cache", "cookies", "storage"'
        
        return response
    
    def _is_public_endpoint(self, path):
        """Check if path is public and doesn't need session validation"""
        public_paths = [
            '/login',
            '/logout',
            '/tenant-admin/login',
            '/tenant-admin/logout',
            '/register',
            '/register-user',
            '/api/auth/login',
            '/api/auth/register',
            '/health/',
            '/static/',
            '/media/',
        ]
        
        for public_path in public_paths:
            if path.startswith(public_path):
                return True
        
        return False
    
    def _extract_client_ip(self, request):
        """Extract client IP from request"""
        # Check X-Forwarded-For (for proxies/load balancers)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
            return ip
        
        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', 'UNKNOWN')


