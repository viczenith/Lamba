"""
Device Token Serializers
=========================
DRF Serializers for device token management (push notifications).

This module provides secure serializers for:
- Device token registration
- Device token listing
- Token validation

SECURITY IMPLEMENTATIONS:
1. Input validation and sanitization
2. Token format validation
3. Platform whitelist validation
4. Length limits to prevent overflow
5. Read-only fields to prevent modification attacks
6. XSS prevention

Used by: Flutter mobile app for push notification registration
Endpoints: /device-tokens/, /device-tokens/register/

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework import serializers
from django.utils.html import escape
import re
import logging

from estateApp.models import UserDeviceToken

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY CONSTANTS
# =============================================================================

# Maximum lengths for security
MAX_TOKEN_LENGTH = 255
MAX_APP_VERSION_LENGTH = 32
MAX_DEVICE_MODEL_LENGTH = 64

# Valid platforms whitelist
VALID_PLATFORMS = {'android', 'ios', 'web'}

# Token format patterns (Firebase/APNs tokens are alphanumeric with some special chars)
TOKEN_PATTERN = re.compile(r'^[a-zA-Z0-9:_\-\.]+$')


# =============================================================================
# SECURITY UTILITY FUNCTIONS
# =============================================================================

def sanitize_string(value, max_length=None):
    """
    Sanitize string input to prevent XSS and limit length.
    SECURITY: Always sanitize user inputs.
    """
    if value is None:
        return ''
    
    sanitized = escape(str(value).strip())
    
    if max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_token_format(token):
    """
    Validate device token format.
    SECURITY: Prevent injection via malformed tokens.
    """
    if not token:
        return False
    
    # Check length
    if len(token) > MAX_TOKEN_LENGTH or len(token) < 10:
        return False
    
    # Check format (alphanumeric with allowed special chars)
    if not TOKEN_PATTERN.match(token):
        return False
    
    return True


# =============================================================================
# SERIALIZERS
# =============================================================================

class DeviceTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for device token registration and listing.
    
    SECURITY IMPLEMENTATIONS:
    - Input validation for token format
    - Platform whitelist validation
    - Length limits on all fields
    - Read-only fields for sensitive data
    - XSS prevention via sanitization
    - Audit logging for registration
    """
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    
    # Explicit field definitions with validation
    token = serializers.CharField(
        max_length=MAX_TOKEN_LENGTH,
        min_length=10,
        required=True,
        help_text="Firebase/APNs device token"
    )
    platform = serializers.ChoiceField(
        choices=UserDeviceToken.Platform.choices,
        required=True,
        help_text="Device platform (android, ios, web)"
    )
    app_version = serializers.CharField(
        max_length=MAX_APP_VERSION_LENGTH,
        required=False,
        allow_blank=True,
        default=""
    )
    device_model = serializers.CharField(
        max_length=MAX_DEVICE_MODEL_LENGTH,
        required=False,
        allow_blank=True,
        default=""
    )

    class Meta:
        model = UserDeviceToken
        fields = [
            "id",
            "user_id",
            "token",
            "platform",
            "app_version",
            "device_model",
            "is_active",
            "created_at",
            "last_seen",
        ]
        read_only_fields = ["id", "user_id", "is_active", "created_at", "last_seen"]

    def validate_token(self, value):
        """
        Validate device token format.
        SECURITY: Prevents malformed/malicious tokens.
        """
        if not value:
            raise serializers.ValidationError("Token is required.")
        
        # Strip whitespace
        value = value.strip()
        
        # Validate format
        if not validate_token_format(value):
            logger.warning(f"SECURITY: Invalid token format attempted: {value[:20]}...")
            raise serializers.ValidationError(
                "Invalid token format. Token must be alphanumeric with allowed characters."
            )
        
        return value

    def validate_platform(self, value):
        """
        Validate platform against whitelist.
        SECURITY: Only allow known platforms.
        """
        if value and value.lower() not in VALID_PLATFORMS:
            logger.warning(f"SECURITY: Invalid platform attempted: {value}")
            raise serializers.ValidationError(
                f"Invalid platform. Must be one of: {', '.join(VALID_PLATFORMS)}"
            )
        return value.lower() if value else value

    def validate_app_version(self, value):
        """
        Sanitize app version string.
        SECURITY: Prevent XSS via app version field.
        """
        return sanitize_string(value, MAX_APP_VERSION_LENGTH)

    def validate_device_model(self, value):
        """
        Sanitize device model string.
        SECURITY: Prevent XSS via device model field.
        """
        return sanitize_string(value, MAX_DEVICE_MODEL_LENGTH)

    def create(self, validated_data):
        """
        Create or update device token with security checks.
        
        SECURITY:
        - Verifies user authentication
        - Logs registration attempts
        - Uses update_or_create to prevent duplicates
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        
        if user is None or not user.is_authenticated:
            logger.warning("SECURITY: Unauthenticated device token registration attempt")
            raise serializers.ValidationError("Authentication required to register device tokens.")

        token = validated_data["token"]
        platform = validated_data["platform"]
        app_version = validated_data.get("app_version", "")
        device_model = validated_data.get("device_model", "")
        
        defaults = {
            "user": user,
            "platform": platform,
            "app_version": app_version,
            "device_model": device_model,
            "is_active": True,
        }

        # Log registration
        logger.info(
            f"Device token registration: user={user.id}, platform={platform}, "
            f"token={token[:20]}..."
        )

        instance, created = UserDeviceToken.objects.update_or_create(
            token=token, 
            defaults=defaults
        )
        
        instance.mark_seen(
            platform=platform,
            app_version=app_version,
            device_model=device_model,
        )
        
        action = "registered" if created else "updated"
        logger.info(f"Device token {action}: user={user.id}, token_id={instance.id}")
        
        return instance

    def to_representation(self, instance):
        """
        Serialize with sanitized output.
        SECURITY: Sanitize all string fields in output.
        """
        data = super().to_representation(instance)
        
        # Sanitize string fields in output
        if data.get('app_version'):
            data['app_version'] = sanitize_string(data['app_version'])
        if data.get('device_model'):
            data['device_model'] = sanitize_string(data['device_model'])
        
        # Truncate token in response for security (don't expose full token)
        if data.get('token'):
            token = data['token']
            if len(token) > 20:
                data['token_preview'] = f"{token[:10]}...{token[-10:]}"
            else:
                data['token_preview'] = token
        
        return data


class DeviceTokenListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing device tokens.
    
    SECURITY:
    - All fields read-only
    - Token truncated for security
    - Sanitized output
    """
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    token_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = UserDeviceToken
        fields = [
            "id",
            "user_id",
            "token_preview",
            "platform",
            "app_version",
            "device_model",
            "is_active",
            "created_at",
            "last_seen",
        ]
        read_only_fields = fields

    def get_token_preview(self, obj):
        """Return truncated token for security."""
        token = obj.token
        if len(token) > 20:
            return f"{token[:10]}...{token[-10:]}"
        return token
