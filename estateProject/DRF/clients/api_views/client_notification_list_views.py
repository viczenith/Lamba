"""
Client Notification List Views
===============================
DRF Views for notification.html (Notifications List Page)

Security Features:
- Token + Session Authentication (dual auth)
- IsClient permission with audit logging
- IDOR Protection - user derived from request.user only
- Rate limiting to prevent abuse
- Company-based data isolation
- Input sanitization
- Comprehensive audit logging
"""

import logging
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from DRF.shared_drf import APIResponse
from DRF.clients.serializers.client_notification_list_serializers import (
    ClientUserNotificationSerializer,
    NotificationListResponseSerializer,
)
from estateApp.models import UserNotification

logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITING
# =============================================================================
class NotificationListThrottle(UserRateThrottle):
    """Rate limit for notification list: 60 requests per hour"""
    rate = '60/hour'


class NotificationActionThrottle(UserRateThrottle):
    """Rate limit for notification actions (mark read/unread): 120 requests per hour"""
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
            f"Notification permission check: user={request.user}, "
            f"is_authenticated={request.user.is_authenticated}"
        )
        
        if not request.user.is_authenticated:
            logger.warning(f"Unauthenticated notification access attempt")
            return False
        
        if request.user.role != 'client':
            logger.warning(
                f"Non-client notification access attempt: user={request.user.email}, "
                f"role={request.user.role}"
            )
            return False
        
        return True


# =============================================================================
# NOTIFICATION LIST PAGE VIEWS
# =============================================================================
class ClientNotificationListPageAPIView(APIView):
    """
    API endpoint for notification.html page
    Returns complete page data with stats, unread list, and read list
    
    GET /api/clients/notifications/page/
    
    Security:
    - Authenticated clients only
    - Returns only notifications belonging to the user
    - Company isolation enforced
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationListThrottle]
    
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            logger.info(f"Notification list page request: user={user.email}")
            
            # SECURITY: Only fetch notifications for the authenticated user
            base_qs = UserNotification.objects.filter(
                user=user
            ).select_related(
                'notification',
                'notification__company'
            ).order_by('-created_at')
            
            # Split into unread and read lists
            unread_list = list(base_qs.filter(read=False))
            read_list = list(base_qs.filter(read=True))
            
            # Build response matching notification.html template
            response_data = {
                'stats': {
                    'unread_count': len(unread_list),
                    'read_count': len(read_list),
                    'total_count': len(unread_list) + len(read_list),
                },
                'unread_list': ClientUserNotificationSerializer(
                    unread_list, 
                    many=True,
                    context={'request': request}
                ).data,
                'read_list': ClientUserNotificationSerializer(
                    read_list, 
                    many=True,
                    context={'request': request}
                ).data,
            }
            
            logger.info(
                f"Notification list returned: user={user.email}, "
                f"unread={len(unread_list)}, read={len(read_list)}"
            )
            
            return APIResponse.success(
                data=response_data,
                message="Notifications retrieved successfully"
            )
            
        except Exception as e:
            logger.error(f"Error fetching notifications: {str(e)}")
            return APIResponse.server_error(
                message="Failed to fetch notifications",
                error_code="NOTIFICATION_FETCH_ERROR"
            )


class ClientNotificationListAPI(ListAPIView):
    """
    Paginated notification list API
    Supports filtering by read status and since timestamp
    
    GET /api/client/notifications/
    Query params:
    - filter: 'all', 'unread', 'read'
    - since: ISO datetime to fetch notifications after
    - page: page number
    - page_size: items per page (max 100)
    
    Security:
    - Authenticated clients only
    - Returns only notifications belonging to the user
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    serializer_class = ClientUserNotificationSerializer
    throttle_classes = [NotificationListThrottle]
    
    def get_queryset(self):
        user = self.request.user
        logger.info(f"Notification list query: user={user.email}")
        
        # SECURITY: Only fetch notifications for the authenticated user
        qs = UserNotification.objects.filter(
            user=user
        ).select_related(
            'notification',
            'notification__company'
        ).order_by('-created_at')
        
        # Apply filter
        filter_param = self.request.GET.get('filter', 'all').lower().strip()
        if filter_param == 'unread':
            qs = qs.filter(read=False)
        elif filter_param == 'read':
            qs = qs.filter(read=True)
        
        # Apply since filter for polling
        since = self.request.GET.get('since', '').strip()
        if since:
            try:
                dt = parse_datetime(since)
                if dt:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.get_default_timezone())
                    qs = qs.filter(created_at__gt=dt)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid since parameter: {since}, error: {e}")
        
        return qs


class ClientUnreadCountAPIView(APIView):
    """
    Return unread notification count for badge display
    
    GET /api/clients/notifications/unread-count/
    
    Response:
    {
        "unread": 5,
        "total": 15
    }
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationListThrottle]
    
    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            
            # SECURITY: Count only user's notifications
            unread = UserNotification.objects.filter(user=user, read=False).count()
            total = UserNotification.objects.filter(user=user).count()
            
            return APIResponse.success(
                data={
                    'unread': unread,
                    'total': total
                },
                message="Unread count retrieved"
            )
            
        except Exception as e:
            logger.error(f"Error fetching unread count: {str(e)}")
            return APIResponse.server_error(
                message="Failed to fetch count",
                error_code="COUNT_FETCH_ERROR"
            )


# =============================================================================
# NOTIFICATION ACTION VIEWS (Mark Read/Unread)
# =============================================================================
class ClientMarkReadAPIView(APIView):
    """
    Mark a notification as read
    
    POST /api/clients/notifications/<pk>/mark-read/
    
    Security:
    - Validates notification belongs to the user
    - IDOR protection via user filtering
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationActionThrottle]
    
    def post(self, request, pk, *args, **kwargs):
        try:
            user = request.user
            
            # SECURITY: Sanitize and validate ID
            try:
                notification_id = int(str(pk).strip())
            except (ValueError, TypeError):
                logger.warning(f"Invalid notification ID: {pk}")
                return APIResponse.validation_error(
                    errors={'id': ['Invalid notification ID']},
                    error_code="INVALID_ID"
                )
            
            # SECURITY: Only fetch if belongs to user (IDOR protection)
            notification = UserNotification.objects.filter(
                pk=notification_id,
                user=user
            ).select_related('notification', 'notification__company').first()
            
            if not notification:
                logger.warning(
                    f"Unauthorized mark-read attempt: user={user.email}, "
                    f"notification_id={notification_id}"
                )
                return APIResponse.not_found(
                    message="Notification not found",
                    error_code="NOTIFICATION_NOT_FOUND"
                )
            
            if not notification.read:
                notification.read = True
                notification.save(update_fields=['read'])
                logger.info(f"Notification marked read: id={notification_id}, user={user.email}")
            
            return APIResponse.success(
                data=ClientUserNotificationSerializer(
                    notification,
                    context={'request': request}
                ).data,
                message="Notification marked as read"
            )
            
        except Exception as e:
            logger.error(f"Error marking notification read: {str(e)}")
            return APIResponse.server_error(
                message="Failed to update notification",
                error_code="UPDATE_ERROR"
            )


class ClientMarkUnreadAPIView(APIView):
    """
    Mark a notification as unread
    
    POST /api/clients/notifications/<pk>/mark-unread/
    
    Security:
    - Validates notification belongs to the user
    - IDOR protection via user filtering
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationActionThrottle]
    
    def post(self, request, pk, *args, **kwargs):
        try:
            user = request.user
            
            # SECURITY: Sanitize and validate ID
            try:
                notification_id = int(str(pk).strip())
            except (ValueError, TypeError):
                logger.warning(f"Invalid notification ID: {pk}")
                return Response(
                    {'error': 'Invalid notification ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # SECURITY: Only fetch if belongs to user (IDOR protection)
            notification = UserNotification.objects.filter(
                pk=notification_id,
                user=user
            ).select_related('notification', 'notification__company').first()
            
            if not notification:
                logger.warning(
                    f"Unauthorized mark-unread attempt: user={user.email}, "
                    f"notification_id={notification_id}"
                )
                return Response(
                    {'error': 'Notification not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if notification.read:
                notification.read = False
                notification.save(update_fields=['read'])
                logger.info(f"Notification marked unread: id={notification_id}, user={user.email}")
            
            return APIResponse.success(
                data=ClientUserNotificationSerializer(
                    notification,
                    context={'request': request}
                ).data,
                message="Notification marked as unread"
            )
            
        except Exception as e:
            logger.error(f"Error marking notification unread: {str(e)}")
            return APIResponse.server_error(
                message="Failed to update notification",
                error_code="UPDATE_ERROR"
            )


class ClientMarkAllReadAPIView(APIView):
    """
    Mark all notifications as read
    
    POST /api/clients/notifications/mark-all-read/
    
    Response:
    {
        "marked": 5  // number of notifications marked
    }
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsClient]
    throttle_classes = [NotificationActionThrottle]
    
    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            
            # SECURITY: Only update user's notifications
            updated = UserNotification.objects.filter(
                user=user,
                read=False
            ).update(read=True)
            
            logger.info(f"All notifications marked read: user={user.email}, count={updated}")
            
            return APIResponse.success(
                data={'marked': updated},
                message="All notifications marked as read"
            )
            
        except Exception as e:
            logger.error(f"Error marking all notifications read: {str(e)}")
            return APIResponse.server_error(
                message="Failed to update notifications",
                error_code="BULK_UPDATE_ERROR"
            )
