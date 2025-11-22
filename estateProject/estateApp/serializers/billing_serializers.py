"""
Serializers for Invoice and Payment models.
"""
from rest_framework import serializers
from estateApp.models import Invoice, Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )
    is_verified = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'invoice',
            'amount',
            'payment_method',
            'payment_method_display',
            'payment_reference',
            'notes',
            'paid_at',
            'verified_at',
            'verified_by',
            'is_verified',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'paid_at',
            'verified_at',
            'verified_by',
            'created_at',
        ]
    
    def get_is_verified(self, obj):
        return obj.is_verified


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model"""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    total_amount = serializers.DecimalField(
        source='total_amount',
        read_only=True,
        max_digits=12,
        decimal_places=2
    )
    is_overdue = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()
    payments = PaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'company',
            'invoice_number',
            'period_start',
            'period_end',
            'amount',
            'tax_amount',
            'total_amount',
            'status',
            'status_display',
            'due_date',
            'issued_at',
            'paid_at',
            'notes',
            'is_overdue',
            'days_until_due',
            'payments',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'invoice_number',
            'tax_amount',
            'total_amount',
            'issued_at',
            'paid_at',
            'payments',
            'created_at',
            'updated_at',
        ]
    
    def get_is_overdue(self, obj):
        return obj.is_overdue
    
    def get_days_until_due(self, obj):
        return obj.days_until_due
