"""
Client Profile Serializers
==========================
Serializers for the client profile page tabs:
- Overview Tab (profile info, contact, portfolio stats, best estate)
- Edit Profile Tab (profile update form)
- Password Tab (change password form)
"""

from rest_framework import serializers
from estateApp.models import ClientUser


# =============================================================================
# OVERVIEW TAB SERIALIZERS
# =============================================================================

class ContactInfoSerializer(serializers.Serializer):
    """Contact information section in left column"""
    email = serializers.EmailField(allow_null=True)
    phone = serializers.CharField(allow_null=True, allow_blank=True)
    company = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)


class ProfileStatsSerializer(serializers.Serializer):
    """Quick stats section (properties count, total invested)"""
    properties_count = serializers.IntegerField()
    total_investment = serializers.DecimalField(max_digits=18, decimal_places=2)


class BestPerformingEstateSerializer(serializers.Serializer):
    """Best performing estate data for the trophy card"""
    estate_name = serializers.CharField()
    growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    location = serializers.CharField(allow_null=True)
    company_name = serializers.CharField(allow_null=True)


class PortfolioSummarySerializer(serializers.Serializer):
    """Portfolio summary stats for overview tab"""
    current_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_investment = serializers.DecimalField(max_digits=18, decimal_places=2)
    appreciation_total = serializers.DecimalField(max_digits=18, decimal_places=2)
    average_growth = serializers.DecimalField(max_digits=10, decimal_places=2)
    best_performing_estate = BestPerformingEstateSerializer(allow_null=True)


class ProfileDetailsSerializer(serializers.Serializer):
    """Profile details table in overview tab"""
    full_name = serializers.CharField()
    company = serializers.CharField(allow_null=True, allow_blank=True)
    job = serializers.CharField(allow_null=True, allow_blank=True)
    country = serializers.CharField(allow_null=True, allow_blank=True)
    date_registered = serializers.DateTimeField()
    about = serializers.CharField(allow_null=True, allow_blank=True)


class ClientProfileOverviewSerializer(serializers.Serializer):
    """
    Complete serializer for Profile Overview Tab
    Combines: avatar, contact info, profile details, stats, portfolio summary
    """
    # User identification
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    profile_image_url = serializers.SerializerMethodField()
    role = serializers.CharField(default='Real Estate Investor')
    
    # Contact info
    contact_info = ContactInfoSerializer()
    
    # Profile details
    profile_details = ProfileDetailsSerializer()
    
    # Stats
    stats = ProfileStatsSerializer()
    
    # Portfolio summary
    portfolio = PortfolioSummarySerializer()

    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if obj.get('profile_image'):
            if request:
                return request.build_absolute_uri(f'/secure-profile-image/{obj["id"]}/')
            return f'/secure-profile-image/{obj["id"]}/'
        return None


# =============================================================================
# EDIT PROFILE TAB SERIALIZERS
# =============================================================================

class ProfileEditSerializer(serializers.ModelSerializer):
    """Serializer for editing profile - Edit Profile Tab"""
    
    class Meta:
        model = ClientUser
        fields = [
            'id', 'title', 'full_name', 'email', 'date_of_birth', 'about',
            'phone', 'country', 'address', 'company', 'job'
        ]
        read_only_fields = ['id', 'email']  # Email cannot be changed

    def validate_full_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value.strip()


class ProfileImageUploadSerializer(serializers.Serializer):
    """Serializer for profile image upload"""
    profile_image = serializers.ImageField(required=True)

    def validate_profile_image(self, value):
        # Max 2MB
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Image file too large. Maximum size is 2MB.")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Invalid image format. Use JPG, PNG, or GIF.")
        
        return value


# =============================================================================
# PASSWORD TAB SERIALIZERS
# =============================================================================

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change - Password Tab"""
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, min_length=8, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        """Validate password requirements"""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "New password and confirmation do not match."
            })
        return attrs
    
    # Company info
    company_name = serializers.CharField(allow_null=True)
