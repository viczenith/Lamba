"""
Serializers for Company, Subscription, and SaaS features
"""
from rest_framework import serializers
from estateApp.models import Company, MarketerAffiliation, MarketerEarnedCommission, ClientDashboard, ClientPropertyView
from django.utils import timezone


class CompanyBasicSerializer(serializers.ModelSerializer):
    """Basic company info for public endpoints"""
    
    is_trial_active = serializers.SerializerMethodField()
    is_subscription_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'company_name', 'email', 'phone', 'location',
            'logo', 'subscription_tier', 'subscription_status',
            'is_trial_active', 'is_subscription_active', 'theme_color'
        ]
    
    def get_is_trial_active(self, obj):
        return obj.is_trial_active()
    
    def get_is_subscription_active(self, obj):
        return obj.is_subscription_active()


class CompanyDetailedSerializer(serializers.ModelSerializer):
    """Detailed company info for admin/company owners"""
    
    is_trial_active = serializers.SerializerMethodField()
    is_subscription_active = serializers.SerializerMethodField()
    plots_remaining = serializers.SerializerMethodField()
    agents_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'company_name', 'registration_number', 'registration_date',
            'location', 'ceo_name', 'email', 'phone', 'logo',
            'subscription_tier', 'subscription_status', 'trial_ends_at',
            'subscription_ends_at', 'max_plots', 'max_agents',
            'custom_domain', 'theme_color', 'billing_email',
            'is_trial_active', 'is_subscription_active',
            'plots_remaining', 'agents_remaining',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['api_key', 'stripe_customer_id', 'created_at', 'updated_at']
    
    def get_is_trial_active(self, obj):
        return obj.is_trial_active()
    
    def get_is_subscription_active(self, obj):
        return obj.is_subscription_active()
    
    def get_plots_remaining(self, obj):
        from estateApp.models import EstatePlot
        current_plots = EstatePlot.objects.filter(estate__company=obj).count()
        return max(0, obj.max_plots - current_plots)
    
    def get_agents_remaining(self, obj):
        current_agents = obj.users.filter(role='admin').count()
        return max(0, obj.max_agents - current_agents)


class MarketerAffiliationSerializer(serializers.ModelSerializer):
    """Marketer affiliation with company and commission tracking"""
    
    marketer_name = serializers.CharField(source='marketer.full_name', read_only=True)
    marketer_email = serializers.CharField(source='marketer.email', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True)
    pending_commissions = serializers.SerializerMethodField()
    commission_tier_display = serializers.CharField(source='get_commission_tier_display', read_only=True)
    
    class Meta:
        model = MarketerAffiliation
        fields = [
            'id', 'marketer', 'marketer_name', 'marketer_email',
            'company', 'company_name', 'commission_tier',
            'commission_tier_display', 'commission_rate',
            'properties_sold', 'total_commissions_earned',
            'total_commissions_paid', 'pending_commissions',
            'total_sales_value', 'status', 'date_affiliated',
            'approval_date', 'bank_name', 'account_number', 'account_name'
        ]
    
    def get_pending_commissions(self, obj):
        return float(obj.get_pending_commissions())


class MarketerAffiliationListSerializer(serializers.ModelSerializer):
    """Simplified marketer affiliation for list views"""
    
    marketer_name = serializers.CharField(source='marketer.full_name', read_only=True)
    company_name = serializers.CharField(source='company.company_name', read_only=True)
    commission_tier_display = serializers.CharField(source='get_commission_tier_display', read_only=True)
    
    class Meta:
        model = MarketerAffiliation
        fields = [
            'id', 'marketer_name', 'company_name',
            'commission_tier_display', 'commission_rate',
            'properties_sold', 'status', 'date_affiliated'
        ]


class MarketerCommissionSerializer(serializers.ModelSerializer):
    """Individual commission details"""
    
    marketer_name = serializers.CharField(source='affiliation.marketer.full_name', read_only=True)
    company_name = serializers.CharField(source='affiliation.company.company_name', read_only=True)
    plot_details = serializers.CharField(source='plot_allocation', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MarketerEarnedCommission
        fields = [
            'id', 'affiliation', 'marketer_name', 'company_name',
            'plot_allocation', 'plot_details', 'sale_amount',
            'commission_rate', 'commission_amount', 'status',
            'status_display', 'created_at', 'approved_at', 'paid_at',
            'payment_reference', 'dispute_reason', 'disputed_at'
        ]
        read_only_fields = ['created_at', 'approved_at', 'paid_at', 'disputed_at']


class CommissionBulkApprovalSerializer(serializers.Serializer):
    """Bulk approve/reject commissions"""
    
    commission_ids = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=['approve', 'reject', 'dispute'])
    reason = serializers.CharField(required=False, allow_blank=True)


class ClientDashboardSerializer(serializers.ModelSerializer):
    """Client's aggregated portfolio across all companies"""
    
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    
    class Meta:
        model = ClientDashboard
        fields = [
            'id', 'client', 'client_name', 'client_email',
            'total_properties_owned', 'total_invested', 'portfolio_value',
            'roi_percentage', 'month_over_month_growth',
            'projected_value_1yr', 'projected_value_5yr',
            'preferred_currency', 'notification_preferences',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ClientPropertyViewSerializer(serializers.ModelSerializer):
    """Client's property views and interests"""
    
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    estate_name = serializers.CharField(source='plot.estate.name', read_only=True)
    plot_number = serializers.CharField(source='plot.plot_number', read_only=True)
    company_name = serializers.CharField(source='plot.estate.company.company_name', read_only=True)
    plot_size = serializers.CharField(source='plot.plot_size.size_sqm', read_only=True)
    
    class Meta:
        model = ClientPropertyView
        fields = [
            'id', 'client', 'client_name', 'plot', 'estate_name',
            'plot_number', 'company_name', 'plot_size',
            'view_count', 'first_viewed_at', 'last_viewed_at',
            'is_interested', 'is_favorited', 'client_notes'
        ]
        read_only_fields = ['first_viewed_at', 'last_viewed_at', 'view_count']
