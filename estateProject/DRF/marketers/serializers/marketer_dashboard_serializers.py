from rest_framework import serializers

class DashboardSummarySerializer(serializers.Serializer):
    # Fields required by `marketer_side.html` (keep minimal and explicit)
    total_transactions = serializers.IntegerField()
    number_clients = serializers.IntegerField()
    total_companies = serializers.IntegerField()

class PerformanceBlockSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    tx = serializers.ListField(child=serializers.IntegerField())
    est = serializers.ListField(child=serializers.IntegerField())
    cli = serializers.ListField(child=serializers.IntegerField())

class CompanyTransactionItemSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    transactions = serializers.IntegerField()
    company_logo = serializers.CharField(allow_null=True, required=False)


class DashboardFullSerializer(serializers.Serializer):
    summary = DashboardSummarySerializer()
    weekly = PerformanceBlockSerializer()
    monthly = PerformanceBlockSerializer()
    yearly = PerformanceBlockSerializer()
    alltime = PerformanceBlockSerializer()
    # Optional company-level breakdown used by the bar chart in the marketer UI
    companies = CompanyTransactionItemSerializer(many=True, required=False)

    # Backwards-compatible fields used by server-rendered template
    company_names = serializers.ListField(child=serializers.CharField(), required=False)
    company_transactions = serializers.ListField(child=serializers.IntegerField(), required=False)
