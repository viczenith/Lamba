"""
Client Company Serializers
===========================
Serializers for client company portfolio pages:

MY COMPANIES PAGE:
- ClientCompanyListSerializer: Company card with allocation count, total invested, rank

MY COMPANY PORTFOLIO PAGE:
- CompanyDetailSerializer: Company info (logo, address, contact)
- PortfolioStatsSerializer: Stats cards data
- PropertySerializer: Individual property in properties tab
- AppreciationPropertySerializer: Property with appreciation data
- PaymentSerializer: Recent payment record
- TransactionDetailSerializer: Transaction modal data
- PortfolioSummarySerializer: Summary section data

Security Features:
- All data scoped to authenticated client only
- Company access validated before returning data
- No cross-client data exposure
"""

from rest_framework import serializers
from decimal import Decimal


# =============================================================================
# MY COMPANIES PAGE SERIALIZERS
# =============================================================================

class ClientCompanySerializer(serializers.Serializer):
    """
    Serializer for company card on My Companies page.
    Includes allocation count, total invested, and rank badge.
    """
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    office_address = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    phone = serializers.CharField(read_only=True, allow_null=True)
    
    # Portfolio metrics (calculated per company)
    allocations_count = serializers.IntegerField(read_only=True)
    total_invested = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    rank_tag = serializers.CharField(read_only=True)
    
    def get_logo_url(self, obj):
        """Return secure logo URL if exists."""
        request = self.context.get('request')
        company_id = obj.get('id') if isinstance(obj, dict) else obj.id
        if company_id and request:
            return request.build_absolute_uri(f'/secure-company-logo/{company_id}/')
        return None


class MyCompaniesResponseSerializer(serializers.Serializer):
    """Response serializer for My Companies endpoint."""
    total_companies = serializers.IntegerField(read_only=True)
    companies = ClientCompanySerializer(many=True, read_only=True)


# =============================================================================
# MY COMPANY PORTFOLIO PAGE SERIALIZERS
# =============================================================================

class CompanyInfoSerializer(serializers.Serializer):
    """Serializer for company header section."""
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    office_address = serializers.CharField(read_only=True, allow_null=True)
    location = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    phone = serializers.CharField(read_only=True, allow_null=True)
    
    def get_logo_url(self, obj):
        """Return secure logo URL if exists."""
        request = self.context.get('request')
        company_id = obj.get('id') if isinstance(obj, dict) else getattr(obj, 'id', None)
        if company_id and request:
            return request.build_absolute_uri(f'/secure-company-logo/{company_id}/')
        return None


class MarketerInfoSerializer(serializers.Serializer):
    """Serializer for marketer details card."""
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    phone = serializers.CharField(read_only=True, allow_null=True)


class PortfolioStatsSerializer(serializers.Serializer):
    """
    Serializer for portfolio stats cards:
    - Total Invested
    - Total Appreciation
    - Total Current Value
    - Marketer Info
    """
    total_invested = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_appreciation = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    marketer = MarketerInfoSerializer(read_only=True, allow_null=True)


class EstateInfoSerializer(serializers.Serializer):
    """Serializer for estate info within property."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    location = serializers.CharField(read_only=True, allow_null=True)


class PlotSizeInfoSerializer(serializers.Serializer):
    """Serializer for plot size info."""
    id = serializers.IntegerField(read_only=True)
    size = serializers.CharField(read_only=True)


class PropertySerializer(serializers.Serializer):
    """
    Serializer for property card in Properties tab.
    Includes estate info, plot details, pricing, and status.
    """
    allocation_id = serializers.IntegerField(read_only=True)
    transaction_id = serializers.IntegerField(read_only=True, allow_null=True)
    estate = EstateInfoSerializer(read_only=True)
    plot_size = PlotSizeInfoSerializer(read_only=True)
    plot_number = serializers.CharField(read_only=True, allow_null=True)
    
    # Pricing
    purchase_price = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    appreciation = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Payment info
    payment_type = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    
    # Dates
    transaction_date = serializers.DateField(read_only=True, allow_null=True)


class AppreciationPropertySerializer(serializers.Serializer):
    """
    Serializer for property in Value Appreciation tab.
    Includes detailed appreciation breakdown.
    """
    allocation_id = serializers.IntegerField(read_only=True)
    estate_name = serializers.CharField(read_only=True)
    plot_size = serializers.CharField(read_only=True)
    
    # Pricing details
    purchase_price = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    current_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    value_increase = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    abs_growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Timeline
    purchase_date = serializers.DateField(read_only=True, allow_null=True)
    current_date = serializers.DateField(read_only=True)


class PaymentRecordSerializer(serializers.Serializer):
    """
    Serializer for payment record in recent payments accordion.
    """
    id = serializers.IntegerField(read_only=True, allow_null=True)
    date = serializers.DateField(read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    reference_code = serializers.CharField(read_only=True)
    payment_type = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    estate_name = serializers.CharField(read_only=True)


class PaymentsByYearSerializer(serializers.Serializer):
    """Serializer for payments grouped by year."""
    year = serializers.IntegerField(read_only=True)
    payments = PaymentRecordSerializer(many=True, read_only=True)
    payment_count = serializers.IntegerField(read_only=True)


class PortfolioSummarySerializer(serializers.Serializer):
    """
    Serializer for Portfolio Summary section.
    Shows total appreciation, average growth, highest growth.
    """
    appreciation_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    average_growth = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    highest_growth_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    highest_growth_property = serializers.CharField(read_only=True, allow_null=True)


class TransactionDetailSerializer(serializers.Serializer):
    """
    Serializer for transaction details modal.
    Shows transaction info and payment history.
    """
    id = serializers.IntegerField(read_only=True)
    reference_code = serializers.CharField(read_only=True)
    transaction_date = serializers.DateField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    
    # Allocation details
    allocation = serializers.SerializerMethodField()
    
    # Part payment details (if applicable)
    payment_duration = serializers.IntegerField(read_only=True, allow_null=True)
    custom_duration = serializers.IntegerField(read_only=True, allow_null=True)
    installment_plan = serializers.CharField(read_only=True, allow_null=True)
    first_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    second_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    third_percent = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    first_installment = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, allow_null=True)
    second_installment = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, allow_null=True)
    third_installment = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True, allow_null=True)
    
    def get_allocation(self, obj):
        """Return allocation details."""
        allocation = obj.get('allocation') if isinstance(obj, dict) else getattr(obj, 'allocation', None)
        if not allocation:
            return None
        return {
            'estate': {
                'name': allocation.estate.name if hasattr(allocation, 'estate') else '',
            },
            'plot_size': str(allocation.plot_size.size) if hasattr(allocation, 'plot_size') and allocation.plot_size else '',
            'plot_number': str(allocation.plot_number) if hasattr(allocation, 'plot_number') and allocation.plot_number else None,
            'payment_type': allocation.payment_type if hasattr(allocation, 'payment_type') else '',
        }


class PaymentHistorySerializer(serializers.Serializer):
    """Serializer for payment history in modal."""
    date = serializers.DateField(read_only=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    method = serializers.CharField(read_only=True)
    installment = serializers.CharField(read_only=True, allow_null=True)
    reference = serializers.CharField(read_only=True)


class TransactionPaymentHistoryResponseSerializer(serializers.Serializer):
    """Response for transaction payment history endpoint."""
    payments = PaymentHistorySerializer(many=True, read_only=True)


# =============================================================================
# FULL PORTFOLIO RESPONSE SERIALIZERS
# =============================================================================

class CompanyPortfolioResponseSerializer(serializers.Serializer):
    """
    Full response serializer for company portfolio page.
    Combines all data needed by my_company_portfolio.html template.
    """
    company = CompanyInfoSerializer(read_only=True)
    stats = PortfolioStatsSerializer(read_only=True)
    properties = PropertySerializer(many=True, read_only=True)
    properties_count = serializers.IntegerField(read_only=True)
    
    # Value Appreciation tab
    appreciation_data = AppreciationPropertySerializer(many=True, read_only=True)
    
    # Recent Payments
    payments_by_year = serializers.DictField(read_only=True)
    total_payments_count = serializers.IntegerField(read_only=True)
    
    # Summary
    summary = PortfolioSummarySerializer(read_only=True)
    
    # Company stats
    estates_count = serializers.IntegerField(read_only=True)
