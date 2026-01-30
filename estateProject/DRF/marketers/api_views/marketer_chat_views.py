from datetime import timedelta

from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.generics import CreateAPIView, DestroyAPIView, ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView
from DRF.clients.serializers.chat_serializers import MessageListSerializer
from DRF.shared_drf import APIResponse

from DRF.marketers.serializers.marketer_chat_serializers import (
    MarketerMessageCreateSerializer,
    MarketerMessageListSerializer,
    MarketerMessageSerializer,
)
from DRF.marketers.api_views.marketer_profile_views import IsMarketer
from estateApp.models import Message, CustomUser
from DRF.shared_drf.push_service import send_chat_message_deleted_push


SUPPORT_ROLES = ('admin', 'support')


class MarketerChatPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class MarketerChatListAPIView(ListAPIView):
    """Return the conversation between the marketer and admin users."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]
    serializer_class = MarketerMessageListSerializer
    pagination_class = MarketerChatPagination

    def get_queryset(self):
        user = self.request.user

        Message.objects.filter(
            sender__role__in=SUPPORT_ROLES,
            recipient=user,
            is_read=False,
        ).update(is_read=True, status='read')

        queryset = Message.objects.filter(
            Q(sender=user, recipient__role__in=SUPPORT_ROLES) |
            Q(sender__role__in=SUPPORT_ROLES, recipient=user)
        ).select_related('sender', 'recipient').order_by('date_sent')

        last_msg_id = self.request.query_params.get('last_msg_id')
        if last_msg_id:
            try:
                queryset = queryset.filter(id__gt=int(last_msg_id))
            except (TypeError, ValueError):
                pass

        # Filter by company if provided
        company_id = self.request.query_params.get('company_id')
        if company_id:
            try:
                queryset = queryset.filter(company_id=int(company_id))
            except (TypeError, ValueError):
                pass

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        messages_html = ""
        for msg in queryset:
            messages_html += render_to_string('marketer_side/chat_message.html', {
                'msg': msg,
                'request': request,
            })

        return APIResponse.success(
            data={
                'count': queryset.count(),
                'messages': serializer.data,
                'messages_html': messages_html,
            },
            message='Messages retrieved'
        )


class MarketerChatDetailAPIView(APIView):
    """Retrieve a single marketer-admin chat message."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]

    def get(self, request, pk):
        try:
            message = Message.objects.select_related('sender', 'recipient').get(
                Q(sender=request.user) | Q(recipient=request.user),
                pk=pk,
            )
        except Message.DoesNotExist:
            return APIResponse.not_found(
                message='Message not found or access denied.',
                error_code='MESSAGE_NOT_FOUND'
            )

        serializer = MarketerMessageSerializer(message, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message='Message retrieved'
        )


class MarketerChatSendAPIView(CreateAPIView):
    """Create a new message from marketer to admin."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]
    serializer_class = MarketerMessageCreateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return APIResponse.validation_error(
                errors=serializer.errors,
                error_code='VALIDATION_FAILED'
            )

        message = serializer.save()
        response_serializer = MarketerMessageSerializer(message, context={'request': request})

        message_html = render_to_string('marketer_side/chat_message.html', {
            'msg': message,
            'request': request,
        })

        return APIResponse.created(
            data={
                'message': response_serializer.data,
                'message_html': message_html,
            },
            message='Message sent'
        )


class MarketerChatDeleteAPIView(DestroyAPIView):
    """Allow marketers to delete their own recent messages."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]

    def get_queryset(self):
        return Message.objects.filter(sender=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            message = self.get_queryset().get(pk=kwargs['pk'])
        except Message.DoesNotExist:
            return APIResponse.not_found(
                message='Message not found or access denied.',
                error_code='MESSAGE_NOT_FOUND'
            )

        time_limit = timezone.now() - timedelta(minutes=30)
        if message.date_sent < time_limit:
            return APIResponse.forbidden(
                message='Messages can only be deleted within 30 minutes.',
                error_code='DELETE_TIME_EXPIRED'
            )

        message.deleted_for_everyone = True
        message.deleted_for_everyone_at = timezone.now()
        message.deleted_for_everyone_by = request.user
        message.save(update_fields=[
            'deleted_for_everyone',
            'deleted_for_everyone_at',
            'deleted_for_everyone_by',
        ])

        send_chat_message_deleted_push(message)

        serializer = MarketerMessageSerializer(message, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message='Message deleted'
        )


class MarketerChatDeleteForEveryoneAPIView(APIView):
    """Soft-delete a marketer message for both participants within 24 hours."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]

    def post(self, request):
        message_id = request.data.get('message_id')

        if not message_id:
            return APIResponse.validation_error(
                errors={'message_id': ['message_id is required']},
                error_code='MISSING_FIELD'
            )

        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return APIResponse.validation_error(
                errors={'message_id': ['Invalid message_id supplied']},
                error_code='INVALID_FORMAT'
            )

        try:
            message = Message.objects.select_related('sender').get(pk=message_id)
        except Message.DoesNotExist:
            return APIResponse.not_found(
                message='Message not found',
                error_code='MESSAGE_NOT_FOUND'
            )

        if message.sender != request.user:
            return APIResponse.forbidden(
                message='You can only delete your own messages.',
                error_code='PERMISSION_DENIED'
            )

        if message.deleted_for_everyone:
            serializer = MarketerMessageSerializer(message, context={'request': request})
            return APIResponse.success(
                data=serializer.data,
                message='Message already deleted for everyone'
            )

        time_limit = timezone.now() - timedelta(hours=24)
        if message.date_sent < time_limit:
            return APIResponse.forbidden(
                message='You can only delete messages within 24 hours of sending.',
                error_code='DELETE_TIME_EXPIRED'
            )

        message.deleted_for_everyone = True
        message.deleted_for_everyone_at = timezone.now()
        message.deleted_for_everyone_by = request.user
        message.save(update_fields=[
            'deleted_for_everyone',
            'deleted_for_everyone_at',
            'deleted_for_everyone_by',
        ])

        send_chat_message_deleted_push(message)

        serializer = MarketerMessageSerializer(message, context={'request': request})
        return APIResponse.success(
            data=serializer.data,
            message='Message deleted for everyone'
        )


class MarketerChatUnreadCountAPIView(APIView):
    """Return unread message count from admin to marketer."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]

    def get(self, request):
        user = request.user

        unread_count = Message.objects.filter(
            sender__role__in=SUPPORT_ROLES,
            recipient=user,
            is_read=False,
        ).count()

        last_message = Message.objects.filter(
            Q(sender=user, recipient__role__in=SUPPORT_ROLES) |
            Q(sender__role__in=SUPPORT_ROLES, recipient=user)
        ).select_related('sender').order_by('-date_sent').first()

        data = {
            'unread_count': unread_count,
            'last_message': (
                MessageListSerializer(last_message, context={'request': request}).data
                if last_message
                else None
            ),
        }

        return APIResponse.success(
            data=data,
            message='Unread count retrieved'
        )


class MarketerChatMarkAsReadAPIView(APIView):
    """Mark marketer chat messages as read."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]

    def post(self, request):
        user = request.user
        message_ids = request.data.get('message_ids', [])
        mark_all = request.data.get('mark_all', False)

        if mark_all:
            updated = Message.objects.filter(
                sender__role__in=SUPPORT_ROLES,
                recipient=user,
                is_read=False,
            ).update(is_read=True, status='read')

            return APIResponse.success(
                data={'marked_count': updated},
                message=f'{updated} message(s) marked as read.'
            )

        if message_ids:
            updated = Message.objects.filter(
                id__in=message_ids,
                sender__role__in=SUPPORT_ROLES,
                recipient=user,
                is_read=False,
            ).update(is_read=True, status='read')

            return APIResponse.success(
                data={'marked_count': updated},
                message=f'{updated} message(s) marked as read.'
            )

        return APIResponse.validation_error(
            errors={'request': ['Provide message_ids or set mark_all to true']},
            error_code='MISSING_PARAMETER'
        )


class MarketerChatPollAPIView(APIView):
    """Polling endpoint for marketer chat updates."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsMarketer]

    def get(self, request):
        user = request.user
        last_msg_id = request.query_params.get('last_msg_id', 0)
        company_id = request.query_params.get('company_id')

        try:
            last_msg_id = int(last_msg_id)
        except (TypeError, ValueError):
            last_msg_id = 0

        new_messages = Message.objects.filter(
            Q(sender=user, recipient__role__in=SUPPORT_ROLES) |
            Q(sender__role__in=SUPPORT_ROLES, recipient=user),
            id__gt=last_msg_id,
        ).select_related('sender').order_by('date_sent')

        # Filter by company if provided
        if company_id:
            try:
                new_messages = new_messages.filter(company_id=int(company_id))
            except (TypeError, ValueError):
                pass

        Message.objects.filter(
            id__in=[msg.id for msg in new_messages],
            sender__role__in=SUPPORT_ROLES,
            recipient=user,
            is_read=False,
        ).update(is_read=True, status='read')

        serializer = MarketerMessageListSerializer(new_messages, many=True, context={'request': request})

        new_messages_html = ""
        for msg in new_messages:
            new_messages_html += render_to_string('marketer_side/chat_message.html', {
                'msg': msg,
                'request': request,
            })

        updated_statuses = []
        if new_messages.exists():
            user_messages = Message.objects.filter(
                sender=user,
                id__lte=last_msg_id + len(new_messages),
            ).values('id', 'status')
            updated_statuses = list(user_messages)

        return APIResponse.success(
            data={
                'new_messages': serializer.data,
                'count': new_messages.count(),
                'updated_statuses': updated_statuses,
                'new_messages_html': new_messages_html,
            },
            message='Poll completed'
        )
