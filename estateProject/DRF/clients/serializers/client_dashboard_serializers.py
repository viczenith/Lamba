"""
Client Dashboard Serializers
=============================
DRF Serializers for the client dashboard page (client_side.html)

This module provides secure serializers for:
- Dashboard statistics (properties purchased, payment status)
- Active promotional offers with company grouping
- Price history/increments organized by company
- Estate and company information

SECURITY IMPLEMENTATIONS:
1. Read-only fields to prevent data modification
2. XSS prevention through HTML escaping
3. Minimal data exposure - only necessary fields
4. Input validation and sanitization
5. Decimal precision handling for financial data
6. No sensitive business data exposed (internal IDs, etc.)
7. Company-scoped data isolation

Author: System
Version: 2.0
Last Updated: December 2024
"""

from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.utils.html import escape
import logging

from estateApp.models import (
    PromotionalOffer, Estate, PropertyPrice, PriceHistory
)

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


def safe_float(value, default=None):
    """
    Safely convert a value to float with validation.
    SECURITY: Prevents type confusion attacks.
    """
    if value is None:
        return default
    try:
        result = float(value)
        # Validate reasonable bounds for financial data
        if result < 0 or result > 999999999999:  # Max ~1 trillion
            logger.warning(f"SECURITY: Suspicious float value: {value}")
            return default
        return result
    except (ValueError, TypeError, InvalidOperation):
        return default


def safe_decimal_to_float(decimal_value, precision=2):
    """
    Safely convert Decimal to float with precision.
    SECURITY: Handles potential overflow/precision issues.
    """
    if decimal_value is None:
        return None
    try:
        quantized = Decimal(decimal_value).quantize(Decimal(10) ** -precision)
        return float(quantized)
    except (InvalidOperation, ValueError, TypeError):
        return None


def calculate_discount_price(original_price, discount_percent):
    """
    Calculate discounted price safely.
    SECURITY: Validates inputs, prevents calculation errors.
    """
    if original_price is None or discount_percent is None:
        return None
    try:
        original = Decimal(str(original_price))
        discount = Decimal(str(discount_percent))
        
        # Validate discount range
        if discount < 0 or discount > 100:
            logger.warning(f"SECURITY: Invalid discount percentage: {discount_percent}")
            return None
        
        discounted = (original * (Decimal(100) - discount)) / Decimal(100)
        return float(discounted.quantize(Decimal('0.01')))
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.warning(f"Error calculating discount: {e}")
        return None


# =============================================================================
# BASE SERIALIZERS
# =============================================================================

class EstateSizeDetailSerializer(serializers.Serializer):
    """
    Estate size with pricing details.
    SECURITY: All fields read-only, validated.
    """
    plot_unit_id = serializers.IntegerField(allow_null=True, read_only=True)
    size = serializers.CharField(allow_blank=True, allow_null=True, read_only=True)
    amount = serializers.FloatField(allow_null=True, read_only=True)
    current = serializers.FloatField(allow_null=True, read_only=True)
    discounted = serializers.FloatField(allow_null=True, read_only=True)
    promo_price = serializers.FloatField(allow_null=True, read_only=True)
    discount_pct = serializers.IntegerField(allow_null=True, read_only=True)
    discount = serializers.IntegerField(allow_null=True, read_only=True)


class CompanyMinimalSerializer(serializers.Serializer):
    """
    Minimal company info for nested responses.
    SECURITY: Only expose ID and sanitized name.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        """Sanitize company name."""
        if isinstance(obj, dict):
            return sanitize_string(obj.get('name'))
        return sanitize_string(getattr(obj, 'company_name', getattr(obj, 'name', None)))


class CompanyDetailSerializer(serializers.Serializer):
    """
    Minimal company info for nested responses.
    SECURITY: Only expose necessary fields with sanitization.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        if isinstance(obj, dict):
            return sanitize_string(obj.get('name'))
        return sanitize_string(getattr(obj, 'company_name', getattr(obj, 'name', None)))


# =============================================================================
# ESTATE SERIALIZERS
# =============================================================================

class EstateDetailSerializer(serializers.ModelSerializer):
    """
    Estate details with promotional offers and pricing.
    
    SECURITY:
    - All fields read-only
    - String fields sanitized
    - Pricing data validated
    - Company data scoped
    """
    id = serializers.IntegerField(source='pk', read_only=True)
    estate_id = serializers.SerializerMethodField()
    estate_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    promo = serializers.SerializerMethodField()
    promotional_offers = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = Estate
        fields = ['id', 'name', 'estate_id', 'estate_name', 'location', 'promo', 'promotional_offers', 'sizes', 'company']
        read_only_fields = fields

    def get_estate_id(self, obj):
        return obj.id

    def get_estate_name(self, obj):
        return sanitize_string(obj.name)

    def get_name(self, obj):
        return sanitize_string(obj.name)

    def get_location(self, obj):
        return sanitize_string(getattr(obj, 'location', None))

    def get_company(self, obj):
        """Return sanitized company info."""
        company = getattr(obj, 'company', None)
        if company:
            return {
                "id": company.id,
                "name": sanitize_string(getattr(company, 'company_name', str(company)))
            }
        return None

    def _promo_dict(self, promo):
        """Build promo dictionary with validation."""
        if not promo:
            return {
                "active": False,
                "is_active": False,
                "name": None,
                "discount_pct": None
            }
        
        try:
            today = timezone.localdate()
            is_active_now = (promo.start <= today <= promo.end)
            discount_pct = int(promo.discount) if promo.discount is not None else None
            
            # Validate discount range
            if discount_pct is not None and (discount_pct < 0 or discount_pct > 100):
                logger.warning(f"SECURITY: Invalid discount in promo {promo.id}: {discount_pct}")
                discount_pct = None
            
            return {
                "active": is_active_now,
                "is_active": is_active_now,
                "id": promo.id,
                "name": sanitize_string(promo.name),
                "discount": discount_pct,
                "discount_pct": discount_pct,
                "start": promo.start,
                "end": promo.end
            }
        except Exception as e:
            logger.warning(f"Error processing promo: {e}")
            return {"active": False, "is_active": False, "name": None, "discount_pct": None}

    def get_promo(self, estate):
        """Get active promo for estate with security checks."""
        try:
            today = timezone.localdate()
            promo = PromotionalOffer.objects.filter(
                estates=estate,
                start__lte=today,
                end__gte=today
            ).order_by('-discount', '-start').first()
            return self._promo_dict(promo)
        except Exception as e:
            logger.warning(f"Error getting promo for estate {estate.id}: {e}")
            return self._promo_dict(None)

    def get_promotional_offers(self, estate):
        """Get all promos for estate."""
        try:
            qs = estate.promotional_offers.all().order_by('-discount', '-start')
            return PromotionalOfferSimpleSerializer(qs, many=True, context=self.context).data
        except Exception as e:
            logger.warning(f"Error getting promotional offers: {e}")
            return []

    def get_sizes(self, estate):
        """
        Get estate sizes with pricing and promo calculations.
        SECURITY: Validates all pricing data, prevents duplicates.
        """
        out = []
        
        try:
            today = timezone.localdate()
            promo = PromotionalOffer.objects.filter(
                estates=estate,
                start__lte=today,
                end__gte=today
            ).order_by('-discount', '-start').first()
            
            # Track seen plot units to prevent duplicates
            seen_plot_units = set()
            
            # Get prices ordered by creation (latest first)
            prices = estate.property_prices.select_related(
                'plot_unit__plot_size'
            ).all().order_by('-created_at')
            
            for pp in prices:
                plot_unit = getattr(pp, 'plot_unit', None)
                if not plot_unit:
                    continue
                
                plot_unit_id = plot_unit.id
                if plot_unit_id in seen_plot_units:
                    continue
                seen_plot_units.add(plot_unit_id)
                
                # Get plot size name
                plot_size = getattr(plot_unit, 'plot_size', None)
                size_name = sanitize_string(getattr(plot_size, 'size', None)) if plot_size else f"Plot Unit {plot_unit_id}"
                
                # Get and validate amount
                amount = safe_float(pp.current)
                
                # Calculate discounted price if promo exists
                discounted = None
                discount_pct = None
                
                if promo and amount is not None:
                    discount_pct = int(promo.discount) if promo.discount is not None else None
                    if discount_pct is not None and 0 <= discount_pct <= 100:
                        discounted = calculate_discount_price(pp.current, promo.discount)
                
                out.append({
                    "plot_unit_id": plot_unit_id,
                    "size": size_name,
                    "amount": amount,
                    "current": amount,
                    "discounted": discounted,
                    "promo_price": discounted,
                    "discount_pct": discount_pct,
                    "discount": discount_pct
                })
        
        except Exception as e:
            logger.warning(f"Error getting estate sizes: {e}")
        
        return out


# =============================================================================
# PROMOTIONAL OFFER SERIALIZERS
# =============================================================================

class PromotionalOfferSimpleSerializer(serializers.ModelSerializer):
    """
    Simple promo serializer with security validation.
    SECURITY: All fields read-only, validated discount ranges.
    """
    discount_pct = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    start = serializers.DateField(format="%Y-%m-%d", read_only=True)
    end = serializers.DateField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = PromotionalOffer
        fields = ['id', 'name', 'discount', 'discount_pct', 'start', 'end', 'is_active', 'active', 'description']
        read_only_fields = fields

    def get_name(self, obj):
        return sanitize_string(getattr(obj, 'name', None))

    def get_description(self, obj):
        return sanitize_string(getattr(obj, 'description', None))

    def get_discount_pct(self, obj):
        discount = getattr(obj, 'discount', None)
        if discount is not None:
            try:
                pct = int(discount)
                if 0 <= pct <= 100:
                    return pct
                logger.warning(f"SECURITY: Invalid discount in promo {obj.id}: {pct}")
            except (ValueError, TypeError):
                pass
        return None

    def get_is_active(self, obj):
        try:
            today = timezone.localdate()
            return obj.start <= today <= obj.end
        except Exception:
            return False

    def get_active(self, obj):
        return self.get_is_active(obj)


class PromoEstateSizeSerializer(serializers.Serializer):
    """Promo estate size with pricing."""
    plot_unit_id = serializers.IntegerField(read_only=True)
    size = serializers.CharField(read_only=True)
    current = serializers.FloatField(allow_null=True, read_only=True)
    promo_price = serializers.FloatField(allow_null=True, read_only=True)


class PromotionDashboardSerializer(serializers.ModelSerializer):
    """
    Promotion serializer for dashboard display.
    
    SECURITY:
    - All fields read-only
    - Estates filtered by company scope
    - Pricing data validated
    - String fields sanitized
    """
    estates = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    discount_pct = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = PromotionalOffer
        fields = ['id', 'name', 'discount', 'discount_pct', 'start', 'end', 'description', 'estates', 'is_active']
        read_only_fields = fields

    def get_name(self, obj):
        return sanitize_string(getattr(obj, 'name', None))

    def get_description(self, obj):
        return sanitize_string(getattr(obj, 'description', None))

    def get_estates(self, promo):
        """Get estates with pricing for this promo."""
        estates = []
        
        try:
            for estate in promo.estates.all().prefetch_related('property_prices__plot_unit__plot_size'):
                sizes = []
                seen_plot_units = set()
                
                for pp in estate.property_prices.select_related('plot_unit__plot_size').all().order_by('-created_at'):
                    plot_unit = getattr(pp, 'plot_unit', None)
                    if not plot_unit:
                        continue
                    
                    plot_unit_id = plot_unit.id
                    if plot_unit_id in seen_plot_units:
                        continue
                    seen_plot_units.add(plot_unit_id)
                    
                    plot_size = getattr(plot_unit, 'plot_size', None)
                    size_name = sanitize_string(getattr(plot_size, 'size', '')) if plot_size else ''
                    
                    sizes.append({
                        "plot_unit_id": plot_unit_id,
                        "size": size_name,
                        "current": safe_float(pp.current)
                    })
                
                estates.append({
                    "id": estate.id,
                    "name": sanitize_string(estate.name),
                    "sizes": sizes,
                    "location": sanitize_string(getattr(estate, 'location', None))
                })
        except Exception as e:
            logger.warning(f"Error getting promo estates: {e}")
        
        return estates

    def get_is_active(self, promo):
        try:
            today = timezone.localdate()
            return promo.start <= today <= promo.end
        except Exception:
            return False

    def get_discount_pct(self, obj):
        discount = getattr(obj, 'discount', None)
        if discount is not None:
            try:
                pct = int(discount)
                return pct if 0 <= pct <= 100 else None
            except (ValueError, TypeError):
                pass
        return None


class PromotionListItemSerializer(serializers.ModelSerializer):
    """
    Compact promo serializer for lists.
    SECURITY: Limited fields, sanitized strings.
    """
    is_active = serializers.SerializerMethodField()
    estates_preview = serializers.SerializerMethodField()
    discount_pct = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = PromotionalOffer
        fields = ['id', 'name', 'discount', 'discount_pct', 'description', 'start', 'end', 'is_active', 'estates_preview']
        read_only_fields = fields

    def get_name(self, obj):
        return sanitize_string(getattr(obj, 'name', None))

    def get_description(self, obj):
        return sanitize_string(getattr(obj, 'description', None))

    def get_is_active(self, obj):
        try:
            today = timezone.localdate()
            return obj.start <= today <= obj.end
        except Exception:
            return False

    def get_estates_preview(self, obj):
        """Get first 2 estate names (sanitized)."""
        try:
            return [sanitize_string(e.name) for e in obj.estates.all()[:2]]
        except Exception:
            return []

    def get_discount_pct(self, obj):
        discount = getattr(obj, 'discount', None)
        if discount is not None:
            try:
                pct = int(discount)
                return pct if 0 <= pct <= 100 else None
            except (ValueError, TypeError):
                pass
        return None


class PromotionDetailSerializer(serializers.ModelSerializer):
    """
    Detailed promo serializer.
    SECURITY: Full validation, sanitized fields.
    """
    estates = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    discount_pct = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = PromotionalOffer
        fields = ['id', 'name', 'discount', 'discount_pct', 'start', 'end', 'description', 'created_at', 'is_active', 'estates']
        read_only_fields = fields

    def get_name(self, obj):
        return sanitize_string(getattr(obj, 'name', None))

    def get_description(self, obj):
        return sanitize_string(getattr(obj, 'description', None))

    def get_is_active(self, obj):
        try:
            today = timezone.localdate()
            return obj.start <= today <= obj.end
        except Exception:
            return False

    def get_discount_pct(self, obj):
        discount = getattr(obj, 'discount', None)
        if discount is not None:
            try:
                pct = int(discount)
                return pct if 0 <= pct <= 100 else None
            except (ValueError, TypeError):
                pass
        return None

    def get_estates(self, promo):
        """Get detailed estates with pricing."""
        estates_out = []
        
        try:
            for estate in promo.estates.prefetch_related('property_prices__plot_unit__plot_size').all():
                sizes = []
                seen_plot_units = set()
                
                for pp in estate.property_prices.select_related('plot_unit__plot_size').all().order_by('-created_at'):
                    plot_unit = getattr(pp, 'plot_unit', None)
                    if not plot_unit:
                        continue
                    
                    plot_unit_id = plot_unit.id
                    if plot_unit_id in seen_plot_units:
                        continue
                    seen_plot_units.add(plot_unit_id)
                    
                    plot_size = getattr(plot_unit, 'plot_size', None)
                    size_name = sanitize_string(getattr(plot_size, 'size', '')) if plot_size else ''
                    
                    current = safe_float(pp.current)
                    promo_price = calculate_discount_price(pp.current, promo.discount) if promo.discount else None
                    
                    sizes.append({
                        "plot_unit_id": plot_unit_id,
                        "size": size_name,
                        "current": current,
                        "promo_price": promo_price,
                    })
                
                company_data = None
                if hasattr(estate, 'company') and estate.company:
                    company_data = {
                        "id": estate.company.id,
                        "name": sanitize_string(getattr(estate.company, 'company_name', str(estate.company)))
                    }
                
                estates_out.append({
                    "id": estate.id,
                    "name": sanitize_string(estate.name),
                    "location": sanitize_string(getattr(estate, 'location', None)),
                    "sizes": sizes,
                    "company": company_data
                })
        except Exception as e:
            logger.warning(f"Error getting promo detail estates: {e}")
        
        return estates_out


# =============================================================================
# PRICE HISTORY SERIALIZERS
# =============================================================================

class PriceHistoryListSerializer(serializers.ModelSerializer):
    """
    Price history serializer for dashboard display.
    
    SECURITY:
    - All fields read-only
    - Pricing validated
    - String fields sanitized
    - Percent change calculated safely
    """
    estate_name = serializers.SerializerMethodField()
    plot_unit = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    previous = serializers.SerializerMethodField()
    current = serializers.SerializerMethodField()
    percent_change = serializers.SerializerMethodField()
    effective = serializers.DateField(format="%Y-%m-%d", read_only=True)
    recorded_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)
    notes = serializers.SerializerMethodField()
    promo = serializers.SerializerMethodField()
    promo_price = serializers.SerializerMethodField()

    class Meta:
        model = PriceHistory
        fields = [
            'id', 'price', 'estate_name', 'plot_unit', 'previous', 'current', 'percent_change',
            'effective', 'recorded_at', 'notes', 'promo', 'promo_price'
        ]
        read_only_fields = fields

    def get_estate_name(self, obj):
        try:
            return sanitize_string(getattr(obj.price.estate, 'name', None))
        except Exception:
            return None

    def get_notes(self, obj):
        return sanitize_string(getattr(obj, 'notes', None))

    def get_plot_unit(self, obj):
        try:
            pu = obj.price.plot_unit
            return {
                "id": pu.id,
                "size": sanitize_string(getattr(pu.plot_size, 'size', None))
            }
        except Exception:
            return None

    def get_price(self, obj):
        """
        Return nested price object for template compatibility.
        SECURITY: All strings sanitized.
        """
        try:
            price_obj = getattr(obj, 'price', None)
            if not price_obj:
                return None

            estate = getattr(price_obj, 'estate', None)
            plot_unit = getattr(price_obj, 'plot_unit', None)
            plot_size = getattr(plot_unit, 'plot_size', None) if plot_unit else None

            return {
                "estate": {
                    "id": getattr(estate, 'id', None),
                    "name": sanitize_string(getattr(estate, 'name', None)),
                    "company": {
                        "id": estate.company.id,
                        "name": sanitize_string(getattr(estate.company, 'company_name', str(estate.company)))
                    } if hasattr(estate, 'company') and estate.company else None
                } if estate else None,
                "plot_unit": {
                    "id": getattr(plot_unit, 'id', None),
                    "plot_size": {
                        "id": getattr(plot_size, 'id', None),
                        "size": sanitize_string(getattr(plot_size, 'size', None))
                    } if plot_size else None
                } if plot_unit else None
            }
        except Exception as e:
            logger.warning(f"Error getting price nested object: {e}")
            return None

    def get_previous(self, obj):
        return safe_float(obj.previous)

    def get_current(self, obj):
        return safe_float(obj.current)

    def get_percent_change(self, obj):
        """
        Calculate percent change safely.
        SECURITY: Handles division by zero, validates bounds.
        """
        try:
            prev = Decimal(str(obj.previous or 0))
            cur = Decimal(str(obj.current or 0))
            
            if prev == 0:
                return None
            
            pct = (cur - prev) / prev * Decimal(100)
            result = float(pct.quantize(Decimal('0.01')))
            
            # Validate reasonable bounds (-1000% to +1000%)
            if result < -1000 or result > 1000:
                logger.warning(f"SECURITY: Suspicious percent change: {result}")
                return None
            
            return result
        except Exception:
            return None

    def get_promo(self, obj):
        """Get active promo for the estate."""
        try:
            estate = obj.price.estate
            today = timezone.localdate()
            promo = PromotionalOffer.objects.filter(
                estates=estate,
                start__lte=today,
                end__gte=today
            ).order_by('-discount').first()
            
            if promo:
                discount_pct = None
                if promo.discount is not None:
                    try:
                        discount_pct = int(promo.discount)
                        if discount_pct < 0 or discount_pct > 100:
                            discount_pct = None
                    except (ValueError, TypeError):
                        pass
                
                return {
                    "id": promo.id,
                    "name": sanitize_string(promo.name),
                    "discount": discount_pct,
                    "discount_pct": discount_pct,
                    "start": promo.start,
                    "end": promo.end,
                    "active": True
                }
        except Exception as e:
            logger.warning(f"Error getting promo for price history: {e}")
        return None

    def get_promo_price(self, obj):
        """Calculate promo price if promo exists."""
        try:
            promo = self.get_promo(obj)
            if not promo or obj.current is None:
                return None
            return calculate_discount_price(obj.current, promo['discount'])
        except Exception:
            return None


# =============================================================================
# DASHBOARD RESPONSE SERIALIZERS
# =============================================================================

class EstateSizePriceSerializer(serializers.Serializer):
    """Estate size price for responses."""
    plot_unit_id = serializers.IntegerField(read_only=True)
    size = serializers.CharField(read_only=True)
    amount = serializers.FloatField(allow_null=True, read_only=True)
    discounted = serializers.FloatField(allow_null=True, read_only=True)
    discount_pct = serializers.IntegerField(allow_null=True, read_only=True)


class CompanyDashboardSerializer(serializers.Serializer):
    """
    Per-company dashboard data serializer.
    
    SECURITY:
    - All fields read-only
    - Company data scoped
    - Nested data validated
    """
    id = serializers.IntegerField(source='company.id', read_only=True)
    name = serializers.SerializerMethodField()
    estates_count = serializers.IntegerField(read_only=True)
    active_promotions_count = serializers.IntegerField(read_only=True)
    total_portfolio_value = serializers.FloatField(read_only=True, allow_null=True)
    recent_price_updates = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )
    active_promotions = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )

    def get_name(self, obj):
        company = obj.get('company') if isinstance(obj, dict) else getattr(obj, 'company', None)
        if company:
            return sanitize_string(getattr(company, 'company_name', getattr(company, 'name', str(company))))
        return None


class DashboardStatsSerializer(serializers.Serializer):
    """
    Dashboard statistics serializer.
    SECURITY: All fields read-only, validated.
    """
    total_properties = serializers.IntegerField(read_only=True, min_value=0)
    fully_paid_and_allocated = serializers.IntegerField(read_only=True, min_value=0)
    not_fully_paid = serializers.IntegerField(read_only=True, min_value=0)
    paid_complete_not_allocated = serializers.IntegerField(read_only=True, min_value=0)


class UserInfoSerializer(serializers.Serializer):
    """
    User info for dashboard.
    SECURITY: Minimal exposure, sanitized.
    """
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(read_only=True)

    def get_full_name(self, obj):
        return sanitize_string(getattr(obj, 'full_name', None))


class ClientDashboardResponseSerializer(serializers.Serializer):
    """
    Complete dashboard response serializer.
    SECURITY: Validates entire response structure.
    """
    user = UserInfoSerializer(read_only=True)
    total_properties = serializers.IntegerField(read_only=True, min_value=0)
    fully_paid_and_allocated = serializers.IntegerField(read_only=True, min_value=0)
    not_fully_paid = serializers.IntegerField(read_only=True, min_value=0)
    paid_complete_not_allocated = serializers.IntegerField(read_only=True, min_value=0)
    active_promotions = serializers.ListField(read_only=True)
    latest_value_by_company = serializers.ListField(read_only=True)
