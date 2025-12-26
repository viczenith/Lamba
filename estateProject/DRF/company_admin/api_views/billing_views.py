"""
Billing and invoicing API views.
Handles: invoice retrieval, payment history, subscription management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone
from estateApp.models import Invoice, Payment, Company
from DRF.company_admin.serializers.billing_serializers import InvoiceSerializer, PaymentSerializer
import logging

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Invoice management for billing.
    
    Endpoints:
    - GET /api/invoices/ - List invoices for authenticated company
    - GET /api/invoices/{id}/ - Get invoice details
    - GET /api/invoices/download-pdf/ - Download invoice as PDF
    - POST /api/invoices/mark-paid/ - Mark invoice as paid
    """
    
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'period_start', 'period_end']
    ordering = ['-period_end']
    
    def get_queryset(self):
        """Only return invoices for user's company"""
        company = getattr(self.request, 'company', None)
        if company:
            return Invoice.objects.filter(company=company)
        return Invoice.objects.none()
    
    def list(self, request, *args, **kwargs):
        """List all invoices for the company"""
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get invoice summary statistics"""
        company = getattr(request, 'company', None)
        if not company:
            return Response({'error': 'No company context'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoices = Invoice.objects.filter(company=company)
        
        total_invoiced = sum(inv.total_amount for inv in invoices.filter(status='issued'))
        total_paid = sum(inv.total_amount for inv in invoices.filter(status='paid'))
        overdue = invoices.filter(status='issued').filter(due_date__lt=timezone.now().date())
        
        return Response({
            'total_invoiced': float(total_invoiced),
            'total_paid': float(total_paid),
            'pending_amount': float(total_invoiced - total_paid),
            'overdue_invoices': overdue.count(),
            'overdue_amount': float(sum(inv.total_amount for inv in overdue)),
        })
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid"""
        invoice = self.get_object()
        invoice.status = 'paid'
        invoice.save(update_fields=['status'])
        
        return Response({
            'status': 'success',
            'message': 'Invoice marked as paid',
            'invoice_id': invoice.pk,
        })
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download invoice as PDF.
        Note: Requires weasyprint or similar PDF generation library
        """
        invoice = self.get_object()
        
        # TODO: Implement PDF generation
        # For now, return JSON response
        return Response({
            'error': 'PDF generation not yet implemented',
            'invoice_id': invoice.pk,
            'invoice_number': invoice.invoice_number,
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment history and tracking.
    
    Endpoints:
    - GET /api/payments/ - List payments for invoices in company
    - GET /api/payments/{id}/ - Get payment details
    - POST /api/payments/verify/ - Verify manual payment
    """
    
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['payment_method', 'paid_at']
    ordering = ['-paid_at']
    
    def get_queryset(self):
        """Only return payments for company's invoices"""
        company = getattr(self.request, 'company', None)
        if company:
            invoice_ids = Invoice.objects.filter(company=company).values_list('pk', flat=True)
            return Payment.objects.filter(invoice_id__in=invoice_ids)
        return Payment.objects.none()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payment summary statistics"""
        company = getattr(request, 'company', None)
        if not company:
            return Response({'error': 'No company context'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice_ids = Invoice.objects.filter(company=company).values_list('pk', flat=True)
        payments = Payment.objects.filter(invoice_id__in=invoice_ids)
        
        total_paid = sum(p.amount for p in payments)
        verified_payments = payments.filter(verified_at__isnull=False)
        pending_verification = payments.filter(verified_at__isnull=True)
        
        return Response({
            'total_paid': float(total_paid),
            'total_payments': payments.count(),
            'verified_count': verified_payments.count(),
            'pending_verification': pending_verification.count(),
            'payment_methods': dict(
                payments.values('payment_method').annotate(
                    count=Count('id'),
                    total=Sum('amount')
                ).values_list('payment_method', 'count')
            ),
        })
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify manual payment"""
        payment = self.get_object()
        
        if payment.is_verified:
            return Response(
                {'error': 'Payment already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.mark_verified(request.user)
        
        return Response({
            'status': 'success',
            'message': 'Payment verified',
            'payment_id': payment.pk,
            'verified_by': request.user.full_name,
        })


from django.db.models import Count, Sum
