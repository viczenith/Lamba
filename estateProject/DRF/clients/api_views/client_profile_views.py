"""
Client Profile API Views
========================
API endpoints for client profile page tabs:

OVERVIEW TAB:
- ClientProfileOverviewView: GET complete profile overview data
  Returns: Avatar, stats, contact info, portfolio summary, best estate

EDIT PROFILE TAB:
- ClientProfileEditView: GET/POST profile data
  GET: Returns all profile fields for edit form
  POST: Updates title, full_name, email (read-only), DOB, about, phone, country, address, company, job
- ClientProfileImageUploadView: POST profile image only
  POST: Upload new profile image (JPEG/PNG/GIF, max 2MB)

PASSWORD TAB:
- ClientChangePasswordView: POST password change
  POST: Change password with validation (current password, new password, confirmation)

SECURITY:
- All endpoints require authentication (Token or Session)
- IsClient permission enforces role-based access (role='client')
- IDOR Protection: Clients can only access/update their own profile (pk=user.id)
- Password changes: Validates current password before allowing updates
- Profile images: Validated for type (JPEG/PNG/GIF) and size (max 2MB)
- Rate Limiting:
  - Password changes: 5 attempts per hour (prevent brute force)
  - Profile updates: 30 per hour (prevent spam)
- Audit Logging: All security-sensitive operations logged (password change, image upload)
- Cross-company access allowed: Clients can purchase from multiple companies
"""

from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle
from decimal import Decimal
import logging

from DRF.shared_drf import APIResponse
from DRF.clients.serializers.client_profile_serializer import (
    # Overview Tab
    ClientProfileOverviewSerializer,
    # Edit Profile Tab
    ClientProfileEditSerializer,
    ProfilePhotoUploadSerializer,
    # Password Tab
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
    """
    Limit password change attempts to prevent brute force attacks.
    Rate: 5 attempts per hour
    """
    rate = '5/hour'


class ProfileUpdateThrottle(UserRateThrottle):
    """
    Limit profile update requests to prevent spam.
    Rate: 30 updates per hour
    """
    rate = '30/hour'


# =============================================================================
# PERMISSION CLASSES
# =============================================================================

class IsClient(permissions.BasePermission):
    """
    Permission class to verify user is a client.
    
    Checks:
    - User is authenticated
    - User role is 'client'
    - Allows staff/superusers for admin access
    - Logs unauthorized access attempts for security
    
    IDOR Protection: Views using this permission must verify pk=user.id
    """
    message = 'Access denied. Client role required.'
    
    def has_permission(self, request, view):
        # Check authentication
        if not request.user or not request.user.is_authenticated:
            logger.warning(
                f"SECURITY: Unauthenticated access attempt to {view.__class__.__name__} "
                f"from IP: {self._get_client_ip(request)}"
            )
            return False
        
        # Allow staff/superusers (admin access)
        if getattr(request.user, 'is_staff', False) or getattr(request.user, 'is_superuser', False):
            logger.info(f"Admin access to client profile API by {request.user.email}")
            return True
        
        # Verify client role
        is_client = getattr(request.user, 'role', '') == 'client'
        
        if not is_client:
            logger.warning(
                f"SECURITY: Non-client user {request.user.email} (role: {getattr(request.user, 'role', 'N/A')}) "
                f"attempted access to {view.__class__.__name__}"
            )
        
        return is_client
    
    def _get_client_ip(self, request):
        """Extract client IP address from request headers"""
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
    
    Returns:
    {
        'current_value': Total current value of all properties,
        'total_investment': Total amount invested,
        'appreciation_total': Current value - Total investment,
        'average_growth': Average growth percentage,
        'highest_growth_estate': Best performing estate dict or None,
        'highest_growth_rate': Growth rate of best estate,
        'highest_growth_location': Location of best estate,
        'highest_growth_company': Company name of best estate,
    }
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
        
        # Get current price from PropertyPrice model
        try:
            prop_price = PropertyPrice.objects.filter(
                estate=alloc.estate,
                plot_unit=alloc.plot_size_unit
            ).first()
            current_price = prop_price.current if prop_price else purchase_price
        except Exception as e:
            logger.warning(f"Error fetching PropertyPrice for estate {alloc.estate.id}: {e}")
            current_price = purchase_price
        
        current_value += current_price
        
        # Accumulate growth data per estate for best performer calculation
        estate_name = alloc.estate.name
        if estate_name not in estate_growth_data:
            estate_growth_data[estate_name] = {
                'estate': alloc.estate,
                'purchase_total': Decimal('0'),
                'current_total': Decimal('0'),
            }
        estate_growth_data[estate_name]['purchase_total'] += purchase_price
        estate_growth_data[estate_name]['current_total'] += current_price
    
    # Calculate total appreciation
    appreciation_total = current_value - total_investment
    
    # Calculate average growth percentage
    if total_investment > 0:
        average_growth = ((current_value - total_investment) / total_investment) * 100
    else:
        average_growth = Decimal('0')
    
    # Find best performing estate (highest growth rate)
    best_estate_data = {
        'highest_growth_estate': None,
        'highest_growth_rate': Decimal('0'),
        'highest_growth_location': None,
        'highest_growth_company': None,
    }
    
    best_growth_rate = Decimal('-999999')
    
    for estate_name, data in estate_growth_data.items():
        if data['purchase_total'] > 0:
            growth = ((data['current_total'] - data['purchase_total']) / data['purchase_total']) * 100
            if growth > best_growth_rate:
                best_growth_rate = growth
                best_estate_data = {
                    'highest_growth_estate': estate_name,
                    'highest_growth_rate': growth,
                    'highest_growth_location': data['estate'].location or '',
                    'highest_growth_company': data['estate'].company.company_name if data['estate'].company else None,
                }
    
    return {
        'current_value': current_value,
        'total_investment': total_investment,
        'appreciation_total': appreciation_total,
        'average_growth': average_growth,
        **best_estate_data,  # Unpack best estate fields
    }


# =============================================================================
# OVERVIEW TAB VIEWS
# =============================================================================

class ClientProfileOverviewView(APIView):
    """
    GET: Returns complete profile overview data for the OVERVIEW TAB
    
    Includes:
    - Avatar: full_name, profile_image, role
    - Stats: properties_count, total_investment
    - Contact Info: email, phone, company, address
    - Profile Details Table: full_name, company, job, country, date_registered
    - Portfolio Summary: current_value, average_growth, appreciation_total
    - Best Performing Estate: highest_growth_estate, rate, location, company
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)

    def get(self, request, *args, **kwargs):
        user = request.user
        
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            return APIResponse.not_found(
                message="Client profile not found",
                error_code="PROFILE_NOT_FOUND"
            )
        
        try:
            # Get portfolio stats (includes best estate data)
            portfolio_stats = get_client_portfolio_stats(client)
            
            # Get properties count
            properties_count = PlotAllocation.objects.filter(client=client).count()
            
            # Build overview response matching all HTML sections
            overview_data = {
                # Avatar section (left column)
                'id': client.id,
                'full_name': client.full_name,
                'profile_image': client.profile_image.url if client.profile_image else None,
                'role': 'Real Estate Investor',
                
                # Contact info section (left column)
                'email': client.email,
                'phone': client.phone or '',
                'company': client.company or '',
                'address': client.address or '',
                
                # Profile details table (overview tab - right column)
                'job': client.job or '',
                'country': client.country or '',
                'date_registered': client.date_registered,
                'about': client.about or '',
                
                # Stats section (left column)
                'properties_count': properties_count,
                'total_investment': portfolio_stats['total_investment'],
                
                # Portfolio summary section (overview tab - right column)
                'current_value': portfolio_stats['current_value'],
                'average_growth': portfolio_stats['average_growth'],
                'appreciation_total': portfolio_stats['appreciation_total'],
                'highest_growth_estate': portfolio_stats['highest_growth_estate'],
                'highest_growth_rate': portfolio_stats['highest_growth_rate'],
                'highest_growth_location': portfolio_stats['highest_growth_location'],
                'highest_growth_company': portfolio_stats['highest_growth_company'],
            }
            
            serializer = ClientProfileOverviewSerializer(overview_data, context={'request': request})
            
            logger.info(f"Profile overview retrieved for client {client.email}")
            
            return APIResponse.success(
                data=serializer.data,
                message="Profile overview retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error retrieving profile overview for {user.email}: {e}", exc_info=True)
            return APIResponse.server_error(
                message="Failed to retrieve profile overview",
                error_code="RETRIEVAL_FAILED"
            )


# =============================================================================
# EDIT PROFILE TAB VIEWS
# =============================================================================

class ClientProfileEditView(APIView):
    """
    GET: Returns profile data for EDIT PROFILE FORM
    POST: Updates profile data
    
    Returns/Updates:
    - Personal Details: title, full_name, email (read-only), date_of_birth, about
    - Contact Information: phone, country, address
    - Work Information: company, job
    - Profile Photo: profile_image (handled by separate upload endpoint)
    
    SECURITY:
    - Rate limited to 30 updates per hour
    - IDOR protection: users can only access/update their own profile (pk=user.id)
    - Logs all profile updates for audit trail
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (ProfileUpdateThrottle,)

    def get(self, request, *args, **kwargs):
        """GET: Retrieve profile data for edit form"""
        user = request.user
        
        # SECURITY: IDOR Protection - only get own profile
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            logger.warning(f"SECURITY: Client {user.email} attempted to access non-existent profile")
            return APIResponse.not_found(
                message="Client profile not found",
                error_code="PROFILE_NOT_FOUND"
            )

        try:
            serializer = ClientProfileEditSerializer(client)
            logger.info(f"Profile edit data retrieved for {client.email}")
            
            return APIResponse.success(
                data=serializer.data,
                message="Profile data retrieved for editing"
            )
        except Exception as e:
            logger.error(f"Error retrieving profile edit data for {user.email}: {e}")
            return APIResponse.server_error(
                message="Failed to retrieve profile data",
                error_code="RETRIEVAL_FAILED"
            )

    def post(self, request, *args, **kwargs):
        """POST: Update profile data"""
        user = request.user
        
        # SECURITY: IDOR Protection - only update own profile
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            logger.warning(f"SECURITY: Client {user.email} attempted to update non-existent profile")
            return APIResponse.not_found(
                message="Client profile not found",
                error_code="PROFILE_NOT_FOUND"
            )

        try:
            serializer = ClientProfileEditSerializer(
                client,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                logger.warning(f"Profile update validation failed for {user.email}: {serializer.errors}")
                return APIResponse.validation_error(
                    errors=serializer.errors
                )
            
            serializer.save()
            
            logger.info(f"Profile updated successfully for {client.email}")
            
            return APIResponse.success(
                data=serializer.data,
                message="Profile updated successfully"
            )
            
        except Exception as e:
            logger.error(f"Profile update error for {user.email}: {e}", exc_info=True)
            return APIResponse.server_error(
                message="Failed to update profile",
                error_code="UPDATE_FAILED"
            )


class ClientProfileImageUploadView(APIView):
    """
    POST: Upload profile image for EDIT PROFILE TAB
    
    Validation:
    - File type: JPEG, PNG, GIF only
    - File size: Maximum 2MB
    
    SECURITY:
    - Rate limited to 30 uploads per hour
    - IDOR protection: users can only update their own image (pk=user.id)
    - Logs all image uploads for audit trail
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = (ProfileUpdateThrottle,)

    def post(self, request, *args, **kwargs):
        """POST: Upload and set profile image"""
        user = request.user
        
        # SECURITY: IDOR Protection - only update own profile image
        try:
            client = ClientUser.objects.get(pk=user.id)
        except ClientUser.DoesNotExist:
            logger.warning(f"SECURITY: Client {user.email} attempted to update image for non-existent profile")
            return APIResponse.not_found(
                message="Client profile not found",
                error_code="PROFILE_NOT_FOUND"
            )

        try:
            serializer = ProfilePhotoUploadSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Profile image validation failed for {user.email}: {serializer.errors}")
                return APIResponse.validation_error(
                    errors=serializer.errors
                )

            # Update profile image
            client.profile_image = serializer.validated_data['profile_image']
            client.save()

            logger.info(f"Profile image uploaded and updated for {client.email}")

            return APIResponse.success(
                data={
                    'profile_image': client.profile_image.url if client.profile_image else None
                },
                message="Profile image updated successfully"
            )
            
        except Exception as e:
            logger.error(f"Profile image upload error for {user.email}: {e}", exc_info=True)
            return APIResponse.server_error(
                message="Failed to upload profile image",
                error_code="UPLOAD_FAILED"
            )


# =============================================================================
# PASSWORD TAB VIEWS
# =============================================================================

class ClientChangePasswordView(APIView):
    """
    POST: Change user password for PASSWORD TAB
    
    Request Fields:
    - current_password: Current password (required)
    - new_password: New password (required, min 8 chars, 1 uppercase, 1 number)
    - confirm_password: Confirmation of new password (required, must match new_password)
    
    SECURITY:
    - Rate limited to 5 attempts per hour (prevent brute force attacks)
    - Validates current password before allowing change
    - Logs all password change attempts (success and failures)
    - IP address logging for forensics
    - Minimum password requirements enforced
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsClient)
    throttle_classes = (PasswordChangeThrottle,)

    def post(self, request, *args, **kwargs):
        """POST: Validate current password and set new password"""
        user = request.user
        
        try:
            serializer = ChangePasswordSerializer(data=request.data)
            
            if not serializer.is_valid():
                client_ip = self._get_client_ip(request)
                logger.warning(
                    f"SECURITY: Password change validation failed for {user.email}. "
                    f"Errors: {serializer.errors} | IP: {client_ip}"
                )
                return APIResponse.validation_error(
                    errors=serializer.errors
                )

            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']
            client_ip = self._get_client_ip(request)

            # SECURITY: Verify current password before change
            if not user.check_password(current_password):
                logger.warning(
                    f"SECURITY: Failed password change attempt for {user.email}. "
                    f"Incorrect current password. IP: {client_ip}"
                )
                return APIResponse.validation_error(
                    errors={'current_password': ['Current password is incorrect.']},
                    error_code="INVALID_PASSWORD"
                )

            # Set new password
            user.set_password(new_password)
            user.save()

            logger.info(
                f"SECURITY: Password successfully changed for {user.email} | IP: {client_ip}"
            )

            return APIResponse.success(
                message="Password changed successfully"
            )
            
        except Exception as e:
            client_ip = self._get_client_ip(request)
            logger.error(
                f"SECURITY: Unexpected error during password change for {user.email}: {e} | IP: {client_ip}",
                exc_info=True
            )
            return APIResponse.server_error(
                message="Failed to change password",
                error_code="CHANGE_FAILED"
            )
    
    def _get_client_ip(self, request):
        """Extract client IP address from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

