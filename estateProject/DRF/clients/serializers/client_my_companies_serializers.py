"""
My Companies Page Serializers
==============================
Serializers for the My Companies page (my_companies.html)

This page shows a grid of company cards where the client has investments.
Each card displays:
- Company info (name, logo, address)
- Allocation count (properties)
- Total invested amount
- Client rank badge

Security: All data scoped to authenticated client only.
"""

from rest_framework import serializers
from decimal import Decimal


class CompanyCardSerializer(serializers.Serializer):
    """
    Serializer for individual company card on My Companies page.
    Maps to the glass-card component in my_companies.html template.
    """
    id = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()
    office_address = serializers.CharField(read_only=True, allow_null=True)
    
    # Portfolio metrics per company
    allocations_count = serializers.IntegerField(read_only=True)
    total_invested = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    rank_tag = serializers.CharField(read_only=True)
    
    def get_logo_url(self, obj):
        """Return secure logo URL if company has logo."""
        request = self.context.get('request')
        company_id = obj.get('id') if isinstance(obj, dict) else getattr(obj, 'id', None)
        if company_id and request:
            return request.build_absolute_uri(f'/secure-company-logo/{company_id}/')
        return None


class MyCompaniesListResponseSerializer(serializers.Serializer):
    """
    Full response serializer for My Companies API endpoint.
    Returns total count and list of company cards.
    """
    total_companies = serializers.IntegerField(read_only=True)
    companies = CompanyCardSerializer(many=True, read_only=True)
