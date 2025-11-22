"""
Advanced authentication mechanisms for multi-tenant API.
Supports token, API key, and tenant-aware authentication.
"""
import logging
from rest_framework.authentication import TokenAuthentication, BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class BearerTokenAuthentication(TokenAuthentication):
    """
    Bearer token authentication.
    Token format: Bearer <token>
    """
    keyword = 'Bearer'
    
    def authenticate(self, request):
        result = super().authenticate(request)
        
        if result:
            user, token = result
            # Store token object for later use (rate limiting, etc.)
            request.auth_token = token
        
        return result


class APIKeyAuthentication(BaseAuthentication):
    """
    API Key authentication for service-to-service communication.
    Supports header: X-API-Key
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
        
        try:
            # Import here to avoid circular imports
            from estateApp.models import APIKey
            
            # Get and verify API key
            api_key_obj = APIKey.objects.select_related('company', 'created_by').get(
                key=api_key,
                is_active=True
            )
            
            # Check if key is expired
            if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
                raise AuthenticationFailed('API key has expired.')
            
            # Check rate limit
            if api_key_obj.should_be_rate_limited():
                raise AuthenticationFailed('API key rate limit exceeded.')
            
            # Update last used
            api_key_obj.last_used_at = timezone.now()
            api_key_obj.usage_count += 1
            api_key_obj.save(update_fields=['last_used_at', 'usage_count'])
            
            # Get user from API key
            user = api_key_obj.created_by
            
            # Set company on request
            request.company = api_key_obj.company
            request.api_key = api_key_obj
            
            logger.info(f"API request authenticated with key: {api_key_obj.name}")
            
            return (user, api_key_obj)
        
        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            raise AuthenticationFailed('Invalid API key.')


class TenantAwareTokenAuthentication(TokenAuthentication):
    """
    Token authentication with automatic tenant/company extraction.
    """
    
    def authenticate(self, request):
        result = super().authenticate(request)
        
        if result:
            user, token = result
            
            # Try to get company from user
            try:
                if hasattr(user, 'company'):
                    request.company = user.company
                elif hasattr(user, 'employee') and hasattr(user.employee, 'company'):
                    request.company = user.employee.company
            except Exception as e:
                logger.warning(f"Could not set company on request: {e}")
            
            return result
        
        return None


class SessionAuthentication(BaseAuthentication):
    """
    Django session authentication with tenant awareness.
    """
    
    def authenticate(self, request):
        user = request.user
        
        if not user or not user.is_authenticated:
            return None
        
        # Set company on request
        try:
            if hasattr(user, 'company'):
                request.company = user.company
        except Exception as e:
            logger.warning(f"Could not set company from session: {e}")
        
        return (user, None)


class MultiAuthenticationBackend:
    """
    Composite authentication supporting multiple methods:
    - API Key (X-API-Key header)
    - Bearer Token (Authorization: Bearer <token>)
    - Session (Django session)
    - Query parameter (for WebSocket)
    """
    
    AUTHENTICATION_CLASSES = [
        APIKeyAuthentication,
        BearerTokenAuthentication,
        SessionAuthentication,
    ]
    
    @staticmethod
    def authenticate_request(request):
        """Authenticate request using available methods"""
        for auth_class in MultiAuthenticationBackend.AUTHENTICATION_CLASSES:
            try:
                auth = auth_class()
                result = auth.authenticate(request)
                if result is not None:
                    request.user, request.auth = result
                    return True
            except AuthenticationFailed:
                continue
            except Exception as e:
                logger.warning(f"Authentication error: {e}")
                continue
        
        return False


class JWTTenantAuthentication(BaseAuthentication):
    """
    JWT authentication with tenant claim.
    JWT payload includes 'company_id' claim for multi-tenant support.
    """
    
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        
        if len(auth) != 2 or auth[0].lower() != 'bearer':
            return None
        
        try:
            import jwt
            from django.conf import settings
            
            token = auth[1]
            
            # Decode JWT
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # Get user
            user = User.objects.get(id=payload.get('user_id'))
            
            # Set company from JWT
            company_id = payload.get('company_id')
            if company_id:
                from estateApp.models import Company
                try:
                    company = Company.objects.get(id=company_id)
                    request.company = company
                except Company.DoesNotExist:
                    raise AuthenticationFailed('Invalid company in token.')
            
            return (user, token)
        
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('JWT token has expired.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid JWT token.')
        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            raise AuthenticationFailed('Authentication failed.')


class OAuthTokenAuthentication(TokenAuthentication):
    """
    OAuth token authentication for third-party integrations.
    """
    
    def authenticate(self, request):
        # Try standard token first
        result = super().authenticate(request)
        
        if result:
            return result
        
        # Try OAuth token from header
        auth = request.META.get('HTTP_AUTHORIZATION', '').split()
        
        if len(auth) != 2 or auth[0].lower() != 'oauth':
            return None
        
        try:
            from estateApp.models import OAuthToken
            
            oauth_token = OAuthToken.objects.select_related('user', 'company').get(
                token=auth[1],
                is_active=True
            )
            
            # Check expiration
            if oauth_token.is_expired():
                raise AuthenticationFailed('OAuth token has expired.')
            
            request.company = oauth_token.company
            request.oauth_token = oauth_token
            
            return (oauth_token.user, oauth_token)
        
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            raise AuthenticationFailed('Invalid OAuth token.')


def get_company_from_request(request):
    """
    Extract company from request through various means.
    """
    # Check if already set
    if hasattr(request, 'company') and request.company:
        return request.company
    
    # Try to get from URL
    company_id = request.query_params.get('company_id')
    if company_id:
        try:
            from estateApp.models import Company
            company = Company.objects.get(id=company_id)
            request.company = company
            return company
        except Exception:
            pass
    
    # Try to get from user
    if request.user and request.user.is_authenticated:
        if hasattr(request.user, 'company'):
            return request.user.company
    
    return None
