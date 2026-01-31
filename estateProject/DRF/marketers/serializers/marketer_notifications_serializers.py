from rest_framework import serializers
from estateApp.models import Notification, UserNotification


class CompanyMiniSerializer(serializers.Serializer):
    """Minimal company representation used by notification serializers."""
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    initial = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        request = self.context.get("request")
        company_id = getattr(obj, "id", None)
        if not company_id or not request:
            return None
        try:
            from django.urls import reverse

            return request.build_absolute_uri(
                reverse("secure-company-logo", kwargs={"company_id": company_id})
            )
        except Exception:
            return None

    def get_initial(self, obj):
        name = getattr(obj, "company_name", None) or getattr(obj, "name", None) or ""
        if name:
            return name[:1].upper()
        return "S"


class MarketerNotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source="get_notification_type_display", read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    company = CompanyMiniSerializer(source="company", read_only=True)

    # Friendly formatted fields used by the detail page
    formatted_date = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "message",
            "created_at",
            "company",
            "formatted_date",
            "formatted_time",
        ]

    def get_formatted_date(self, obj):
        if not obj or not getattr(obj, "created_at", None):
            return ""
        try:
            return obj.created_at.strftime("%b %d, %Y")
        except Exception:
            return ""

    def get_formatted_time(self, obj):
        if not obj or not getattr(obj, "created_at", None):
            return ""
        try:
            # Use 12-hour format with AM/PM
            time_str = obj.created_at.strftime("%I:%M %p")
            return time_str.lstrip('0')
        except Exception:
            return ""


class MarketerUserNotificationSerializer(serializers.ModelSerializer):
    notification = MarketerNotificationSerializer(read_only=True)
    read = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = UserNotification
        fields = ["id", "notification", "read", "created_at"]
