"""
Device Token API Views
=======================
DRF views for device token management (push notifications).

This module provides secure API endpoints for:
- Registering device tokens (POST /device-tokens/register/)
- Deleting device tokens (DELETE /device-tokens/register/)
- Listing user's device tokens (GET /device-tokens/)

SECURITY IMPLEMENTATIONS:
1. Authentication required for all endpoints
2. Rate limiting to prevent abuse
3. User-scoped data isolation (users only see their own tokens)
4. Input validation and sanitization
5. Audit logging for all operations
6. Error handling without information disclosure

Used by: Flutter mobile app for push notification registration
Linked to: push_notification_service.dart, api_service.dart

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.throttling import UserRateThrottle
from django.utils import timezone
import logging

from estateApp.models import UserDeviceToken
from DRF.clients.serializers.device_token_serializers import (
    DeviceTokenSerializer, 
    DeviceTokenListSerializer
)

logger = logging.getLogger(__name__)


# =============================================================================
# THROTTLE CLASSES
# =============================================================================

class DeviceTokenRegisterThrottle(UserRateThrottle):
    """
    Rate limiting for device token registration.
    10 requests per minute - registration shouldn't be frequent.
    """
    rate = '10/minute'
    scope = 'device_token_register'


class DeviceTokenListThrottle(UserRateThrottle):
    """
    Rate limiting for device token listing.
    30 requests per minute.
    """
    rate = '30/minute'
    scope = 'device_token_list'


# =============================================================================
# SECURITY UTILITY FUNCTIONS
# =============================================================================

def log_access(user, action, resource_type, resource_id=None, success=True, details=None):
    """
    Log access attempts for security auditing.
    SECURITY: Track all device token operations.
    """
    log_data = {
        'user_id': user.id if user else None,
        'user_email': getattr(user, 'email', 'anonymous'),
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'success': success,
        'details': details,
        'timestamp': timezone.now().isoformat()
    }
    
    if success:
        logger.info(f"DEVICE_TOKEN: {action}", extra=log_data)
    else:
        logger.warning(f"DEVICE_TOKEN_FAILED: {action}", extra=log_data)


def validate_token_param(token):
    """
    Validate token parameter from request.
    SECURITY: Prevents injection via malformed tokens.
    """
    if not token:
        return None
    
    token = str(token).strip()
    
    # Basic validation
    if len(token) < 10 or len(token) > 255:
        return None
    
    # Only alphanumeric and safe chars
    import re
    if not re.match(r'^[a-zA-Z0-9:_\-\.]+$', token):
        logger.warning(f"SECURITY: Invalid token format in request: {token[:20]}...")
        return None
    
    return token


# =============================================================================
# API VIEWS
# =============================================================================

class DeviceTokenRegisterView(APIView):
    """
    Register or delete device tokens for push notifications.
    
    POST: Register a new device token
    DELETE: Remove a device token
    
    SECURITY IMPLEMENTATIONS:
    - Token/Session authentication required
    - Rate limiting (10 requests/minute)
    - Input validation
    - User-scoped operations
    - Audit logging
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DeviceTokenRegisterThrottle]

    def post(self, request, *args, **kwargs):
        """
        Register a device token for push notifications.
        
        POST /device-tokens/register/
        Body: {token, platform, app_version?, device_model?}
        """
        try:
            user = request.user
            
            serializer = DeviceTokenSerializer(
                data=request.data, 
                context={"request": request}
            )
            
            if not serializer.is_valid():
                log_access(user, 'register_token', 'device_token', 
                          success=False, details=str(serializer.errors))
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            instance = serializer.save()
            
            log_access(user, 'register_token', 'device_token', 
                      resource_id=instance.id, 
                      details=f"platform={instance.platform}")

            response_serializer = DeviceTokenSerializer(
                instance, 
                context={"request": request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception(f"Device token registration error: {e}")
            return Response(
                {"error": "Failed to register device token"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, *args, **kwargs):
        """
        Delete a device token.
        
        DELETE /device-tokens/register/?token=xxx
        or
        DELETE /device-tokens/register/ with body {token: xxx}
        """
        try:
            user = request.user
            
            # Get token from body or query params
            token = request.data.get("token") or request.query_params.get("token")
            
            # Validate token
            token = validate_token_param(token)
            if not token:
                return Response(
                    {"detail": "Valid token is required to delete a device registration."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Only delete tokens belonging to this user (SECURITY)
            deleted_count, _ = UserDeviceToken.objects.filter(
                user=user, 
                token=token
            ).delete()
            
            if deleted_count == 0:
                log_access(user, 'delete_token', 'device_token', 
                          success=False, details=f"Token not found: {token[:20]}...")
                return Response(
                    {"detail": "Specified token was not found for this user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            log_access(user, 'delete_token', 'device_token', 
                      details=f"Deleted token: {token[:20]}...")
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.exception(f"Device token deletion error: {e}")
            return Response(
                {"error": "Failed to delete device token"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeviceTokenListView(APIView):
    """
    List all device tokens for the authenticated user.
    
    GET /device-tokens/
    
    SECURITY IMPLEMENTATIONS:
    - Token/Session authentication required
    - Rate limiting (30 requests/minute)
    - User-scoped data only (users only see their own tokens)
    - Result limiting
    - Audit logging
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [DeviceTokenListThrottle]

    def get(self, request, *args, **kwargs):
        """
        List user's device tokens.
        
        Returns tokens ordered by last_seen (most recent first).
        Limited to 50 tokens max for security.
        """
        try:
            user = request.user
            
            # User-scoped query (SECURITY: only user's own tokens)
            queryset = UserDeviceToken.objects.filter(
                user=user
            ).order_by("-last_seen")[:50]  # Limit results
            
            log_access(user, 'list_tokens', 'device_token', 
                      details=f"Count: {queryset.count()}")
            
            serializer = DeviceTokenListSerializer(
                queryset, 
                many=True, 
                context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Device token list error: {e}")
            return Response(
                {"error": "Failed to retrieve device tokens"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
