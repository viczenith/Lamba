from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from DRF.shared_drf import APIResponse

from DRF.marketers.serializers.marketer_notifications_serializers import (
    MarketerUserNotificationSerializer,
)
from DRF.marketers.serializers.permissions import IsMarketerUser
from estateApp.models import UserNotification


class MarketerNotificationPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100


class MarketerNotificationListAPI(ListAPIView):
    """List notifications for the authenticated marketer user."""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)
    serializer_class = MarketerUserNotificationSerializer
    pagination_class = MarketerNotificationPagination

    def get_queryset(self):
        user = self.request.user
        qs = (
            UserNotification.objects.filter(user=user)
            .select_related("notification")
            .order_by("-created_at")
        )

        filt = self.request.GET.get("filter", "all").lower()
        if filt == "unread":
            qs = qs.filter(read=False)
        elif filt == "read":
            qs = qs.filter(read=True)

        since = self.request.GET.get("since")
        if since:
            dt = parse_datetime(since)
            if dt:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_default_timezone())
                qs = qs.filter(created_at__gt=dt)
        return qs


# Page-style API (matches server-rendered notification.html)
class MarketerNotificationListPageAPIView(APIView):
    """API endpoint that returns the full page payload used by notification.html.

    Response shape:
    {
      "stats": { "unread_count": int, "read_count": int, "total_count": int },
      "unread_list": [ UserNotificationSerializer... ],
      "read_list": [ UserNotificationSerializer... ]
    }

    Security:
    - Authenticated marketers only
    - Company-scoped: only notifications from companies the marketer is affiliated with OR global (company is null)
    - Rate-limited for polling
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def get(self, request, *args, **kwargs):
        try:
            user = request.user

            # Get affiliated companies (re-use client helper to ensure canonical logic)
            try:
                from DRF.clients.api_views.client_dashboard_views import get_user_affiliated_companies

                affiliated = get_user_affiliated_companies(user)
                affiliated_ids = [c.id for c in affiliated]
            except Exception:
                affiliated_ids = []

            base_qs = (
                UserNotification.objects.filter(user=user)
                .select_related('notification', 'notification__company')
                .order_by('-created_at')
            )

            # Enforce company scoping for marketers: company in affiliated OR global
            if affiliated_ids:
                from django.db.models import Q

                base_qs = base_qs.filter(
                    Q(notification__company_id__in=affiliated_ids) | Q(notification__company__isnull=True)
                )

            unread_qs = list(base_qs.filter(read=False))
            read_qs = list(base_qs.filter(read=True))

            payload = {
                'stats': {
                    'unread_count': len(unread_qs),
                    'read_count': len(read_qs),
                    'total_count': len(unread_qs) + len(read_qs),
                },
                'unread_list': MarketerUserNotificationSerializer(unread_qs, many=True, context={'request': request}).data,
                'read_list': MarketerUserNotificationSerializer(read_qs, many=True, context={'request': request}).data,
            }

            return APIResponse.success(data=payload, message='Notifications retrieved')

        except Exception as exc:
            return APIResponse.server_error(message='Failed to fetch notifications', error=str(exc))


class MarketerNotificationDetailAPI(RetrieveAPIView):
    """Retrieve a specific notification belonging to the marketer."""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)
    serializer_class = MarketerUserNotificationSerializer
    lookup_field = "pk"

    def get_object(self):
        user = self.request.user
        return get_object_or_404(
            UserNotification.objects.select_related("notification"),
            pk=self.kwargs["pk"],
            user=user,
        )


class MarketerUnreadCountAPI(APIView):
    """Return unread and total counts for marketer notifications."""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def get(self, request, *args, **kwargs):
        user = request.user
        unread = UserNotification.objects.filter(user=user, read=False).count()
        total = UserNotification.objects.filter(user=user).count()
        return APIResponse.success(
            data={"unread": unread, "total": total},
            message="Unread count retrieved"
        )


class MarketerMarkReadAPI(APIView):
    """Mark a marketer notification as read."""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        un = get_object_or_404(UserNotification, pk=pk, user=user)
        if not un.read:
            un.read = True
            un.save(update_fields=["read"])
        return APIResponse.success(
            data=MarketerUserNotificationSerializer(un, context={"request": request}).data,
            message="Notification marked read"
        )


class MarketerMarkUnreadAPI(APIView):
    """Mark a marketer notification as unread."""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        un = get_object_or_404(UserNotification, pk=pk, user=user)
        if un.read:
            un.read = False
            un.save(update_fields=["read"])
        return APIResponse.success(
            data=MarketerUserNotificationSerializer(un, context={"request": request}).data,
            message="Notification marked unread"
        )


class MarketerMarkAllReadAPI(APIView):
    """Mark all marketer notifications as read."""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def post(self, request, *args, **kwargs):
        user = request.user
        updated = UserNotification.objects.filter(user=user, read=False).update(read=True)
        return APIResponse.success(
            data={"marked": updated},
            message="All notifications marked read"
        )


# -----------------------------------------------------------------------------
# Marketer notification detail page and delete endpoints
# -----------------------------------------------------------------------------
import logging
from rest_framework.throttling import UserRateThrottle

logger = logging.getLogger(__name__)


class MarketerNotificationDetailThrottle(UserRateThrottle):
    """Rate limit for marketer notification detail: 120 requests per hour"""
    rate = '120/hour'


def validate_marketer_notification_ownership(user, notification_id):
    """
    Validate that the UserNotification with id belongs to the marketer user.
    Returns (user_notification, error_response) tuple.
    """
    try:
        nid = int(str(notification_id).strip())
    except (ValueError, TypeError):
        logger.warning(f"Invalid notification ID format: {notification_id}")
        return None, APIResponse.validation_error(errors={'id': ['Invalid notification ID']}, error_code='INVALID_ID')

    un = UserNotification.objects.filter(pk=nid, user=user).select_related('notification', 'notification__company').first()
    if not un:
        logger.warning(f"Unauthorized notification access attempt: user={user.email}, notification_id={nid}")
        return None, APIResponse.not_found(message='Notification not found', error_code='NOTIFICATION_NOT_FOUND')

    return un, None


class MarketerNotificationDetailPageAPIView(APIView):
    """API endpoint for marketer notification detail page.

    GET /api/marketers/notifications/<pk>/detail/
    - Auto marks as read (configurable via ?auto_read=false)
    - Returns { 'notification': serialized UserNotification, 'is_read': bool }
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)
    throttle_classes = (MarketerNotificationDetailThrottle,)

    def get(self, request, pk, *args, **kwargs):
        try:
            user = request.user
            logger.info(f"Marketer notification detail request: user={user.email}, pk={pk}")

            un, err = validate_marketer_notification_ownership(user, pk)
            if err:
                return err

            auto_mark = request.GET.get('auto_read', 'true').lower() == 'true'
            if auto_mark and not un.read:
                un.read = True
                un.save(update_fields=['read'])

            payload = {
                'notification': MarketerUserNotificationSerializer(un, context={'request': request}).data,
                'is_read': un.read,
            }

            return APIResponse.success(data=payload, message='Notification detail retrieved')
        except Exception as exc:
            logger.exception('Failed to fetch marketer notification detail')
            return APIResponse.server_error(message='Failed to fetch notification', error=str(exc))


class MarketerNotificationDeleteAPIView(APIView):
    """Delete a marketer user notification (deletes only the UserNotification)."""
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)
    throttle_classes = (MarketerNotificationDetailThrottle,)

    def delete(self, request, pk, *args, **kwargs):
        try:
            user = request.user
            un, err = validate_marketer_notification_ownership(user, pk)
            if err:
                return err

            nid = un.id
            title = un.notification.title if un.notification else 'Unknown'
            un.delete()
            logger.info(f"Marketer notification deleted: id={nid}, title={title}, user={user.email}")
            return APIResponse.success(data={'id': nid}, message='Notification deleted')
        except Exception as exc:
            logger.exception('Failed to delete marketer notification')
            return APIResponse.server_error(message='Failed to delete notification', error=str(exc))
