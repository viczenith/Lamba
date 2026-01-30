from rest_framework import serializers
from estateApp.models import Company, Notification, UserNotification


class NotificationCompanySerializer(serializers.ModelSerializer):
    """Serializer for company data in notifications - minimal exposure"""
    logo_url = serializers.SerializerMethodField()
    initial = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = ['id', 'company_name', 'logo_url', 'initial']
    
    def get_logo_url(self, obj):
        """Return secure logo URL if company has logo"""
        if obj and obj.logo:
            return f"/api/secure-company-logo/{obj.id}/"
        return None
    
    def get_initial(self, obj):
        """Return first letter of company name for avatar fallback"""
        if obj and obj.company_name:
            return obj.company_name[0].upper()
        return "S"


class NotificationItemSerializer(serializers.ModelSerializer):
    """Serializer for the inner Notification model"""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    company = NotificationCompanySerializer(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    time_ago = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',
            'preview',
            'company',
            'created_at',
            'time_ago',
        ]
    
    def get_preview(self, obj):
        """Return truncated message for list preview"""
        if obj.message:
            return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
        return ""
    
    def get_time_ago(self, obj):
        """Return human-readable time difference"""
        from django.utils import timezone
        from django.utils.timesince import timesince
        if obj.created_at:
            return f"{timesince(obj.created_at)} ago"
        return ""


class ClientUserNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for UserNotification model (notification list items)
    Maps to each notification card in the list
    """
    notification = NotificationItemSerializer(read_only=True)
    read = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    
    class Meta:
        model = UserNotification
        fields = ['id', 'notification', 'read', 'created_at']


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    unread_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    total_count = serializers.IntegerField()


class NotificationListResponseSerializer(serializers.Serializer):
    """
    Full response serializer for notification.html page
    Matches the HTML template structure:
    - stats (unread/read counts)
    - unread_list (new notifications)
    - read_list (earlier notifications)
    """
    stats = NotificationStatsSerializer()
    unread_list = ClientUserNotificationSerializer(many=True)
    read_list = ClientUserNotificationSerializer(many=True)
