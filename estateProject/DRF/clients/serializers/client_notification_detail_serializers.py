"""
Client Notification Detail Serializers
=======================================
DRF Serializers for notification_detail.html (Single Notification Detail Page)

Security Features:
- Data exposure control - only necessary fields exposed
- Company data isolation - only show notification client should see
- No sensitive internal data exposed
"""

from rest_framework import serializers
from estateApp.models import Company, Notification, UserNotification


class DetailCompanySerializer(serializers.ModelSerializer):
    """Serializer for company data in notification detail - minimal exposure"""
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


class NotificationDetailContentSerializer(serializers.ModelSerializer):
    """
    Serializer for notification content in detail view
    Exposes full message (not truncated like list view)
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display', 
        read_only=True
    )
    company = DetailCompanySerializer(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    formatted_date = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'notification_type_display',
            'title',
            'message',  # Full message, not truncated
            'company',
            'created_at',
            'formatted_date',
            'formatted_time',
        ]
    
    def get_formatted_date(self, obj):
        """Return date formatted as 'Dec 17, 2025'"""
        if obj.created_at:
            return obj.created_at.strftime("%b %d, %Y")
        return ""
    
    def get_formatted_time(self, obj):
        """Return time formatted as '3:45 PM'"""
        if obj.created_at:
            return obj.created_at.strftime("%-I:%M %p") if hasattr(obj.created_at, 'strftime') else obj.created_at.strftime("%I:%M %p").lstrip('0')
        return ""


class ClientNotificationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for UserNotification detail view
    Maps to notification_detail.html template
    """
    notification = NotificationDetailContentSerializer(read_only=True)
    read = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    
    class Meta:
        model = UserNotification
        fields = ['id', 'notification', 'read', 'created_at']


class NotificationDetailResponseSerializer(serializers.Serializer):
    """
    Full response serializer for notification_detail.html page
    Returns single notification with all details
    """
    notification = ClientNotificationDetailSerializer()
    is_read = serializers.BooleanField()
