"""
Company Portfolio Page Serializers
===================================
Serializers for the My Company Portfolio page (my_company_portfolio.html)

This page shows detailed portfolio data for a specific company:
- Company header (logo, name, address, contact)
- Stats cards (Total Invested, Appreciation, Current Value, Marketer)
- Properties Tab (property cards grid)
- Value Appreciation Tab (appreciation cards with timeline)
- Recent Payments sidebar (grouped by year)
- Portfolio Summary section
- Transaction Details Modal

Security: All data scoped to authenticated client and validated company access.
"""

from rest_framework import serializers
from decimal import Decimal


# =============================================================================
# COMPANY HEADER SERIALIZERS
# =============================================================================

class CompanyHeaderSerializer(serializers.Serializer):
    """
    Serializer for company header section.
    Maps to .company-hero component in template.
    """
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    office_address = serializers.CharField(read_only=True, allow_null=True)
    location = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    phone = serializers.CharField(read_only=True, allow_null=True)
    
    def get_logo_url(self, obj):
        """Return secure logo URL."""
        request = self.context.get('request')
        company_id = obj.get('id') if isinstance(obj, dict) else getattr(obj, 'id', None)
        if company_id and request:
            return request.build_absolute_uri(f'/secure-company-logo/{company_id}/')
        return None


# =============================================================================
# STATS CARDS SERIALIZERS
# =============================================================================

class MarketerInfoSerializer(serializers.Serializer):
    """Serializer for marketer details in stats card."""
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    phone = serializers.CharField(read_only=True, allow_null=True)


class PortfolioStatsSerializer(serializers.Serializer):
    """
    Serializer for the 4 stats cards row.
    - Total Invested
    - Total Appreciation (value increased)
    - Total Current Value
    - Marketer Info
    """
    total_invested = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_appreciation = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    marketer = MarketerInfoSerializer(read_only=True, allow_null=True)


# =============================================================================
# PROPERTIES TAB SERIALIZERS
# =============================================================================

class EstateInfoSerializer(serializers.Serializer):
    """Estate info within property card."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    location = serializers.CharField(read_only=True, allow_null=True)


class PlotSizeSerializer(serializers.Serializer):
    """Plot size info within property card."""
    id = serializers.IntegerField(read_only=True, allow_null=True)
    size = serializers.CharField(read_only=True)


class PropertyCardSerializer(serializers.Serializer):
    """
    Serializer for property card in Properties tab.
    Maps to .property-item component in template.
    """
    allocation_id = serializers.IntegerField(read_only=True)
    transaction_id = serializers.IntegerField(read_only=True, allow_null=True)
    estate = EstateInfoSerializer(read_only=True)
    plot_size = PlotSizeSerializer(read_only=True)
    plot_number = serializers.CharField(read_only=True, allow_null=True)
    
    # Pricing
    purchase_price = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    appreciation = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Payment info
    payment_type = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    
    # Date
    transaction_date = serializers.DateField(read_only=True, allow_null=True)


# =============================================================================
# VALUE APPRECIATION TAB SERIALIZERS
# =============================================================================

class AppreciationCardSerializer(serializers.Serializer):
    """
    Serializer for appreciation card in Value Appreciation tab.
    Maps to .appreciation-card component with timeline.
    """
    allocation_id = serializers.IntegerField(read_only=True)
    estate_name = serializers.CharField(read_only=True)
    plot_size = serializers.CharField(read_only=True)
    
    # Pricing breakdown
    purchase_price = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    value_increase = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    abs_growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Timeline dates
    purchase_date = serializers.DateField(read_only=True, allow_null=True)
    current_date = serializers.DateField(read_only=True)


class PortfolioSummarySerializer(serializers.Serializer):
    """
    Serializer for Portfolio Summary section at bottom of Appreciation tab.
    Shows total appreciation, average growth, highest growth property.
    """
    appreciation_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    average_growth = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    highest_growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    highest_growth_property = serializers.CharField(read_only=True, allow_null=True)


# =============================================================================
# RECENT PAYMENTS SERIALIZERS
# =============================================================================

class PaymentRecordSerializer(serializers.Serializer):
    """
    Serializer for payment record in Recent Payments accordion.
    """
    id = serializers.IntegerField(read_only=True, allow_null=True)
    date = serializers.DateField(read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    reference_code = serializers.CharField(read_only=True)
    payment_type = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    estate_name = serializers.CharField(read_only=True)


# =============================================================================
# TRANSACTION MODAL SERIALIZERS
# =============================================================================

class TransactionAllocationSerializer(serializers.Serializer):
    """Allocation details within transaction modal."""
    estate_name = serializers.CharField(read_only=True)
    plot_size = serializers.CharField(read_only=True)
    plot_number = serializers.CharField(read_only=True, allow_null=True)
    payment_type = serializers.CharField(read_only=True)


class TransactionDetailSerializer(serializers.Serializer):
    """
    Serializer for Transaction Details modal.
    Shows full transaction info and part-payment details.
    """
    id = serializers.IntegerField(read_only=True)
    reference_code = serializers.CharField(read_only=True)
    transaction_date = serializers.DateField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    
    # Allocation info
    allocation = TransactionAllocationSerializer(read_only=True)
    
    # Part-payment details (shown if payment_type == 'part')
    payment_duration = serializers.IntegerField(read_only=True, allow_null=True)
    custom_duration = serializers.IntegerField(read_only=True, allow_null=True)
    installment_plan = serializers.CharField(read_only=True, allow_null=True)
    first_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    second_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    third_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    first_installment = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, allow_null=True)
    second_installment = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, allow_null=True)
    third_installment = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, allow_null=True)


class PaymentHistoryItemSerializer(serializers.Serializer):
    """Serializer for payment history row in transaction modal."""
    date = serializers.DateField(read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    method = serializers.CharField(read_only=True)
    installment = serializers.CharField(read_only=True, allow_null=True)
    reference = serializers.CharField(read_only=True)


class PaymentHistoryResponseSerializer(serializers.Serializer):
    """Response for payment history endpoint."""
    payments = PaymentHistoryItemSerializer(many=True, read_only=True)


# =============================================================================
# FULL PAGE RESPONSE SERIALIZER
# =============================================================================

class CompanyPortfolioResponseSerializer(serializers.Serializer):
    """
    Full response serializer for Company Portfolio API endpoint.
    Combines all data needed by my_company_portfolio.html template.
    """
    # Company header
    company = CompanyHeaderSerializer(read_only=True)
    
    # Stats cards
    stats = PortfolioStatsSerializer(read_only=True)
    
    # Properties tab
    properties = PropertyCardSerializer(many=True, read_only=True)
    properties_count = serializers.IntegerField(read_only=True)
    
    # Value Appreciation tab
    appreciation_data = AppreciationCardSerializer(many=True, read_only=True)
    
    # Portfolio summary
    summary = PortfolioSummarySerializer(read_only=True)
    
    # Recent Payments sidebar (grouped by year)
    payments_by_year = serializers.DictField(read_only=True)
    total_payments_count = serializers.IntegerField(read_only=True)
    
    # Company sidebar stats
    estates_count = serializers.IntegerField(read_only=True)
