"""
Client Estate Detail API Views
================================
DRF Views for the client estate detail page (client_estate_detail.html)

This module provides secure API endpoints for:
- Estate detail information retrieval
- Secure prototype image serving
- Secure estate layout image serving
- Secure floor plan image serving

SECURITY IMPLEMENTATIONS:
1. Authentication required for all endpoints
2. Multi-tenant data isolation (company-based)
3. Client ownership verification (only access their properties)
4. Rate limiting to prevent abuse and DoS attacks
5. Input validation and sanitization
6. Audit logging for security monitoring
7. No direct file path exposure
8. Permission-based access control
9. IDOR (Insecure Direct Object Reference) prevention
10. Information disclosure prevention

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework.views import APIView

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.db.models import Q
import logging
import mimetypes
import os

from DRF.shared_drf import APIResponse
from DRF.clients.serializers.client_estate_detail_serializer import (
    ClientEstateDetailSerializer,
    ClientEstateDetailResponseSerializer,
    ErrorResponseSerializer,
)
from DRF.clients.serializers.permissions import IsClientUser

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM THROTTLE CLASSES
# =============================================================================

class ClientEstateDetailThrottle(UserRateThrottle):
    """
    Custom throttle for estate detail API.
    SECURITY: Prevents abuse and potential DoS attacks.
    """
    rate = '100/hour'
    scope = 'client_estate_detail'


class SecureMediaThrottle(UserRateThrottle):
    """
    Throttle for secure media endpoints.
    SECURITY: Higher limit for images but still protected.
    """
    rate = '500/hour'
    scope = 'secure_media'


class BurstThrottle(UserRateThrottle):
    """
    Burst throttle to prevent rapid-fire requests.
    SECURITY: Limits short-term request bursts.
    """
    rate = '30/minute'
    scope = 'burst'


# =============================================================================
# BASE SECURE VIEW CLASS
# =============================================================================

class SecureClientBaseView(APIView):
    """
    Base view class with common security implementations.
    
    SECURITY FEATURES:
    - Client profile validation
    - Company isolation verification
    - Audit logging
    - Error handling without information disclosure
    """
    permission_classes = [IsAuthenticated, IsClientUser]
    
    def get_client_profile(self, user):
        """
        Get the client profile for authenticated user.
        
        SECURITY: Validates user has proper client profile.
        Raises PermissionDenied if not a valid client.
        """
        # Try different attribute names based on model structure
        client_profile = None
        
        # Check for ClientUser (the actual client model)
        if hasattr(user, 'role') and user.role == 'client':
            # User IS the client in this case
            client_profile = user
        elif hasattr(user, 'client_profile'):
            client_profile = user.client_profile
        elif hasattr(user, 'clientprofile'):
            client_profile = user.clientprofile
        
        if not client_profile:
            logger.warning(
                f"SECURITY: User {user.id} ({user.email}) attempted access without client profile"
            )
            raise PermissionDenied("Client profile not found. Access denied.")
        
        return client_profile

    def validate_company_access(self, client_profile, company):
        """
        Validate client has relationship with the company.
        
        SECURITY: Prevents cross-company data access.
        """
        if not company:
            return False
        
        # Check if client has any allocations/transactions with this company
        from estateApp.models import PlotAllocation, Transaction
        
        has_access = False
        
        # Check through allocations
        try:
            has_access = PlotAllocation.objects.filter(
                client=client_profile,
                estate__company=company
            ).exists()
        except Exception:
            pass
        
        if not has_access:
            # Check through transactions
            try:
                has_access = Transaction.objects.filter(
                    client=client_profile,
                    company=company
                ).exists()
            except Exception:
                pass
        
        return has_access

    def validate_estate_access(self, client_profile, estate, plot_size=None):
        """
        Validate client has access to this specific estate.
        
        SECURITY: 
        - Verifies ownership through PlotAllocation
        - Optionally validates specific plot size access
        - Prevents IDOR attacks
        """
        from estateApp.models import PlotAllocation
        
        # Build base query
        query = Q(client=client_profile, estate=estate)
        
        # If plot size specified, add to query
        if plot_size:
            query &= Q(plot_size=plot_size)
        
        has_access = PlotAllocation.objects.filter(query).exists()
        
        if not has_access:
            logger.warning(
                f"SECURITY: Client {client_profile.id} attempted unauthorized access to "
                f"estate {estate.id}" + (f" with plot_size {plot_size.id}" if plot_size else "")
            )
        
        return has_access

    def log_access(self, client_profile, resource_type, resource_id, success=True):
        """
        Log access attempts for security audit trail.
        
        SECURITY: Creates audit log for monitoring and forensics.
        """
        status_str = "SUCCESS" if success else "DENIED"
        logger.info(
            f"ACCESS_LOG: [{status_str}] Client {client_profile.id} accessed "
            f"{resource_type} ID:{resource_id}"
        )

    def handle_error(self, error, context=""):
        """
        Handle errors without exposing sensitive information.
        
        SECURITY: Logs full error internally, returns safe message to client.
        """
        logger.exception(f"Error in {context}: {str(error)}")
        return APIResponse.server_error(
            message="An error occurred processing your request",
            error_code="SERVER_ERROR"
        )


# =============================================================================
# MAIN ESTATE DETAIL VIEW
# =============================================================================

class ClientEstateDetailAPIView(SecureClientBaseView):
    """
    API endpoint for retrieving client estate details.
    
    GET /api/client/estate/{estate_id}/plot-size/{plot_size_id}/
    
    SECURITY IMPLEMENTATIONS:
    - Authentication required
    - Client role verification
    - Estate ownership validation
    - Plot size access validation
    - Rate limiting (100/hour, 30/minute burst)
    - Audit logging
    - No sensitive data exposure
    - Input validation
    
    Response includes:
    - Estate basic info (name, location, size, title deed)
    - Company minimal info (only ID and name)
    - Progress updates timeline
    - Amenities with icons
    - Prototypes (filtered by plot size)
    - Estate layouts
    - Floor plans (filtered by plot size)
    - Maps with Google embed links
    - Navigation URLs
    """
    throttle_classes = [ClientEstateDetailThrottle, BurstThrottle]

    def get(self, request, *args, **kwargs):
        """
        Retrieve estate details for a specific plot size.

        This method accepts multiple URL shapes for backwards-compatibility:
        - /api/client/estate/<estate_id>/plot-size/<plot_size_id>/  (canonical)
        - /api/clients/estates/<pk>/?plot_size_id=<id>                (legacy/mobile)

        Normalizes parameters from kwargs or querystring and validates them.
        """
        try:
            # Normalize inputs (accept 'estate_id' or legacy 'pk')
            estate_id = kwargs.get('estate_id') or kwargs.get('pk') or (args[0] if len(args) > 0 else None)
            plot_size_id = kwargs.get('plot_size_id') or request.GET.get('plot_size_id') or request.GET.get('plot_size')

            # Import models
            from estateApp.models import Estate, PlotSize, EstateFloorPlan

            # =================================================================
            # STEP 1: Input Validation
            # =================================================================
            try:
                estate_id = int(estate_id)
                plot_size_id = int(plot_size_id)

                # Additional validation for reasonable ranges
                if estate_id <= 0 or plot_size_id <= 0:
                    raise ValueError("IDs must be positive integers")
                if estate_id > 2147483647 or plot_size_id > 2147483647:
                    raise ValueError("ID values too large")

            except (ValueError, TypeError) as e:
                logger.warning(
                    f"SECURITY: Invalid input from user {getattr(request.user, 'id', 'anon')}: "
                    f"estate_id={estate_id}, plot_size_id={plot_size_id}"
                )
                return APIResponse.validation_error(
                    errors={'estate_id': ['Invalid estate or plot size identifier']},
                    error_code="INVALID_ID"
                )
            
            # =================================================================
            # STEP 2: Get Client Profile
            # =================================================================
            client_profile = self.get_client_profile(request.user)
            
            # =================================================================
            # STEP 3: Fetch Estate with Optimized Queries
            # =================================================================
            try:
                estate = Estate.objects.select_related(
                    'company'
                ).prefetch_related(
                    'progress_status',
                    'estate_amenity',
                    'prototypes',
                    'prototypes__plot_size',
                    'estate_layout',
                    'map',
                ).get(id=estate_id)
            except Estate.DoesNotExist:
                logger.info(f"Estate {estate_id} not found for user {request.user.id}")
                return APIResponse.not_found(
                    message="Estate not found",
                    error_code="ESTATE_NOT_FOUND"
                )
            
            # =================================================================
            # STEP 4: Fetch Plot Size
            # =================================================================
            try:
                plot_size = PlotSize.objects.get(id=plot_size_id)
            except PlotSize.DoesNotExist:
                logger.info(f"Plot size {plot_size_id} not found for user {request.user.id}")
                return APIResponse.not_found(
                    message="Plot size not found",
                    error_code="PLOT_SIZE_NOT_FOUND"
                )
            
            # =================================================================
            # STEP 5: Validate Client Access (CRITICAL SECURITY CHECK)
            # =================================================================
            if not self.validate_estate_access(client_profile, estate, plot_size):
                self.log_access(client_profile, "estate", estate_id, success=False)
                return APIResponse.forbidden(
                    message="You do not have access to this estate with the specified plot size",
                    error_code="ACCESS_DENIED"
                )
            
            # =================================================================
            # STEP 6: Fetch Floor Plans (Filtered by Plot Size)
            # =================================================================
            floor_plans = EstateFloorPlan.objects.filter(
                estate=estate,
                plot_size=plot_size
            ).order_by('-date_uploaded')
            
            # =================================================================
            # STEP 7: Serialize Data
            # =================================================================
            serializer = ClientEstateDetailSerializer(
                estate,
                context={
                    'request': request,
                    'plot_size': plot_size,
                    'floor_plans': floor_plans,
                    'client_profile': client_profile,
                }
            )
            
            # =================================================================
            # STEP 8: Log Successful Access
            # =================================================================
            self.log_access(client_profile, "estate", estate_id, success=True)
            
            # =================================================================
            # STEP 9: Return Response
            # =================================================================
            return APIResponse.success(
                data=serializer.data,
                message="Estate details retrieved successfully",
                meta={
                    "estate_id": estate_id,
                    "plot_size_id": plot_size_id,
                }
            )
            
        except PermissionDenied as e:
            return APIResponse.forbidden(
                message=str(e),
                error_code="PERMISSION_DENIED"
            )
        except Exception as e:
            return self.handle_error(e, "ClientEstateDetailAPIView.get")


# =============================================================================
# SECURE MEDIA SERVING VIEWS
# =============================================================================

class SecureMediaBaseView(SecureClientBaseView):
    """
    Base class for secure media serving endpoints.
    
    SECURITY FEATURES:
    - Validates file exists and is accessible
    - Determines correct content type
    - Prevents path traversal attacks
    - Validates client access before serving
    """
    throttle_classes = [SecureMediaThrottle, BurstThrottle]
    
    # Allowed image MIME types
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
        'image/webp', 'image/svg+xml'
    }
    
    # Maximum file size to serve (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def validate_file(self, file_field):
        """
        Validate file exists and is safe to serve.
        
        SECURITY:
        - Checks file exists
        - Validates file size
        - Verifies MIME type
        - Prevents path traversal
        """
        if not file_field:
            return False, "File not found."
        
        try:
            # Check if file has path attribute
            if not hasattr(file_field, 'path'):
                return False, "Invalid file reference."
            
            file_path = file_field.path
            
            # SECURITY: Prevent path traversal
            if '..' in file_path or file_path.startswith('/'):
                logger.warning(f"SECURITY: Potential path traversal attempt: {file_path}")
                return False, "Invalid file path."
            
            # Check file exists
            if not os.path.exists(file_path):
                return False, "File does not exist."
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                logger.warning(f"SECURITY: File too large: {file_path} ({file_size} bytes)")
                return False, "File too large."
            
            # Validate MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type not in self.ALLOWED_MIME_TYPES:
                logger.warning(f"SECURITY: Invalid MIME type: {mime_type} for {file_path}")
                return False, "Invalid file type."
            
            return True, mime_type
            
        except Exception as e:
            logger.exception(f"Error validating file: {e}")
            return False, "Error accessing file."

    def serve_file(self, file_field, filename=None):
        """
        Securely serve a file.
        
        Returns FileResponse with appropriate headers.
        """
        is_valid, result = self.validate_file(file_field)
        
        if not is_valid:
            return APIResponse.not_found(
                message=result,
                error_code="FILE_NOT_FOUND"
            )
        
        mime_type = result
        
        try:
            response = FileResponse(
                open(file_field.path, 'rb'),
                content_type=mime_type
            )
            
            # Set cache headers (cache for 1 hour)
            response['Cache-Control'] = 'private, max-age=3600'
            
            # Set content disposition if filename provided
            if filename:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            logger.exception(f"Error serving file: {e}")
            return APIResponse.server_error(
                message="Error retrieving file",
                error_code="FILE_ERROR"
            )


class SecurePrototypeImageAPIView(SecureMediaBaseView):
    """
    Secure endpoint for serving prototype images.
    
    GET /api/secure/prototype/{prototype_id}/image/
    
    SECURITY:
    - Validates client has access to prototype's estate
    - Serves image through FileResponse (no direct path exposure)
    - Validates file type and size
    - Logs access for audit trail
    """

    def get(self, request, prototype_id):
        """Serve prototype image securely."""
        try:
            from estateApp.models import EstatePrototype
            
            # Validate input
            try:
                prototype_id = int(prototype_id)
                if prototype_id <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return APIResponse.validation_error(
                    errors={'prototype_id': ['Invalid prototype identifier']},
                    error_code="INVALID_ID"
                )
            
            # Get client profile
            client_profile = self.get_client_profile(request.user)
            
            # Fetch prototype
            try:
                prototype = EstatePrototype.objects.select_related(
                    'estate', 'estate__company'
                ).get(id=prototype_id)
            except EstatePrototype.DoesNotExist:
                return APIResponse.not_found(
                    message="Prototype not found",
                    error_code="PROTOTYPE_NOT_FOUND"
                )
            
            # Validate access
            if not self.validate_estate_access(client_profile, prototype.estate):
                self.log_access(client_profile, "prototype_image", prototype_id, success=False)
                return APIResponse.forbidden(
                    message="Access denied",
                    error_code="ACCESS_DENIED"
                )
            
            # Log access
            self.log_access(client_profile, "prototype_image", prototype_id, success=True)
            
            # Serve image
            return self.serve_file(
                prototype.prototype_image,
                filename=f"prototype_{prototype_id}.jpg"
            )
            
        except PermissionDenied as e:
            return APIResponse.forbidden(
                message=str(e),
                error_code="PERMISSION_DENIED"
            )
        except Exception as e:
            return self.handle_error(e, "SecurePrototypeImageAPIView.get")


class SecureEstateLayoutAPIView(SecureMediaBaseView):
    """
    Secure endpoint for serving estate layout images.
    
    GET /api/secure/estate-layout/{layout_id}/image/
    
    SECURITY:
    - Validates client has access to layout's estate
    - Serves image through FileResponse
    - Validates file type and size
    - Logs access for audit trail
    """

    def get(self, request, layout_id):
        """Serve estate layout image securely."""
        try:
            from estateApp.models import EstateLayout
            
            # Validate input
            try:
                layout_id = int(layout_id)
                if layout_id <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return APIResponse.validation_error(
                    errors={'layout_id': ['Invalid layout identifier']},
                    error_code="INVALID_ID"
                )
            
            # Get client profile
            client_profile = self.get_client_profile(request.user)
            
            # Fetch layout
            try:
                layout = EstateLayout.objects.select_related(
                    'estate', 'estate__company'
                ).get(id=layout_id)
            except EstateLayout.DoesNotExist:
                return APIResponse.not_found(
                    message="Layout not found",
                    error_code="LAYOUT_NOT_FOUND"
                )
            
            # Validate access
            if not self.validate_estate_access(client_profile, layout.estate):
                self.log_access(client_profile, "estate_layout", layout_id, success=False)
                return APIResponse.forbidden(
                    message="Access denied",
                    error_code="ACCESS_DENIED"
                )
            
            # Log access
            self.log_access(client_profile, "estate_layout", layout_id, success=True)
            
            # Serve image
            return self.serve_file(
                layout.layout_image,
                filename=f"estate_layout_{layout_id}.jpg"
            )
            
        except PermissionDenied as e:
            return APIResponse.forbidden(
                message=str(e),
                error_code="PERMISSION_DENIED"
            )
        except Exception as e:
            return self.handle_error(e, "SecureEstateLayoutAPIView.get")


class SecureFloorPlanAPIView(SecureMediaBaseView):
    """
    Secure endpoint for serving floor plan images.
    
    GET /api/secure/floor-plan/{plan_id}/image/
    
    SECURITY:
    - Validates client has access to floor plan's estate
    - Serves image through FileResponse
    - Validates file type and size
    - Logs access for audit trail
    """

    def get(self, request, plan_id):
        """Serve floor plan image securely."""
        try:
            from estateApp.models import EstateFloorPlan
            
            # Validate input
            try:
                plan_id = int(plan_id)
                if plan_id <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return APIResponse.validation_error(
                    errors={'plan_id': ['Invalid floor plan identifier']},
                    error_code="INVALID_ID"
                )
            
            # Get client profile
            client_profile = self.get_client_profile(request.user)
            
            # Fetch floor plan
            try:
                plan = EstateFloorPlan.objects.select_related(
                    'estate', 'estate__company', 'plot_size'
                ).get(id=plan_id)
            except EstateFloorPlan.DoesNotExist:
                return APIResponse.not_found(
                    message="Floor plan not found",
                    error_code="FLOOR_PLAN_NOT_FOUND"
                )
            
            # Validate access - also check plot size access
            if not self.validate_estate_access(client_profile, plan.estate, plan.plot_size):
                self.log_access(client_profile, "floor_plan", plan_id, success=False)
                return APIResponse.forbidden(
                    message="Access denied",
                    error_code="ACCESS_DENIED"
                )
            
            # Log access
            self.log_access(client_profile, "floor_plan", plan_id, success=True)
            
            # Serve image
            return self.serve_file(
                plan.floor_plan_image,
                filename=f"floor_plan_{plan_id}.jpg"
            )
            
        except PermissionDenied as e:
            return APIResponse.forbidden(
                message=str(e),
                error_code="PERMISSION_DENIED"
            )
        except Exception as e:
            return self.handle_error(e, "SecureFloorPlanAPIView.get")


# =============================================================================
# ADDITIONAL SECURITY UTILITY VIEWS
# =============================================================================

class ClientEstateAccessCheckAPIView(SecureClientBaseView):
    """
    Utility endpoint to check if client has access to an estate.
    
    GET /api/client/estate/{estate_id}/access-check/
    
    Returns:
        200: {"has_access": true/false, "plot_sizes": [...]}
    
    Useful for:
    - Pre-flight access checks
    - UI state management
    - Navigation decisions
    """
    throttle_classes = [ClientEstateDetailThrottle]

    def get(self, request, estate_id):
        """Check client's access to an estate."""
        try:
            from estateApp.models import Estate, PlotAllocation
            
            # Validate input
            try:
                estate_id = int(estate_id)
                if estate_id <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return APIResponse.validation_error(
                    errors={'estate_id': ['Invalid estate identifier']},
                    error_code="INVALID_ID"
                )
            
            # Get client profile
            client_profile = self.get_client_profile(request.user)
            
            # Check estate exists
            try:
                estate = Estate.objects.get(id=estate_id)
            except Estate.DoesNotExist:
                return APIResponse.not_found(
                    message="Estate not found",
                    error_code="ESTATE_NOT_FOUND"
                )
            
            # Get client's plot allocations for this estate
            allocations = PlotAllocation.objects.filter(
                client=client_profile,
                estate=estate
            ).select_related('plot_size')
            
            has_access = allocations.exists()
            
            # Get unique plot sizes client has access to
            plot_sizes = list(set([
                {
                    'id': a.plot_size.id,
                    'size': a.plot_size.size
                }
                for a in allocations if a.plot_size
            ]))
            
            return APIResponse.success(
                data={
                    'has_access': has_access,
                    'estate_id': estate_id,
                    'plot_sizes': plot_sizes
                },
                message="Access check completed"
            )
            
        except PermissionDenied as e:
            return APIResponse.forbidden(
                message=str(e),
                error_code="PERMISSION_DENIED"
            )
        except Exception as e:
            return self.handle_error(e, "ClientEstateAccessCheckAPIView.get")
