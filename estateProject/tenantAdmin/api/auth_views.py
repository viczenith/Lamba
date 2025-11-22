"""
Tenant Admin Authentication API
Handles system admin login/logout
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate
from estateApp.audit_logging import AuditLogger
import logging

logger = logging.getLogger(__name__)


class TenantAdminAuthViewSet(viewsets.ViewSet):
    """
    System Admin Login Endpoint
    Only system administrators can access this endpoint
    """
    permission_classes = []
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """System admin login endpoint"""
        import jwt
        from datetime import datetime, timedelta
        from django.conf import settings
        
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            AuditLogger.log_security_event(
                user=None,
                company=None,
                event_type='login_attempt',
                description=f'Login attempt with missing credentials from {request.META.get("REMOTE_ADDR")}',
                severity='MEDIUM',
                request=request
            )
            return Response(
                {'error': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user
        user = authenticate(email=email, password=password)
        
        if not user:
            # Try username authentication as fallback
            from django.contrib.auth import authenticate as django_authenticate
            user = django_authenticate(username=email, password=password)
        
        if not user:
            AuditLogger.log_security_event(
                user=None,
                company=None,
                event_type='login_attempt',
                description=f'Failed login attempt for {email} from {request.META.get("REMOTE_ADDR")}',
                severity='MEDIUM',
                request=request
            )
            return Response(
                {'error': 'Invalid email or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user is system admin
        if not hasattr(user, 'is_system_admin') or not user.is_system_admin:
            AuditLogger.log_security_event(
                user=user,
                company=None,
                event_type='unauthorized_access_attempt',
                description=f'Non-system admin {user.email} attempted to access Tenant Admin panel from {request.META.get("REMOTE_ADDR")}',
                severity='HIGH',
                request=request
            )
            return Response(
                {'error': 'Access denied: Not a system administrator'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate JWT token with admin claims
        token_payload = {
            'user_id': user.id,
            'email': user.email,
            'is_system_admin': True,
            'admin_level': 'system',
            'scope': ['tenant:admin', 'system:admin'],
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'company_id': None,
        }
        
        try:
            token = jwt.encode(
                token_payload,
                settings.SECRET_KEY,
                algorithm='HS256'
            )
        except Exception as e:
            logger.error(f"JWT encoding error: {str(e)}")
            return Response(
                {'error': 'Token generation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Log successful login
        AuditLogger.log_security_event(
            user=user,
            company=None,
            event_type='system_admin_login',
            description=f'System admin {user.email} logged into Tenant Admin panel from {request.META.get("REMOTE_ADDR")}',
            severity='LOW',
            request=request
        )
        
        return Response({
            'access_token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'is_system_admin': True,
                'admin_level': 'system',
            },
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """System admin logout endpoint"""
        if request.user.is_authenticated:
            AuditLogger.log_security_event(
                user=request.user,
                company=None,
                event_type='system_admin_logout',
                description=f'System admin {request.user.email} logged out from Tenant Admin panel',
                severity='LOW',
                request=request
            )
        
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
