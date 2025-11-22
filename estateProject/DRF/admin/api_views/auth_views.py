"""
Authentication and Company Management ViewSets for DRF.
Migrates authentication endpoints to DRF with full security integration.
"""
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from estateApp.models import Company, CustomUser as User
from ..serializers.company_serializers import CompanyDetailedSerializer, CompanyBasicSerializer
from ..serializers.user_serializers import CustomUserSerializer
from estateApp.permissions import (
    IsAuthenticated, IsCompanyOwnerOrAdmin, SubscriptionRequiredPermission
)
from estateApp.throttles import AnonymousUserThrottle, SubscriptionTierThrottle
from estateApp.audit_logging import AuditLogger
from estateApp.error_tracking import track_errors, ErrorHandler

logger = logging.getLogger(__name__)


class AuthenticationViewSet(viewsets.ViewSet):
    """
    Authentication endpoints:
    - Register company
    - Login
    - Logout
    - Token refresh
    """
    
    permission_classes = []
    throttle_classes = [AnonymousUserThrottle]
    
    @action(detail=False, methods=['post'])
    @track_errors(error_type='authentication')
    def register(self, request):
        """Register a new company"""
        
        serializer = CompanyBasicSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Create company
                company = serializer.save()
                
                # Create superuser for company
                user_data = request.data.get('admin_user', {})
                user = User.objects.create_user(
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    password=user_data.get('password'),
                    first_name=user_data.get('first_name'),
                    company=company,
                    is_staff=True,
                    is_superuser=True,
                )
                
                # Log audit
                AuditLogger.log_create(
                    user=user,
                    company=company,
                    instance=company,
                    request=request,
                    extra_fields=['company_name', 'subscription_tier']
                )
                
                # Generate token
                token, _ = Token.objects.get_or_create(user=user)
                
                return Response({
                    'company': CompanyBasicSerializer(company).data,
                    'user': CustomUserSerializer(user).data,
                    'token': token.key,
                    'message': 'Company registered successfully'
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            ErrorHandler.handle_api_error(e, request=request, view=self)
            return Response(
                {'error': 'Registration failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    @track_errors(error_type='authentication')
    def login(self, request):
        """Login user and return token"""
        
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find user by email
            user = User.objects.get(email=email)
            
            # Authenticate
            if not user.check_password(password):
                raise ValueError("Invalid credentials")
            
            # Check if company is active
            if hasattr(user, 'company') and not user.company.is_active:
                return Response(
                    {'error': 'Company account is suspended'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Log audit
            if hasattr(user, 'company'):
                AuditLogger.log_login(
                    user=user,
                    company=user.company,
                    request=request
                )
            
            # Generate/get token
            token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                'user': CustomUserSerializer(user).data,
                'token': token.key,
                'company': CompanyBasicSerializer(user.company).data if hasattr(user, 'company') else None,
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Login error: {e}")
            return Response(
                {'error': 'Login failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    @track_errors(error_type='authentication')
    def logout(self, request):
        """Logout user and invalidate token"""
        
        try:
            # Delete token
            request.user.auth_token.delete()
            
            # Log audit
            if hasattr(request.user, 'company'):
                AuditLogger.log_logout(
                    user=request.user,
                    company=request.user.company,
                    request=request
                )
            
            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(
                {'error': 'Logout failed'},
                status=status.HTTP_400_BAD_REQUEST
            )


class CompanyViewSet(viewsets.ModelViewSet):
    """
    Company management endpoints:
    - List companies (admin only)
    - Retrieve company details
    - Update company settings
    - Manage subscription
    """
    
    queryset = Company.objects.all()
    serializer_class = CompanyDetailedSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    throttle_classes = [SubscriptionTierThrottle]
    
    def get_queryset(self):
        """Filter companies by user"""
        user = self.request.user
        
        if user.is_superuser:
            return Company.objects.all()
        
        if hasattr(user, 'company'):
            return Company.objects.filter(id=user.company.id)
        
        return Company.objects.none()
    
    def perform_create(self, serializer):
        """Create company with audit log"""
        company = serializer.save()
        
        AuditLogger.log_create(
            user=self.request.user,
            company=company,
            instance=company,
            request=self.request,
            extra_fields=['company_name', 'subscription_tier']
        )
    
    def perform_update(self, serializer):
        """Update company with audit log"""
        old_instance = self.get_object()
        old_values = {
            'subscription_tier': old_instance.subscription_tier,
            'subscription_status': old_instance.subscription_status,
        }
        
        company = serializer.save()
        
        new_values = {
            'subscription_tier': company.subscription_tier,
            'subscription_status': company.subscription_status,
        }
        
        AuditLogger.log_update(
            user=self.request.user,
            company=company,
            instance=company,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get detailed company information"""
        
        company = self.get_object()
        serializer = self.get_serializer(company)
        
        return Response({
            'company': serializer.data,
            'subscription_info': {
                'tier': company.subscription_tier,
                'status': company.subscription_status,
                'expires_at': company.subscription_ends_at,
                'trial_ends_at': company.trial_ends_at,
                'api_calls_daily': company.max_api_calls_daily,
                'max_plots': company.max_plots,
                'max_agents': company.max_agents,
            }
        })
    
    @action(detail=True, methods=['post'])
    def upgrade_subscription(self, request, pk=None):
        """Upgrade company subscription tier"""
        
        company = self.get_object()
        new_tier = request.data.get('tier')
        
        if new_tier not in ['starter', 'professional', 'enterprise']:
            return Response(
                {'error': 'Invalid subscription tier'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_tier = company.subscription_tier
        
        try:
            with transaction.atomic():
                # Update subscription
                company.subscription_tier = new_tier
                company.subscription_status = 'active'
                company.subscription_ends_at = timezone.now() + timedelta(days=365)
                company.save()
                
                # Log audit
                AuditLogger.log_subscription_change(
                    user=request.user,
                    company=company,
                    old_tier=old_tier,
                    new_tier=new_tier,
                    request=request
                )
                
                return Response({
                    'message': f'Subscription upgraded to {new_tier}',
                    'company': CompanyDetailedSerializer(company).data
                })
        
        except Exception as e:
            logger.error(f"Subscription upgrade error: {e}", exc_info=True)
            ErrorHandler.handle_api_error(e, request=request, view=self)
            return Response(
                {'error': 'Subscription upgrade failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def check_api_limit(self, request, pk=None):
        """Check if company has exceeded API limits"""
        
        company = self.get_object()
        
        # This would integrate with rate limiting
        from django.core.cache import cache
        from django.utils import timezone
        
        today = timezone.now().strftime("%Y%m%d")
        cache_key = f'usage:company:{company.id}:{today}'
        usage = cache.get(cache_key, {'requests': 0})
        
        limit = company.max_api_calls_daily
        exceeded = usage['requests'] >= limit
        
        return Response({
            'exceeded': exceeded,
            'current_usage': usage['requests'],
            'limit': limit,
            'remaining': max(0, limit - usage['requests'])
        })


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    User management endpoints:
    - List users in company
    - Create user
    - Update user
    - Delete user
    - Manage permissions
    """
    
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated, IsCompanyOwnerOrAdmin]
    throttle_classes = [SubscriptionTierThrottle]
    
    def get_queryset(self):
        """Get users in company"""
        company = getattr(self.request, 'company', None)
        
        if company:
            return User.objects.filter(company=company)
        
        return User.objects.none()
    
    def perform_create(self, serializer):
        """Create user with audit log"""
        user = serializer.save(company=self.request.company)
        
        AuditLogger.log_create(
            user=self.request.user,
            company=self.request.company,
            instance=user,
            request=self.request,
            extra_fields=['username', 'email', 'is_staff']
        )
    
    def perform_update(self, serializer):
        """Update user with audit log"""
        old_instance = self.get_object()
        old_values = {
            'is_staff': old_instance.is_staff,
            'is_active': old_instance.is_active,
        }
        
        user = serializer.save()
        
        new_values = {
            'is_staff': user.is_staff,
            'is_active': user.is_active,
        }
        
        AuditLogger.log_update(
            user=self.request.user,
            company=self.request.company,
            instance=user,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    def perform_destroy(self, instance):
        """Delete user with audit log"""
        AuditLogger.log_delete(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            request=self.request,
        )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password"""
        
        user = self.get_object()
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Old and new password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.check_password(old_password):
            return Response(
                {'error': 'Invalid current password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user.set_password(new_password)
        user.save()
        
        AuditLogger.log_security_event(
            user=request.user,
            company=request.company,
            event_type='password_change',
            description=f'User {user.email} changed password',
            severity='LOW',
            request=request
        )
        
        return Response({'message': 'Password changed successfully'})
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """Toggle user active status"""
        
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        AuditLogger.log_update(
            user=request.user,
            company=request.company,
            instance=user,
            old_values={'is_active': not user.is_active},
            new_values={'is_active': user.is_active},
            request=request,
        )
        
        return Response({
            'message': f'User {"activated" if user.is_active else "deactivated"}',
            'is_active': user.is_active
        })
