from rest_framework import serializers


class TargetSerializer(serializers.Serializer):
    period_type = serializers.CharField()
    specific_period = serializers.CharField()
    target_amount = serializers.FloatField()


class CompanyMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    company_name = serializers.CharField()
    logo_url = serializers.CharField(allow_null=True)
    initial = serializers.CharField(allow_null=True)
    location = serializers.CharField(allow_null=True, allow_blank=True)


class MarketerCompanyItemSerializer(serializers.Serializer):
    company = CompanyMiniSerializer()
    closed_deals = serializers.IntegerField()
    commission_rate = serializers.FloatField(allow_null=True)
    yearly_target_achievement = serializers.FloatField(allow_null=True)
    yearly_target = TargetSerializer(allow_null=True)
    total_year_sales = serializers.FloatField()
    monthly_target = TargetSerializer(allow_null=True)
    quarterly_target = TargetSerializer(allow_null=True)
    monthly_sales = serializers.FloatField()
    quarterly_sales = serializers.FloatField()
    monthly_achievement = serializers.FloatField(allow_null=True)
    quarterly_achievement = serializers.FloatField(allow_null=True)
    current_month = serializers.CharField()
    current_quarter = serializers.CharField()
    client_count = serializers.IntegerField()
    has_transactions = serializers.BooleanField()
    rank_position = serializers.IntegerField(allow_null=True)
    rank_total = serializers.IntegerField()
    rank_label = serializers.CharField(allow_blank=True)


class MarketerMyCompaniesResponseSerializer(serializers.Serializer):
    companies = MarketerCompanyItemSerializer(many=True)
    current_year = serializers.IntegerField()
