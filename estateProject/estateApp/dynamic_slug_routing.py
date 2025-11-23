from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, Http404
from django.utils.decorators import wraps
from django.contrib.auth import get_user_model
from .models import Company
import logging
import hashlib
import hmac
import time

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================================
# 1. SLUG VALIDATION & VERIFICATION
# ============================================================================

class SlugValidator:
    """Validates and secures company slugs"""
    
    # Reserved slugs that cannot be used
    RESERVED_SLUGS = {
        'admin', 'api', 'auth', 'login', 'logout', 'register',
        'dashboard', 'settings', 'profile', 'static', 'media',
        'help', 'support', 'contact', 'about', 'pricing',
        'super-admin', 'sys', 'system', 'root', 'django',
        'admin-dashboard', 'user-registration', 'password-reset',
        'client', 'marketer', 'estate', 'plot', 'transaction',
        'payment', 'notification', 'chat', 'message', 'allocation',
        'promotion', 'promo', 'ws', 'websocket', 'socket',
    }
    
    @staticmethod
    def is_valid(slug):
        """
        Validate slug format and security
        
        Rules:
        - 3-50 characters
        - Lowercase alphanumeric and hyphens only
        - Cannot start/end with hyphen
        - Not in reserved list
        - No consecutive hyphens
        """
        if not slug:
            return False
        
        # Check length
        if len(slug) < 3 or len(slug) > 50:
            return False
        
        # Check format
        if not slug.replace('-', '').isalnum() or slug != slug.lower():
            return False
        
        # Check start/end
        if slug.startswith('-') or slug.endswith('-'):
            return False
        
        # Check consecutive hyphens
        if '--' in slug:
            return False
        
        # Check reserved
        if slug in SlugValidator.RESERVED_SLUGS:
            return False
        
        return True
    
    @staticmethod
    def generate_from_company_name(company_name):
        """
        Generate a valid slug from company name
        
        Example: "Victor Godwin Ventures" -> "victor-godwin-ventures"
        """
        import re
        # Convert to lowercase
        slug = company_name.lower()
        # Remove special characters, keep only alphanumeric and spaces
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Replace spaces and multiple hyphens with single hyphen
        slug = re.sub(r'[\s-]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        if SlugValidator.is_valid(slug):
            return slug
        
        # If not valid, add random suffix
        import random
        suffix = random.randint(1000, 9999)
        return f"{slug}-{suffix}"[:50]


# ============================================================================
# 2. COMPANY CONTEXT INJECTION
# ============================================================================

class CompanySlugContextMiddleware:
    """
    Middleware to inject company context from slug into request
    
    Usage:
    - Add to MIDDLEWARE in settings.py
    - Must come after AuthenticationMiddleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract slug from URL path
        slug = self.extract_slug_from_path(request.path)
        
        if slug and SlugValidator.is_valid(slug):
            try:
                company = Company.objects.get(slug=slug)
                request.company = company
                request.company_slug = slug
                # Store in session for backup
                if request.user.is_authenticated:
                    request.session['current_company_slug'] = slug
            except Company.DoesNotExist:
                # Slug doesn't exist, will be handled by view
                request.company = None
                request.company_slug = slug
        else:
            # Get from user's assigned company if authenticated
            if request.user.is_authenticated:
                try:
                    company = request.user.company
                    request.company = company
                    request.company_slug = company.slug
                except (AttributeError, Company.DoesNotExist):
                    request.company = None
                    request.company_slug = None
            else:
                request.company = None
                request.company_slug = None
        
        response = self.get_response(request)
        return response
    
    @staticmethod
    def extract_slug_from_path(path):
        """Extract slug from URL path (first segment after /)"""
        parts = path.strip('/').split('/')
        if parts and parts[0]:
            potential_slug = parts[0]
            # Validate format
            if 3 <= len(potential_slug) <= 50 and '-' in potential_slug:
                return potential_slug
        return None


# ============================================================================
# 3. DECORATORS FOR SLUG-BASED ACCESS CONTROL
# ============================================================================

def company_slug_required(view_func):
    """
    Decorator: Requires valid company slug and user access
    
    Usage:
        @company_slug_required
        def my_view(request, company_slug, ...):
    """
    @wraps(view_func)
    def wrapper(request, company_slug=None, *args, **kwargs):
        # Validate slug format
        if not company_slug or not SlugValidator.is_valid(company_slug):
            logger.warning(f"Invalid slug attempted: {company_slug} by {request.user}")
            raise Http404("Company not found")
        
        # Get company
        try:
            company = Company.objects.get(slug=company_slug)
        except Company.DoesNotExist:
            logger.warning(f"Company slug not found: {company_slug}")
            raise Http404("Company not found")
        
        # Check user access
        if not request.user.is_authenticated:
            return redirect(f'/{company_slug}/login/')
        
        # Verify user belongs to this company
        if not user_has_company_access(request.user, company):
            logger.warning(
                f"Unauthorized access attempt: {request.user} "
                f"tried to access {company_slug}"
            )
            return HttpResponseForbidden("You don't have access to this company")
        
        # Attach company to request
        request.company = company
        request.company_slug = company_slug
        
        return view_func(request, company_slug, *args, **kwargs)
    
    return wrapper


def company_slug_context(view_func):
    """
    Decorator: Injects company context without requiring access
    Useful for mixed-access views (login pages, etc)
    
    Usage:
        @company_slug_context
        def my_view(request, company_slug=None, ...):
    """
    @wraps(view_func)
    def wrapper(request, company_slug=None, *args, **kwargs):
        if company_slug and SlugValidator.is_valid(company_slug):
            try:
                company = Company.objects.get(slug=company_slug)
                request.company = company
                request.company_slug = company_slug
            except Company.DoesNotExist:
                request.company = None
                request.company_slug = company_slug
        
        return view_func(request, company_slug, *args, **kwargs)
    
    return wrapper


def secure_company_slug(view_func):
    """
    Decorator: Maximum security - validates at multiple levels
    Includes signature verification and rate limiting
    
    Usage:
        @secure_company_slug
        def my_view(request, company_slug, ...):
    """
    @wraps(view_func)
    def wrapper(request, company_slug=None, *args, **kwargs):
        # Level 1: Format validation
        if not company_slug or not SlugValidator.is_valid(company_slug):
            logger.warning(f"Invalid slug format: {company_slug}")
            raise Http404()
        
        # Level 2: Company existence
        try:
            company = Company.objects.select_related('subscription_billing').get(slug=company_slug)
        except Company.DoesNotExist:
            logger.warning(f"Company not found: {company_slug}")
            raise Http404()
        
        # Level 3: User authentication
        if not request.user.is_authenticated:
            return redirect(f'/{company_slug}/login/')
        
        # Level 4: Company access verification
        if not user_has_company_access(request.user, company):
            log_unauthorized_access(request.user, company, request)
            raise Http404()
        
        # Level 5: Subscription status check
        from .decorators import check_subscription_active
        subscription_valid = check_subscription_active(company)
        if not subscription_valid and not request.user.is_superuser:
            return redirect(f'/{company_slug}/subscription-required/')
        
        # Level 6: Rate limiting (optional)
        if not check_rate_limit(request.user, company):
            logger.warning(f"Rate limit exceeded for {request.user} in {company_slug}")
            return HttpResponseForbidden("Too many requests")
        
        # Attach context
        request.company = company
        request.company_slug = company_slug
        
        return view_func(request, company_slug, *args, **kwargs)
    
    return wrapper


# ============================================================================
# 4. HELPER FUNCTIONS
# ============================================================================

def user_has_company_access(user, company):
    """
    Check if user has access to company
    
    Rules:
    - System admin: Access all companies
    - Company admin: Access own company only
    - Employees: Access assigned company only
    """
    # System super admin has access to all
    if user.is_superuser:
        return True
    
    # Check if user is admin of this company
    if hasattr(user, 'company') and user.company == company:
        return True
    
    # Check if user belongs to company as employee
    try:
        if user.company == company:
            return True
    except AttributeError:
        pass
    
    return False


def log_unauthorized_access(user, company, request):
    """
    Log unauthorized access attempt for security audit
    
    Logs:
    - User ID and username
    - Company slug
    - IP address
    - User agent
    - Timestamp
    """
    from django.contrib.gis.geoip2 import GeoIP2
    from .models import AuditLog
    
    try:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.objects.create(
            user=user,
            company=company,
            action='UNAUTHORIZED_ACCESS_ATTEMPT',
            target_type='company',
            target_id=company.id,
            details={
                'reason': 'Access denied - not company member',
                'ip_address': ip_address,
                'user_agent': user_agent,
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Error logging unauthorized access: {e}")


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(user, company, max_requests=100, time_window=3600):
    """
    Check if user exceeds rate limit for company
    
    Args:
        user: User object
        company: Company object
        max_requests: Max requests allowed
        time_window: Time window in seconds (default: 1 hour)
    
    Returns:
        True if under limit, False if exceeded
    """
    from django.core.cache import cache
    import time
    
    cache_key = f"rate_limit:{user.id}:{company.id}"
    current_time = int(time.time())
    window_start = current_time - time_window
    
    # Get request history
    request_times = cache.get(cache_key, [])
    
    # Remove old requests outside window
    request_times = [t for t in request_times if t > window_start]
    
    if len(request_times) >= max_requests:
        return False
    
    # Add current request
    request_times.append(current_time)
    cache.set(cache_key, request_times, time_window)
    
    return True


# ============================================================================
# 5. SLUG GENERATION & MANAGEMENT
# ============================================================================

class SlugManager:
    """Manage slug generation and updates"""
    
    @staticmethod
    def generate_unique_slug(company_name, company=None):
        """
        Generate unique slug for company
        
        Ensures no slug collisions
        """
        base_slug = SlugValidator.generate_from_company_name(company_name)
        slug = base_slug
        counter = 1
        
        while Company.objects.filter(slug=slug).exclude(id=company.id if company else None).exists():
            # Add counter: victor-godwin-ventures -> victor-godwin-ventures-1
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug[:50]  # Enforce max length
    
    @staticmethod
    def verify_slug_uniqueness(slug):
        """Check if slug is already taken"""
        return not Company.objects.filter(slug=slug).exists()
    
    @staticmethod
    def get_company_by_slug(slug):
        """Safely retrieve company by slug"""
        if not SlugValidator.is_valid(slug):
            return None
        
        try:
            return Company.objects.get(slug=slug)
        except Company.DoesNotExist:
            return None
    
    @staticmethod
    def update_slug(company, new_name):
        """
        Update company slug
        
        Warning: This changes company URL!
        Only allow if no external references exist
        """
        new_slug = SlugManager.generate_unique_slug(new_name, company=company)
        
        # Log the change
        logger.info(f"Slug changed for {company.id}: {company.slug} -> {new_slug}")
        
        company.slug = new_slug
        company.save()
        
        return new_slug


# ============================================================================
# 6. URL BUILDERS & REDIRECTS
# ============================================================================

def get_company_url(company, path=''):
    """
    Build company-specific URL
    
    Usage:
        url = get_company_url(company, 'dashboard')
        # Returns: /victor-godwin-ventures/dashboard
    """
    base = f"/{company.slug}"
    if path:
        return f"{base}/{path.lstrip('/')}"
    return base


def get_company_absolute_url(request, company, path=''):
    """
    Build absolute company URL with domain
    
    Usage:
        url = get_company_absolute_url(request, company, 'dashboard')
        # Returns: https://realestateapp.com/victor-godwin-ventures/dashboard
    """
    scheme = 'https' if request.is_secure() else 'http'
    domain = request.get_host()
    path_part = get_company_url(company, path).lstrip('/')
    return f"{scheme}://{domain}/{path_part}"


def redirect_to_company_dashboard(company):
    """Redirect to company dashboard"""
    return redirect(get_company_url(company, 'dashboard'))


# ============================================================================
# 7. SLUG SECURITY UTILITIES
# ============================================================================

class SlugSecurity:
    """Advanced security for slug-based routing"""
    
    SIGNATURE_ALGORITHM = 'sha256'
    
    @staticmethod
    def generate_slug_token(company, user, expires_in=3600):
        """
        Generate secure token for slug access
        
        Prevents direct URL sharing, enables temporary access
        
        Usage:
            token = SlugSecurity.generate_slug_token(company, user)
            url = f"/{company.slug}/dashboard?token={token}"
        """
        import json
        from django.conf import settings
        
        data = {
            'company_id': company.id,
            'user_id': user.id,
            'timestamp': int(time.time()),
            'expires_in': expires_in,
        }
        
        # Create HMAC signature
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'token': signature,
            'data': data
        }
    
    @staticmethod
    def verify_slug_token(token, token_data, company, user):
        """
        Verify slug access token
        
        Returns:
            (is_valid, error_message)
        """
        from django.conf import settings
        
        # Check expiration
        current_time = int(time.time())
        if current_time > token_data['timestamp'] + token_data['expires_in']:
            return False, "Token expired"
        
        # Verify company and user
        if token_data['company_id'] != company.id:
            return False, "Invalid company"
        
        if token_data['user_id'] != user.id:
            return False, "Invalid user"
        
        # Verify signature
        import json
        message = json.dumps(token_data, sort_keys=True)
        expected_signature = hmac.new(
            settings.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(token, expected_signature):
            return False, "Invalid token"
        
        return True, None
    
    @staticmethod
    def is_slug_suspicious(slug):
        """
        Check if slug looks like potential security attack
        
        Patterns:
        - SQL injection attempts
        - Path traversal
        - Script tags
        """
        suspicious_patterns = [
            '../', '..\\',  # Path traversal
            'union', 'select', 'insert', 'update', 'delete',  # SQL
            '<script', 'javascript:', 'onerror',  # XSS
            '%00', '%27', '%22',  # URL encoded
        ]
        
        slug_lower = slug.lower()
        for pattern in suspicious_patterns:
            if pattern in slug_lower:
                return True
        
        return False


# ============================================================================
# 8. SLUG MIGRATION UTILITIES
# ============================================================================

class SlugMigration:
    """Utilities for handling slug changes and migrations"""
    
    @staticmethod
    def create_slug_redirect(old_slug, new_slug):
        """
        Create redirect from old slug to new slug
        
        Prevents 404 errors during migrations
        """
        from django.contrib.redirects.models import Redirect
        
        try:
            redirect_obj = Redirect.objects.get(
                old_path=f"/{old_slug}/"
            )
            redirect_obj.new_path = f"/{new_slug}/"
            redirect_obj.save()
        except Redirect.DoesNotExist:
            Redirect.objects.create(
                site_id=1,
                old_path=f"/{old_slug}/",
                new_path=f"/{new_slug}/"
            )
    
    @staticmethod
    def bulk_generate_slugs(company_ids=None):
        """
        Generate slugs for companies that don't have them
        
        Useful for migration
        """
        companies = Company.objects.filter(slug__isnull=True)
        
        if company_ids:
            companies = companies.filter(id__in=company_ids)
        
        count = 0
        for company in companies:
            slug = SlugManager.generate_unique_slug(company.company_name)
            company.slug = slug
            company.save()
            count += 1
        
        return count
