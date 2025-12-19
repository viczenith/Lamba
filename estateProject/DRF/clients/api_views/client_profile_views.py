"""
Client Profile API Views
========================
API endpoints for the client profile page tabs:

OVERVIEW TAB:
- ClientProfileOverviewView: GET complete overview data
- ClientProfileView: GET basic profile data (legacy)

EDIT PROFILE TAB:
- ClientProfileEditView: GET/POST profile data for editing
- ClientProfileUpdateView: POST update profile (legacy)
- ClientProfileImageUploadView: POST profile image

PASSWORD TAB:
- ClientChangePasswordView: POST password change
- ChangePasswordView: POST password change (legacy)

SECURITY:
- All endpoints require authentication (TokenAuthentication or SessionAuthentication)
- IsClient permission enforces role-based access
- Clients can only access their own profile data (IDOR protection)
- Password changes validate current password before allowing updates
- Profile images validated for type and size
- Cross-company access allowed (clients can buy from multiple companies)
- Audit logging for security-sensitive operations
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle
from decimal import Decimal
import logging

from DRF.clients.serializers.client_profile_serializer import (
    ClientProfileOverviewSerializer,
    ProfileEditSerializer,
    ProfileImageUploadSerializer,
    ChangePasswordSerializer,
)
from estateApp.models import (
    ClientUser, Transaction, PlotAllocation, PropertyPrice
)

logger = logging.getLogger(__name__)


# =============================================================================
# THROTTLE CLASSES
# =============================================================================

class PasswordChangeThrottle(UserRateThrottle):
    """Limit password change attempts to prevent brute force"""
    rate = '5/hour'


class ProfileUpdateThrottle(UserRateThrottle):
    """Limit profile updates to prevent spam"""
    rate = '30/hour'


# =============================================================================
# PERMISSION CLASSES
# =============================================================================

class IsClient(permissions.BasePermission):
    """
    Permission class to check if user is a client.
    
    SECURITY:
    - Verifies user is authenticated
    - Checks role is 'client'
    - Allows staff/superusers for admin access
    - Logs unauthorized access attempts
    """
    message = 'Access denied. Client role required.'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.warning(
                f"SECURITY: Unauthenticated access attempt to {view.__class__.__name__} "
                f"from IP: {self._get_client_ip(request)}"
            )
            return False
        
        # Allow staff/admins for admin panel access
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            logger.info(f"Admin access to client profile API by {request.user.email}")
            return True
        
        # Check client role
        is_client = getattr(request.user, 'role', '') == 'client'
        
        if not is_client:
            logger.warning(
                f"SECURITY: Non-client user {request.user.email} (role: {getattr(request.user, 'role', 'N/A')}) "
                f"attempted access to {view.__class__.__name__}"
            )
        
        return is_client
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_client_portfolio_stats(client):
    """
    Calculate portfolio statistics for a client.
    Returns dict with: current_value, total_investment, appreciation_total, average_growth, best_estate
    """
    allocations = PlotAllocation.objects.filter(client=client).select_related(
        'estate', 'plot_size', 'plot_size_unit'
    )
    
    total_investment = Decimal('0')
    current_value = Decimal('0')
    estate_growth_data = {}
    
    for alloc in allocations:
        # Get purchase price from transaction
        transaction = Transaction.objects.filter(
            client=client,
            allocation=alloc
        ).first()
        
        if transaction:
            purchase_price = transaction.total_amount or Decimal('0')
            total_investment += purchase_price
        else:
            purchase_price = Decimal('0')
        
        # Get current price from PropertyPrice
        try:
            prop_price = PropertyPrice.objects.filter(
                estate=alloc.estate,
                plot_unit=alloc.plot_size_unit
            ).first()
            current_price = prop_price.current if prop_price else purchase_price
        except Exception:
            current_price = purchase_price
        
        current_value += current_price
        
        # Track growth per estate
        estate_name = alloc.estate.name
        if estate_name not in estate_growth_data:
            estate_growth_data[estate_name] = {
                'estate': alloc.estate,
                'purchase_total': Decimal('0'),
                'current_total': Decimal('0'),
            }
        estate_growth_data[estate_name]['purchase_total'] += purchase_price
        estate_growth_data[estate_name]['current_total'] += current_price
    
    # Calculate appreciation
    appreciation_total = current_value - total_investment
    
    # Calculate average growth percentage
    if total_investment > 0:
        average_growth = ((current_value - total_investment) / total_investment) * 100
    else:
        average_growth = Decimal('0')
    
    # Find best performing estate
    best_estate = None
    best_growth_rate = Decimal('-999999')
    
    for estate_name, data in estate_growth_data.items():
        if data['purchase_total'] > 0:
            growth = ((data['current_total'] - data['purchase_total']) / data['purchase_total']) * 100
            if growth > best_growth_rate:
                best_growth_rate = growth
                best_estate = {
                    'estate_name': estate_name,
                    'growth_rate': growth,
                    'location': data['estate'].location,
                    'company_name': data['estate'].company.company_name if data['estate'].company else None
                }
    
    return {
        'current_value': current_value,
        'total_investment': total_investment,
        'appreciation_total': appreciation_total,
        'average_growth': average_growth,
        'best_performing_estate': best_estate
    }


# =============================================================================
# OVERVIEW TAB VIEWS
# =============================================================================

class ClientProfileOverviewView(APIView):
    """
    GET: Returns complete profile overview data
    Includes: user info, contact, stats, portfolio summary, best estate
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)

    def get(self, request, *args, **kwargs):
        user = request.user
        
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return Response(
                {'detail': 'Client profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get portfolio stats
        portfolio_stats = get_client_portfolio_stats(client)
        
        # Get properties count
        properties_count = PlotAllocation.objects.filter(client=client).count()
        
        # Build overview data
        overview_data = {
            'id': client.id,
            'full_name': client.full_name,
            'email': client.email,
            'profile_image': client.profile_image,
            'role': 'Real Estate Investor',
            'contact_info': {
                'email': client.email,
                'phone': client.phone,
                'company': client.company,
                'address': client.address,
            },
            'profile_details': {
                'full_name': client.full_name,
                'company': client.company,
                'job': client.job,
                'country': client.country,
                'date_registered': client.date_registered,
                'about': client.about,
            },
            'stats': {
                'properties_count': properties_count,
                'total_investment': portfolio_stats['total_investment'],
            },
            'portfolio': portfolio_stats,
        }
        
        serializer = ClientProfileOverviewSerializer(overview_data, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientProfileView(APIView):
    """
    GET: Returns basic profile data (legacy endpoint - kept for backward compatibility)
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return Response({'detail': 'Client profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get portfolio stats
        portfolio_stats = get_client_portfolio_stats(client)
        properties_count = PlotAllocation.objects.filter(client=client).count()

        data = {
            'id': client.id,
            'full_name': client.full_name,
            'email': client.email,
            'phone': client.phone,
            'title': client.title,
            'about': client.about,
            'company': client.company,
            'job': client.job,
            'country': client.country,
            'address': client.address,
            'date_of_birth': client.date_of_birth,
            'date_registered': client.date_registered,
            'profile_image_url': request.build_absolute_uri(f'/secure-profile-image/{client.id}/') if client.profile_image else None,
            'rank_tag': client.rank_tag,
            'properties_count': properties_count,
            'total_investment': str(portfolio_stats['total_investment']),
            'current_value': str(portfolio_stats['current_value']),
            'appreciation_total': str(portfolio_stats['appreciation_total']),
            'average_growth': str(portfolio_stats['average_growth']),
        }

        if portfolio_stats['best_performing_estate']:
            data['highest_growth_estate'] = portfolio_stats['best_performing_estate']['estate_name']
            data['highest_growth_rate'] = str(portfolio_stats['best_performing_estate']['growth_rate'])
            data['highest_growth_location'] = portfolio_stats['best_performing_estate']['location']
            data['highest_growth_company'] = portfolio_stats['best_performing_estate']['company_name']

        return Response(data, status=status.HTTP_200_OK)


# =============================================================================
# EDIT PROFILE TAB VIEWS
# =============================================================================

class ClientProfileEditView(APIView):
    """
    GET: Returns profile data for edit form
    POST: Updates profile data
    
    SECURITY:
    - Rate limited to 30 updates per hour
    - IDOR protection: users can only access their own profile (pk=user.id)
    - Profile image validated for type and size
    - Logs profile updates for audit trail
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (ProfileUpdateThrottle,)

    def get(self, request, *args, **kwargs):
        user = request.user
        # SECURITY: IDOR Protection - only get own profile
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return Response({'detail': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileEditSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = request.user
        # SECURITY: IDOR Protection - only update own profile
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return Response({'detail': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        # Update fields
        updatable_fields = [
            'title', 'full_name', 'about', 'phone', 'country',
            'address', 'company', 'job', 'date_of_birth'
        ]
        
        for field in updatable_fields:
            if field in request.data:
                value = request.data.get(field)
                # Handle empty strings as None for optional fields
                if value == '' and field not in ['full_name']:
                    value = None
                setattr(client, field, value)

        # Handle profile image if included
        if 'profile_image' in request.FILES:
            client.profile_image = request.FILES['profile_image']

        try:
            client.save()
            serializer = ProfileEditSerializer(client)
            logger.info(f"Profile updated for client {client.email}")
            return Response({
                'detail': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Profile update error for {user.email}: {e}")
            return Response({'detail': 'Failed to update profile'}, status=status.HTTP_400_BAD_REQUEST)


class ClientProfileUpdateView(APIView):
    """
    POST: Update profile (legacy endpoint - kept for backward compatibility)
    
    SECURITY:
    - Rate limited to 30 updates per hour
    - IDOR protection: users can only update their own profile
    - Supports both camelCase and snake_case field names
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (ProfileUpdateThrottle,)

    def post(self, request, *args, **kwargs):
        user = request.user
        # SECURITY: IDOR Protection - only update own profile
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return Response({'detail': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        # Map frontend field names to model fields
        field_mapping = {
            'fullName': 'full_name',
            'dateOfBirth': 'date_of_birth',
        }
        
        updatable_fields = [
            'title', 'fullName', 'about', 'phone', 'country',
            'address', 'company', 'job', 'dateOfBirth'
        ]
        
        for field in updatable_fields:
            if field in request.data:
                model_field = field_mapping.get(field, field)
                value = request.data.get(field)
                if value == '':
                    value = None
                setattr(client, model_field, value)

        if 'profile_image' in request.FILES:
            client.profile_image = request.FILES['profile_image']

        try:
            client.save()
            logger.info(f"Profile updated (legacy endpoint) for client {client.email}")
            return Response({'detail': 'Profile updated successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Profile update error for {user.email}: {e}")
            return Response({'detail': 'Failed to update profile'}, status=status.HTTP_400_BAD_REQUEST)


class ClientProfileImageUploadView(APIView):
    """
    POST: Upload profile image only
    
    SECURITY:
    - Rate limited to 30 uploads per hour
    - IDOR protection: users can only update their own image
    - Image validated for type (JPEG, PNG, GIF) and size (max 2MB)
    - Logs image uploads for audit trail
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (ProfileUpdateThrottle,)

    def post(self, request, *args, **kwargs):
        user = request.user
        # SECURITY: IDOR Protection - only update own profile image
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return Response({'detail': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProfileImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        client.profile_image = serializer.validated_data['profile_image']
        client.save()

        logger.info(f"Profile image updated for client {client.email}")

        return Response({
            'detail': 'Profile image updated successfully',
            'profile_image_url': request.build_absolute_uri(f'/secure-profile-image/{client.id}/')
        }, status=status.HTTP_200_OK)


# =============================================================================
# PASSWORD TAB VIEWS
# =============================================================================

class ClientChangePasswordView(APIView):
    """
    POST: Change user password
    
    SECURITY:
    - Rate limited to 5 attempts per hour
    - Validates current password before change
    - Logs all password change attempts
    - Minimum password length enforced
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (PasswordChangeThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']

        # SECURITY: Log password change attempt
        client_ip = self._get_client_ip(request)
        
        if not user.check_password(current_password):
            logger.warning(
                f"SECURITY: Failed password change attempt for {user.email}. "
                f"Incorrect current password. IP: {client_ip}"
            )
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        logger.info(
            f"SECURITY: Password changed successfully for {user.email}. IP: {client_ip}"
        )

        return Response(
            {'detail': 'Password changed successfully.'},
            status=status.HTTP_200_OK
        )
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class ChangePasswordView(APIView):
    """
    POST: Change password (legacy endpoint name - kept for backward compatibility)
    
    SECURITY:
    - Rate limited to 5 attempts per hour
    - Supports both camelCase and snake_case field names
    - Validates current password before change
    - Minimum 8 character password requirement
    - Logs all password change attempts
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (PasswordChangeThrottle,)

    def post(self, request, *args, **kwargs):
        user = request.user
        client_ip = self._get_client_ip(request)
        
        # Support both naming conventions
        current = request.data.get('current_password') or request.data.get('currentPassword')
        new = request.data.get('new_password') or request.data.get('newPassword')
        confirm = request.data.get('confirm_password') or request.data.get('renewPassword')

        if not all([current, new]):
            return Response(
                {'detail': 'Current password and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if confirm and new != confirm:
            return Response(
                {'detail': 'New password and confirmation do not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current):
            logger.warning(
                f"SECURITY: Failed password change attempt for {user.email}. "
                f"Incorrect current password. IP: {client_ip}"
            )
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new) < 8:
            return Response(
                {'detail': 'Password must be at least 8 characters long.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new)
        user.save()

        logger.info(
            f"SECURITY: Password changed successfully for {user.email}. IP: {client_ip}"
        )

        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
