"""
Client Notification Detail Views
=================================
DRF Views for notification_detail.html (Single Notification Detail Page)

Security Features:
- Token + Session Authentication (dual auth)
- IsClient permission with audit logging
- IDOR Protection - user derived from request.user only
- Notification ownership validation
- Rate limiting to prevent abuse
- Comprehensive audit logging
- Auto mark-as-read on view (optional)
"""

import logging
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from DRF.clients.serializers.client_notification_detail_serializers import (
    ClientNotificationDetailSerializer,
    NotificationDetailResponseSerializer,
)
from estateApp.models import UserNotification

logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITING
# =============================================================================
class NotificationDetailThrottle(UserRateThrottle):
    """Rate limit for notification detail: 120 requests per hour"""
    rate = '120/hour'


# =============================================================================
# PERMISSIONS
# =============================================================================
class IsClient(BasePermission):
    """
    Permission class to ensure only clients can access these endpoints.
    Includes audit logging for security monitoring.
    """
    def has_permission(self, request, view):
        logger.info(
            f"Notification detail permission check: user={request.user}, "
            f"is_authenticated={request.user.is_authenticated}"
        )
        
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated notification detail access attempt")
            return False
        
        if request.user.role != 'client':
            logger.warning(
                f"Non-client notification detail access attempt: user={request.user.email}, "
                f"role={request.user.role}"
            )
            return False
        
        return True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def validate_notification_ownership(user, notification_id):
    """
    Validates that notification belongs to the user.
    Returns (notification, error_response) tuple.
    
    Security:
    - Prevents IDOR attacks
    - User can only access their own notifications
    """
    # Sanitize ID
    try:
        sanitized_id = int(str(notification_id).strip())
    except (ValueError, TypeError):
        logger.warning(f"Invalid notification ID format: {notification_id}")
        return None, Response(
            {'error': 'Invalid notification ID'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Fetch with ownership check
    notification = UserNotification.objects.filter(
        pk=sanitized_id,
        user=user
    ).select_related(
        'notification',
        'notification__company'
    ).first()
    
    if not notification:
        logger.warning(
            f"Unauthorized notification access attempt: user={user.email}, "
            f"notification_id={sanitized_id}"
        )
        return None, Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return notification, None


# =============================================================================
# NOTIFICATION DETAIL PAGE VIEWS
# =============================================================================
class ClientNotificationDetailPageAPIView(APIView):
    """
    API endpoint for notification_detail.html page
    Returns complete notification data for detail view
    
    GET /api/clients/notifications/<pk>/detail/
    
    Features:
    - Auto marks notification as read on view
    - Returns full notification content
    
    Security:
    - Authenticated clients only
    - Returns only if notification belongs to user
    - IDOR protection
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationDetailThrottle]
    
    def get(self, request, pk, *args, **kwargs):
        try:
            user = request.user
            logger.info(f"Notification detail page request: user={user.email}, pk={pk}")
            
            # SECURITY: Validate ownership
            notification, error_response = validate_notification_ownership(user, pk)
            if error_response:
                return error_response
            
            # Auto mark as read when viewed (configurable via query param)
            auto_mark_read = request.GET.get('auto_read', 'true').lower() == 'true'
            if auto_mark_read and not notification.read:
                notification.read = True
                notification.save(update_fields=['read'])
                logger.info(f"Notification auto-marked read: id={pk}, user={user.email}")
            
            # Build response matching notification_detail.html template
            response_data = {
                'notification': ClientNotificationDetailSerializer(
                    notification,
                    context={'request': request}
                ).data,
                'is_read': notification.read,
            }
            
            logger.info(f"Notification detail returned: user={user.email}, pk={pk}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching notification detail: {str(e)}")
            return Response(
                {'error': 'Failed to fetch notification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClientNotificationDetailAPI(RetrieveAPIView):
    """
    Simple retrieve endpoint for notification detail
    Used by existing API consumers
    
    GET /api/client/notifications/<pk>/
    
    Security:
    - Authenticated clients only
    - Returns only if notification belongs to user
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    serializer_class = ClientNotificationDetailSerializer
    throttle_classes = [NotificationDetailThrottle]
    lookup_field = 'pk'
    
    def get_object(self):
        user = self.request.user
        pk = self.kwargs.get('pk')
        
        logger.info(f"Notification detail query: user={user.email}, pk={pk}")
        
        # SECURITY: Sanitize ID
        try:
            notification_id = int(str(pk).strip())
        except (ValueError, TypeError):
            logger.warning(f"Invalid notification ID: {pk}")
            from django.http import Http404
            raise Http404("Notification not found")
        
        # SECURITY: Only fetch if belongs to user (IDOR protection)
        notification = UserNotification.objects.filter(
            pk=notification_id,
            user=user
        ).select_related(
            'notification',
            'notification__company'
        ).first()
        
        if not notification:
            logger.warning(
                f"Notification not found or unauthorized: user={user.email}, pk={pk}"
            )
            from django.http import Http404
            raise Http404("Notification not found")
        
        # Auto mark as read
        if not notification.read:
            notification.read = True
            notification.save(update_fields=['read'])
            logger.info(f"Notification marked read on view: id={pk}")
        
        return notification


class ClientNotificationDeleteAPIView(APIView):
    """
    Delete a notification
    
    DELETE /api/clients/notifications/<pk>/delete/
    
    Security:
    - Validates notification belongs to the user
    - IDOR protection via user filtering
    - Soft or hard delete based on system config
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationDetailThrottle]
    
    def delete(self, request, pk, *args, **kwargs):
        try:
            user = request.user
            
            # SECURITY: Validate ownership
            notification, error_response = validate_notification_ownership(user, pk)
            if error_response:
                return error_response
            
            notification_id = notification.id
            notification_title = notification.notification.title if notification.notification else "Unknown"
            
            # Delete the UserNotification (not the base Notification)
            notification.delete()
            
            logger.info(
                f"Notification deleted: id={notification_id}, "
                f"title={notification_title}, user={user.email}"
            )
            
            return Response(
                {'message': 'Notification deleted successfully'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return Response(
                {'error': 'Failed to delete notification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
