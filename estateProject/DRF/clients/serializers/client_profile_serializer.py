"""
Client Profile Serializers for HTML Page Tabs
==============================================
Maps all HTML sections:
- LEFT COLUMN: Avatar, profile name/role badge, stats, contact info
- RIGHT COLUMN OVERVIEW TAB: About section, profile details table, portfolio summary
- RIGHT COLUMN EDIT PROFILE TAB: Photo upload, personal/contact/work details
- RIGHT COLUMN PASSWORD TAB: Current/new/confirm password with validation
"""

from rest_framework import serializers
from estateApp.models import ClientUser


# =============================================================================
# LEFT COLUMN SERIALIZERS
# =============================================================================

class ProfileAvatarSerializer(serializers.Serializer):
    """Profile avatar section - left column"""
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    profile_image = serializers.URLField(allow_null=True, allow_blank=True)
    role = serializers.CharField(default='Real Estate Investor')
    
    class Meta:
        fields = ['id', 'full_name', 'profile_image', 'role']


class ProfileStatsSerializer(serializers.Serializer):
    """Quick stats - left column (properties count, total invested)"""
    properties_count = serializers.IntegerField(default=0)
    total_investment = serializers.DecimalField(max_digits=18, decimal_places=2, default=0)


class ContactInfoSerializer(serializers.Serializer):
    """Contact info card - left column (email, phone, company, address)"""
    email = serializers.EmailField(allow_null=True, allow_blank=True)
    phone = serializers.CharField(allow_null=True, allow_blank=True)
    company = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)


# =============================================================================
# OVERVIEW TAB SERIALIZERS
# =============================================================================

class ProfileDetailsTableSerializer(serializers.Serializer):
    """
    Profile details table in overview tab:
    - Full Name
    - Company
    - Job Title
    - Country
    - Joined Since
    """
    full_name = serializers.CharField()
    company = serializers.CharField(allow_null=True, allow_blank=True)
    job = serializers.CharField(allow_null=True, allow_blank=True)
    country = serializers.CharField(allow_null=True, allow_blank=True)
    date_registered = serializers.DateTimeField()


class BestPerformingEstateSerializer(serializers.Serializer):
    """
    Best performing estate card (trophy card) in portfolio summary:
    - Estate name
    - Growth rate percentage
    - Location
    - Company name
    """
    highest_growth_estate = serializers.CharField()
    highest_growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2)
    highest_growth_location = serializers.CharField(allow_null=True, allow_blank=True)
    highest_growth_company = serializers.CharField(allow_null=True, allow_blank=True)


class PortfolioSummarySerializer(serializers.Serializer):
    """
    Portfolio Summary section in overview tab:
    - Current Value (stat tile 1)
    - Portfolio Growth % (stat tile 2)
    - Total Appreciation (stat tile 3)
    - Best Performing Estate card
    """
    current_value = serializers.DecimalField(max_digits=18, decimal_places=2, default=0)
    average_growth = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    appreciation_total = serializers.DecimalField(max_digits=18, decimal_places=2, default=0)
    highest_growth_estate = BestPerformingEstateSerializer(allow_null=True)


class ClientProfileOverviewSerializer(serializers.Serializer):
    """
    Complete serializer for OVERVIEW TAB
    Combines:
    - About section (if present)
    - Profile details table
    - Portfolio summary section
    """
    # Profile identification & about
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    about = serializers.CharField(allow_null=True, allow_blank=True)
    
    # Profile details for table
    company = serializers.CharField(allow_null=True, allow_blank=True)
    job = serializers.CharField(allow_null=True, allow_blank=True)
    country = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)
    date_registered = serializers.DateTimeField()
    
    # Left column stats
    profile_stats = ProfileStatsSerializer()
    
    # Portfolio summary (with best estate)
    portfolio_summary = PortfolioSummarySerializer()


# =============================================================================
# EDIT PROFILE TAB SERIALIZERS
# =============================================================================

class PersonalDetailsEditSerializer(serializers.Serializer):
    """
    Personal Details section in Edit Profile tab:
    - Title (dropdown)
    - Full Name
    - Email (read-only)
    - Date of Birth
    - About Me (textarea)
    """
    title = serializers.CharField(allow_null=True, allow_blank=True)
    full_name = serializers.CharField()
    email = serializers.EmailField(read_only=True)
    date_of_birth = serializers.DateField(allow_null=True)
    about = serializers.CharField(allow_null=True, allow_blank=True)

    def validate_full_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value.strip()


class ContactDetailsEditSerializer(serializers.Serializer):
    """
    Contact Information section in Edit Profile tab:
    - Phone Number
    - Country
    - Address
    """
    phone = serializers.CharField(allow_null=True, allow_blank=True)
    country = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)


class WorkDetailsEditSerializer(serializers.Serializer):
    """
    Work Information section in Edit Profile tab:
    - Company
    - Job Title
    """
    company = serializers.CharField(allow_null=True, allow_blank=True)
    job = serializers.CharField(allow_null=True, allow_blank=True)


class ProfilePhotoUploadSerializer(serializers.Serializer):
    """
    Profile Photo Upload section in Edit Profile tab
    Max 2MB, formats: JPG, PNG, GIF
    """
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


class ClientProfileEditSerializer(serializers.ModelSerializer):
    """
    Complete serializer for EDIT PROFILE TAB
    Combines:
    - Profile photo upload
    - Personal details (title, full name, email, DOB, about)
    - Contact information (phone, country, address)
    - Work information (company, job)
    """
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = ClientUser
        fields = [
            'id', 'profile_image', 'title', 'full_name', 'email',
            'date_of_birth', 'about', 'phone', 'country', 'address',
            'company', 'job'
        ]
        read_only_fields = ['id', 'email']

    def validate_profile_image(self, value):
        if value:
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError("Image file too large. Maximum size is 2MB.")
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Invalid image format. Use JPG, PNG, or GIF.")
        return value

    def validate_full_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value.strip()


# =============================================================================
# PASSWORD TAB SERIALIZERS
# =============================================================================

class ChangePasswordSerializer(serializers.Serializer):
    """
    Complete serializer for PASSWORD TAB
    Password change form with validation:
    - Current Password
    - New Password (min 8 chars, 1 uppercase, 1 number)
    - Confirm New Password
    """
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        if not value:
            raise serializers.ValidationError("Current password is required.")
        return value

    def validate_new_password(self, value):
        """
        Validate new password requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one number
        """
        if not value or len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number.")
        return value

    def validate(self, attrs):
        """Ensure new password and confirmation match"""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "New password and confirmation do not match."
            })
        return attrs


# =============================================================================
# COMPLETE PAGE SERIALIZER (Optional - for full-page response)
# =============================================================================

class ClientProfileCompleteSerializer(serializers.Serializer):
    """
    Complete client profile page response combining:
    - Left column (avatar, stats, contact)
    - Overview tab data
    - Edit profile tab data
    - Password tab (methods only, no data)
    """
    # Left column
    avatar = ProfileAvatarSerializer()
    stats = ProfileStatsSerializer()
    contact = ContactInfoSerializer()
    
    # Right column - overview tab
    profile_details = ProfileDetailsTableSerializer()
    portfolio_summary = PortfolioSummarySerializer()
    about = serializers.CharField(allow_null=True, allow_blank=True)

