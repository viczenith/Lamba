from rest_framework import serializers


class AllocationSerializer(serializers.Serializer):
    plot_number = serializers.CharField(allow_null=True)
    plot_size = serializers.CharField(allow_null=True)
    estate = serializers.DictField(child=serializers.CharField(), allow_null=True)


class TransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    transaction_date = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    amount = serializers.FloatField()
    client_id = serializers.IntegerField(allow_null=True)
    allocation = AllocationSerializer(allow_null=True)


class ClientPortfolioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    profile_image = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    date_registered = serializers.CharField(allow_null=True)
    company_transactions = TransactionSerializer(many=True)


class MarketerMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(allow_null=True)
    profile_image = serializers.CharField(allow_null=True)


class TopPerformerSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    marketer = MarketerMiniSerializer()


class MarketerCompanyPortfolioResponseSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company_name = serializers.CharField()
    company_logo = serializers.CharField(allow_null=True)
    current_year = serializers.IntegerField()
    top3 = TopPerformerSerializer(many=True)
    user_entry = TopPerformerSerializer(allow_null=True)
    clients = ClientPortfolioSerializer(many=True)
    closed_deals = serializers.IntegerField()
    commission_rate = serializers.FloatField(allow_null=True)
    commission_earned = serializers.FloatField(allow_null=True)
    total_value = serializers.FloatField()
    transactions = TransactionSerializer(many=True)
