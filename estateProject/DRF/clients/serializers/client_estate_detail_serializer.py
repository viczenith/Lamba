"""
Client Estate Detail Serializers
=================================
DRF Serializers for the client estate detail page (client_estate_detail.html)

This module provides secure serializers for estate information displayed to clients:
- Estate header (name, location, size, title deed)
- Progress status updates with timeline
- Amenities with icons
- Prototypes filtered by plot size
- Estate layouts with zoom capability
- Floor plans filtered by plot size
- Google Maps integration

SECURITY IMPLEMENTATIONS:
1. Read-only fields to prevent data modification
2. Minimal data exposure - only necessary fields serialized
3. Secure image URLs through protected endpoints
4. Company isolation for multi-tenant security
5. Plot size filtering to prevent unauthorized data access
6. No sensitive business data exposed (prices, internal IDs, etc.)
7. Input sanitization and validation
8. XSS prevention through proper escaping

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework import serializers
from django.urls import reverse
from django.utils.html import escape
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY UTILITY FUNCTIONS
# =============================================================================

def sanitize_string(value):
    """
    Sanitize string values to prevent XSS attacks.
    Always escape HTML special characters in user-facing data.
    """
    if value is None:
        return None
    return escape(str(value))


def build_secure_url(request, url_name, **kwargs):
    """
    Build absolute URL with proper security checks.
    Returns None if request is invalid.
    """
    if not request:
        return None
    try:
        return request.build_absolute_uri(reverse(url_name, kwargs=kwargs))
    except Exception as e:
        logger.warning(f"Failed to build URL for {url_name}: {e}")
        return None


# =============================================================================
# NESTED SERIALIZERS - MINIMAL DATA EXPOSURE
# =============================================================================

class CompanyMinimalSerializer(serializers.Serializer):
    """
    Minimal company info to prevent data leakage.
    SECURITY: Expose ID, name and an optional `company_logo` URL for client thumbnails.
    """
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.SerializerMethodField()
    company_logo = serializers.SerializerMethodField()

    def get_company_name(self, obj):
        """Sanitize company name to prevent XSS."""
        name = getattr(obj, 'company_name', None)
        return sanitize_string(name)

    def get_company_logo(self, obj):
        request = self.context.get('request') if isinstance(self.context, dict) else None
        try:
            if getattr(obj, 'logo', None):
                if request:
                    return request.build_absolute_uri(reverse('secure-company-logo', kwargs={'company_id': obj.id}))
                return getattr(obj, 'logo', None)
        except Exception:
            return getattr(obj, 'logo', None)
        return None


class PlotSizeSerializer(serializers.Serializer):
    """
    Plot size information for client display.
    SECURITY: Read-only, no modification allowed.
    """
    id = serializers.IntegerField(read_only=True)
    size = serializers.SerializerMethodField()

    def get_size(self, obj):
        """Sanitize size value."""
        size = getattr(obj, 'size', None)
        return sanitize_string(size)


class ProgressStatusSerializer(serializers.Serializer):
    """
    Progress status updates with formatted timestamps.
    SECURITY: Read-only fields, sanitized content.
    """
    id = serializers.IntegerField(read_only=True)
    progress_status = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(read_only=True, format="%b %d, %Y")
    # Additional field for precise timestamp if needed
    timestamp_iso = serializers.DateTimeField(
        source='timestamp', 
        read_only=True, 
        format="%Y-%m-%dT%H:%M:%SZ"
    )

    def get_progress_status(self, obj):
        """Sanitize progress status text."""
        status = getattr(obj, 'progress_status', None)
        return sanitize_string(status)


class AmenityItemSerializer(serializers.Serializer):
    """
    Individual amenity with display name and icon.
    SECURITY: Validated icon classes, sanitized names.
    """
    display_name = serializers.CharField(read_only=True)
    icon_class = serializers.SerializerMethodField()

    # Whitelist of allowed Bootstrap icons for security
    ALLOWED_ICON_CLASSES = {
        'bi-shield-lock', 'bi-camera-video', 'bi-lightning-charge-fill',
        'bi-droplet-fill', 'bi-building', 'bi-water', 'bi-barbell',
        'bi-trophy', 'bi-emoji-smile', 'bi-mortarboard', 'bi-hospital',
        'bi-shop', 'bi-house', 'bi-tree', 'bi-car-front-fill',
        'bi-briefcase', 'bi-wifi', 'bi-house-door-fill', ''
    }

    def get_icon_class(self, obj):
        """
        Validate and return icon class.
        SECURITY: Only allow whitelisted icon classes.
        """
        icon = obj.get('icon_class', '') if isinstance(obj, dict) else getattr(obj, 'icon_class', '')
        if icon in self.ALLOWED_ICON_CLASSES:
            return icon
        return ''  # Return empty string for invalid icons


class EstateAmenityWrapperSerializer(serializers.Serializer):
    """
    Estate amenities wrapper that extracts amenity list.
    SECURITY: Validates and sanitizes all amenity data.
    """
    amenities = serializers.SerializerMethodField()

    def get_amenities(self, obj):
        """
        Extract and validate amenities from estate amenity record.
        Uses the model's get_amenity_display() method.
        """
        try:
            amenities_list = obj.get_amenity_display() if hasattr(obj, 'get_amenity_display') else []
            if amenities_list:
                validated_amenities = []
                for name, icon in amenities_list:
                    validated_amenities.append({
                        'display_name': sanitize_string(name),
                        'icon_class': icon if icon in AmenityItemSerializer.ALLOWED_ICON_CLASSES else ''
                    })
                return validated_amenities
        except Exception as e:
            logger.warning(f"Error processing amenities: {e}")
        return []


class PrototypeSerializer(serializers.Serializer):
    """
    Prototype with secure image URL.
    SECURITY: 
    - Images served through authenticated endpoint
    - No direct file paths exposed
    - All text fields sanitized
    """
    id = serializers.IntegerField(read_only=True)
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    date_uploaded = serializers.DateTimeField(read_only=True, format="%b %d, %Y")
    date_uploaded_iso = serializers.DateTimeField(
        source='date_uploaded',
        read_only=True, 
        format="%Y-%m-%dT%H:%M:%SZ"
    )
    plot_size_id = serializers.IntegerField(source='plot_size.id', read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_title(self, obj):
        """Sanitize prototype title."""
        title = getattr(obj, 'Title', None)
        return sanitize_string(title)

    def get_description(self, obj):
        """Sanitize prototype description."""
        description = getattr(obj, 'Description', None)
        return sanitize_string(description)

    def get_image_url(self, obj):
        """
        Generate secure image URL through protected endpoint.
        SECURITY: Image served through authenticated view, not direct file access.
        """
        request = self.context.get('request')
        if request and obj.id:
            # Use DRF API endpoint for secure access
            try:
                return request.build_absolute_uri(
                    reverse('api-secure-prototype-image', kwargs={'prototype_id': obj.id})
                )
            except Exception:
                # Fallback to web endpoint
                return build_secure_url(
                    request, 
                    'secure-prototype-image', 
                    prototype_id=obj.id
                )
        return None


class EstateLayoutSerializer(serializers.Serializer):
    """
    Estate layout with secure image URL.
    SECURITY: Protected image serving with access validation.
    """
    id = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        """
        Generate secure layout image URL.
        SECURITY: Image served through authenticated view.
        """
        request = self.context.get('request')
        if request and obj.id:
            try:
                return request.build_absolute_uri(
                    reverse('api-secure-estate-layout', kwargs={'layout_id': obj.id})
                )
            except Exception:
                return build_secure_url(
                    request, 
                    'secure-estate-layout', 
                    layout_id=obj.id
                )
        return None


class FloorPlanSerializer(serializers.Serializer):
    """
    Floor plan with secure image URL.
    SECURITY: 
    - Protected image serving
    - Plot size filtering enforced
    - Sanitized titles
    """
    id = serializers.IntegerField(read_only=True)
    plan_title = serializers.SerializerMethodField()
    date_uploaded = serializers.DateTimeField(read_only=True, format="%b %d, %Y")
    plot_size_id = serializers.IntegerField(source='plot_size.id', read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_plan_title(self, obj):
        """Sanitize floor plan title."""
        title = getattr(obj, 'plan_title', None)
        return sanitize_string(title)

    def get_image_url(self, obj):
        """
        Generate secure floor plan image URL.
        SECURITY: Image served through authenticated view.
        """
        request = self.context.get('request')
        if request and obj.id:
            try:
                return request.build_absolute_uri(
                    reverse('api-secure-floor-plan', kwargs={'plan_id': obj.id})
                )
            except Exception:
                return build_secure_url(
                    request, 
                    'secure-floor-plan', 
                    plan_id=obj.id
                )
        return None


class EstateMapSerializer(serializers.Serializer):
    """
    Map with Google Maps embed link.
    SECURITY: 
    - Only expose generated map link, not raw coordinates
    - Validate URL format
    """
    id = serializers.IntegerField(read_only=True)
    google_map_link = serializers.SerializerMethodField()
    # Optionally expose coordinates for client-side map rendering
    has_coordinates = serializers.SerializerMethodField()

    def get_google_map_link(self, obj):
        """
        Get Google Maps embed link from model property.
        SECURITY: URL is generated server-side, validated.
        """
        if hasattr(obj, 'generate_google_map_link'):
            link = obj.generate_google_map_link
            # Basic URL validation
            if link and (link.startswith('https://www.google.com/maps') or 
                        link.startswith('https://maps.google.com')):
                return link
        return None

    def get_has_coordinates(self, obj):
        """Check if map has valid coordinates."""
        return bool(
            getattr(obj, 'latitude', None) and 
            getattr(obj, 'longitude', None)
        )


# =============================================================================
# MAIN CLIENT ESTATE DETAIL SERIALIZER
# =============================================================================

class ClientEstateDetailSerializer(serializers.Serializer):
    """
    Main serializer for client estate detail page.
    
    SECURITY IMPLEMENTATIONS:
    1. All fields are read-only - no modification through API
    2. Only exposes data the client is authorized to see
    3. Images served through secure, authenticated endpoints
    4. Prototypes and floor plans filtered by client's plot size
    5. No sensitive internal data exposed (prices, financials, etc.)
    6. All text content sanitized against XSS
    7. Company data minimized to prevent leakage
    8. Navigation URLs generated server-side
    
    USAGE:
        serializer = ClientEstateDetailSerializer(
            estate,
            context={
                'request': request,
                'plot_size': plot_size,
                'floor_plans': floor_plans,
                'client_profile': client_profile,  # For additional validation
            }
        )
    """
    # Basic estate information
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    estate_size = serializers.SerializerMethodField()
    estate_size_unit = serializers.SerializerMethodField()
    title_deed = serializers.SerializerMethodField()
    
    # Nested data
    company = CompanyMinimalSerializer(read_only=True)
    plot_size = serializers.SerializerMethodField()
    progress_updates = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    prototypes = serializers.SerializerMethodField()
    estate_layouts = serializers.SerializerMethodField()
    floor_plans = serializers.SerializerMethodField()
    maps = serializers.SerializerMethodField()
    
    # Navigation URLs (generated server-side for security)
    navigation = serializers.SerializerMethodField()
    
    # Metadata
    last_updated = serializers.SerializerMethodField()

    def get_name(self, obj):
        """Sanitize estate name."""
        return sanitize_string(getattr(obj, 'name', None))

    def get_location(self, obj):
        """Sanitize estate location."""
        return sanitize_string(getattr(obj, 'location', None))

    def get_estate_size(self, obj):
        """
        Format estate size for display.
        SECURITY: Convert to string to prevent type confusion.
        """
        size = getattr(obj, 'estate_size', None)
        if size is not None:
            return str(size)
        return None

    def get_estate_size_unit(self, obj):
        """Get estate size unit."""
        unit = getattr(obj, 'estate_size_unit', None)
        return sanitize_string(unit)

    def get_title_deed(self, obj):
        """Sanitize title deed value."""
        deed = getattr(obj, 'title_deed', None)
        return sanitize_string(deed)

    def get_plot_size(self, obj):
        """
        Get plot size information.
        SECURITY: Only return the plot size the client has access to.
        """
        plot_size = self.context.get('plot_size')
        if plot_size:
            return PlotSizeSerializer(plot_size).data
        return None

    def get_progress_updates(self, obj):
        """
        Get progress status updates.
        SECURITY: All updates are read-only and sanitized.
        """
        try:
            progress_statuses = obj.progress_status.all().order_by('-timestamp')
            return ProgressStatusSerializer(progress_statuses, many=True).data
        except Exception as e:
            logger.warning(f"Error fetching progress updates for estate {obj.id}: {e}")
            return []

    def get_amenities(self, obj):
        """
        Get estate amenities as flat list.
        SECURITY: All amenity data validated and sanitized.
        """
        amenities_data = []
        try:
            for amenity_record in obj.estate_amenity.all():
                serializer = EstateAmenityWrapperSerializer(amenity_record)
                amenities_data.extend(serializer.data.get('amenities', []))
        except Exception as e:
            logger.warning(f"Error fetching amenities for estate {obj.id}: {e}")
        return amenities_data

    def get_prototypes(self, obj):
        """
        Get prototypes filtered by client's plot size.
        
        SECURITY:
        - Only returns prototypes for the client's specific plot size
        - Prevents data leakage of other plot size prototypes
        - Images served through secure endpoints
        """
        plot_size = self.context.get('plot_size')
        if not plot_size:
            return []
        
        try:
            # SECURITY: Filter prototypes by plot size to prevent unauthorized access
            filtered_prototypes = obj.prototypes.filter(
                plot_size_id=plot_size.id
            ).order_by('-date_uploaded')
            
            return PrototypeSerializer(
                filtered_prototypes, 
                many=True, 
                context=self.context
            ).data
        except Exception as e:
            logger.warning(f"Error fetching prototypes for estate {obj.id}: {e}")
            return []

    def get_estate_layouts(self, obj):
        """
        Get estate layouts.
        SECURITY: Images served through authenticated endpoint.
        """
        try:
            layouts = obj.estate_layout.all()
            return EstateLayoutSerializer(
                layouts, 
                many=True, 
                context=self.context
            ).data
        except Exception as e:
            logger.warning(f"Error fetching layouts for estate {obj.id}: {e}")
            return []

    def get_floor_plans(self, obj):
        """
        Get floor plans filtered by plot size.
        
        SECURITY:
        - Floor plans pre-filtered by view based on plot size access
        - Prevents access to floor plans for other plot sizes
        """
        floor_plans = self.context.get('floor_plans', [])
        if not floor_plans:
            return []
        
        return FloorPlanSerializer(
            floor_plans, 
            many=True, 
            context=self.context
        ).data

    def get_maps(self, obj):
        """
        Get estate maps.
        SECURITY: Only embed links exposed, not raw coordinate data in detail.
        """
        try:
            maps = obj.map.all()
            return EstateMapSerializer(maps, many=True).data
        except Exception as e:
            logger.warning(f"Error fetching maps for estate {obj.id}: {e}")
            return []

    def get_navigation(self, obj):
        """
        Generate navigation URLs server-side.
        SECURITY: URLs generated server-side to prevent tampering.
        """
        request = self.context.get('request')
        navigation = {
            'dashboard_url': None,
            'portfolio_url': None,
            'back_url': None,
        }
        
        if request:
            try:
                navigation['dashboard_url'] = request.build_absolute_uri(
                    reverse('secure-client-dashboard')
                )
            except Exception:
                pass
            
            if obj.company:
                try:
                    navigation['portfolio_url'] = request.build_absolute_uri(
                        reverse('my-company-portfolio', kwargs={'company_id': obj.company.id})
                    )
                    # Back button goes to portfolio with anchor
                    navigation['back_url'] = f"{navigation['portfolio_url']}#properties-pane"
                except Exception:
                    pass
        
        return navigation

    def get_last_updated(self, obj):
        """
        Get last update timestamp.
        Useful for client-side caching decisions.
        """
        try:
            # Get most recent progress update
            latest_progress = obj.progress_status.order_by('-timestamp').first()
            if latest_progress:
                return latest_progress.timestamp.isoformat()
        except Exception:
            pass
        
        # Fall back to estate date_added
        date_added = getattr(obj, 'date_added', None)
        if date_added:
            return date_added.isoformat()
        return None


# =============================================================================
# RESPONSE WRAPPER SERIALIZER (for consistent API responses)
# =============================================================================

class ClientEstateDetailResponseSerializer(serializers.Serializer):
    """
    Wrapper serializer for consistent API response format.
    
    Response structure:
    {
        "success": true,
        "data": { ... estate detail ... },
        "meta": {
            "cached": false,
            "timestamp": "..."
        }
    }
    """
    success = serializers.BooleanField(default=True, read_only=True)
    data = ClientEstateDetailSerializer(source='*', read_only=True)
    meta = serializers.SerializerMethodField()

    def get_meta(self, obj):
        """Return metadata about the response."""
        from django.utils import timezone
        return {
            'cached': False,
            'timestamp': timezone.now().isoformat(),
            'api_version': '2.0'
        }


# =============================================================================
# ERROR RESPONSE SERIALIZER
# =============================================================================

class ErrorResponseSerializer(serializers.Serializer):
    """
    Standardized error response serializer.
    SECURITY: Never expose internal error details to clients.
    """
    success = serializers.BooleanField(default=False, read_only=True)
    error = serializers.CharField(read_only=True)
    error_code = serializers.CharField(read_only=True, required=False)
    
    # Optional field for validation errors
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
        read_only=True
    )
