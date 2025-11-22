"""
Subscription and Payment Management ViewSets for DRF.
Integrates with Stripe and manages subscriptions and payments.
"""
import logging
import stripe
from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.conf import settings
from django.utils import timezone

from estateApp.models import Company, Payment, Transaction
from ..serializers.billing_serializers import PaymentSerializer
from estateApp.permissions import (
    IsAuthenticated, IsCompanyOwnerOrAdmin, SubscriptionRequiredPermission,
    TenantIsolationPermission
)
from estateApp.throttles import SubscriptionTierThrottle
from estateApp.audit_logging import AuditLogger
from estateApp.error_tracking import track_errors, ErrorHandler

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionViewSet(viewsets.ViewSet):
    """
    Subscription management endpoints:
    - View current subscription
    - Upgrade/downgrade subscription
    - Cancel subscription
    - View billing history
    - Manage payment methods
    """
    
    permission_classes = [
        IsAuthenticated,
        IsCompanyOwnerOrAdmin,
    ]
    throttle_classes = [SubscriptionTierThrottle]
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current subscription for company"""
        
        company = request.company
        
        return Response({
            'tier': company.subscription_tier,
            'status': company.subscription_status,
            'started_at': company.created_at,
            'expires_at': company.subscription_ends_at,
            'trial_ends_at': company.trial_ends_at,
            'api_calls_daily': company.max_api_calls_daily,
            'max_plots': company.max_plots,
            'max_agents': company.max_agents,
        })
    
    @action(detail=False, methods=['post'])
    @track_errors(error_type='subscription')
    def upgrade(self, request):
        """Upgrade company subscription"""
        
        company = request.company
        new_tier = request.data.get('tier')
        payment_method_id = request.data.get('payment_method_id')
        
        # Validate tier
        if new_tier not in ['starter', 'professional', 'enterprise']:
            return Response(
                {'error': 'Invalid subscription tier'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prevent downgrade
        tier_levels = {'starter': 1, 'professional': 2, 'enterprise': 3}
        if tier_levels.get(new_tier, 0) <= tier_levels.get(company.subscription_tier, 0):
            return Response(
                {'error': 'Can only upgrade to higher tier'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Calculate new price
                tier_prices = {
                    'starter': Decimal('99.00'),
                    'professional': Decimal('299.00'),
                    'enterprise': Decimal('999.00'),
                }
                
                new_price = tier_prices.get(new_tier)
                old_price = tier_prices.get(company.subscription_tier)
                
                # Proration: charge difference for current month
                proration_amount = new_price - old_price
                
                # Create Stripe charge if not free tier
                if proration_amount > 0 and payment_method_id:
                    charge = stripe.Charge.create(
                        amount=int(proration_amount * 100),  # Convert to cents
                        currency='usd',
                        customer=company.stripe_customer_id,
                        source=payment_method_id,
                        description=f'Upgrade to {new_tier} tier'
                    )
                    
                    # Log payment
                    AuditLogger.log_payment(
                        user=request.user,
                        company=company,
                        amount=float(proration_amount),
                        status='SUCCESS',
                        transaction_id=charge.id,
                        request=request
                    )
                
                # Update subscription
                old_tier = company.subscription_tier
                company.subscription_tier = new_tier
                company.subscription_status = 'active'
                company.subscription_ends_at = timezone.now() + timezone.timedelta(days=30)
                company.save()
                
                # Log audit
                AuditLogger.log_subscription_change(
                    user=request.user,
                    company=company,
                    old_tier=old_tier,
                    new_tier=new_tier,
                    request=request
                )
                
                return Response({
                    'message': f'Upgraded to {new_tier} tier',
                    'subscription': {
                        'tier': company.subscription_tier,
                        'expires_at': company.subscription_ends_at,
                        'proration_amount': float(proration_amount),
                    }
                })
        
        except stripe.error.CardError as e:
            logger.error(f"Card error during upgrade: {e}")
            return Response(
                {'error': f'Payment failed: {e.user_message}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Subscription upgrade error: {e}", exc_info=True)
            ErrorHandler.handle_api_error(e, request=request, view=self)
            return Response(
                {'error': 'Upgrade failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    @track_errors(error_type='subscription')
    def downgrade(self, request):
        """Downgrade company subscription"""
        
        company = request.company
        new_tier = request.data.get('tier', 'starter')
        
        # Validate tier
        if new_tier not in ['starter', 'professional']:
            return Response(
                {'error': 'Can only downgrade to starter or professional'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                old_tier = company.subscription_tier
                company.subscription_tier = new_tier
                company.save()
                
                # Log audit
                AuditLogger.log_subscription_change(
                    user=request.user,
                    company=company,
                    old_tier=old_tier,
                    new_tier=new_tier,
                    request=request
                )
                
                return Response({
                    'message': f'Downgraded to {new_tier} tier',
                    'effective_date': timezone.now().date()
                })
        
        except Exception as e:
            logger.error(f"Subscription downgrade error: {e}")
            return Response(
                {'error': 'Downgrade failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    @track_errors(error_type='subscription')
    def cancel(self, request):
        """Cancel company subscription"""
        
        company = request.company
        
        try:
            with transaction.atomic():
                company.subscription_status = 'cancelled'
                company.subscription_ends_at = timezone.now()
                company.save()
                
                # Log audit
                AuditLogger.log_subscription_change(
                    user=request.user,
                    company=company,
                    old_tier=company.subscription_tier,
                    new_tier='cancelled',
                    request=request
                )
                
                return Response({
                    'message': 'Subscription cancelled',
                    'effective_date': timezone.now().date()
                })
        
        except Exception as e:
            logger.error(f"Subscription cancellation error: {e}")
            return Response(
                {'error': 'Cancellation failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def billing_history(self, request):
        """Get billing history for company"""
        
        company = request.company
        
        # Get all payments for company
        payments = Payment.objects.filter(
            company=company
        ).order_by('-created_at')
        
        serializer = PaymentSerializer(payments, many=True)
        
        return Response({
            'total_payments': payments.count(),
            'total_amount': sum(p.amount for p in payments),
            'payments': serializer.data
        })


class PaymentViewSet(viewsets.ViewSet):
    """
    Payment processing endpoints:
    - Process payment
    - Get payment receipt
    - Handle webhooks
    """
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [SubscriptionTierThrottle]
    
    @action(detail=False, methods=['post'])
    @track_errors(error_type='payment')
    def process(self, request):
        """Process payment"""
        
        company = request.company
        amount = Decimal(request.data.get('amount', 0))
        payment_method_id = request.data.get('payment_method_id')
        description = request.data.get('description', 'Payment')
        
        if amount <= 0:
            return Response(
                {'error': 'Amount must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create Stripe charge
            charge = stripe.Charge.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                customer=company.stripe_customer_id or None,
                source=payment_method_id,
                description=description,
            )
            
            # Record payment
            payment = Payment.objects.create(
                company=company,
                amount=amount,
                stripe_charge_id=charge.id,
                status='completed',
                description=description,
            )
            
            # Log payment
            AuditLogger.log_payment(
                user=request.user,
                company=company,
                amount=float(amount),
                status='SUCCESS',
                transaction_id=charge.id,
                request=request
            )
            
            return Response({
                'message': 'Payment processed successfully',
                'charge_id': charge.id,
                'amount': float(amount),
                'status': charge.status,
            })
        
        except stripe.error.CardError as e:
            logger.error(f"Card error: {e}")
            return Response(
                {'error': f'Payment failed: {e.user_message}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Payment processing error: {e}", exc_info=True)
            ErrorHandler.handle_api_error(e, request=request, view=self)
            return Response(
                {'error': 'Payment processing failed'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def webhook(self, request):
        """Handle Stripe webhook"""
        
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return Response({'error': 'Invalid signature'}, status=400)
        
        # Handle different event types
        if event['type'] == 'charge.succeeded':
            handle_charge_succeeded(event['data']['object'])
        elif event['type'] == 'charge.failed':
            handle_charge_failed(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        
        return Response({'status': 'success'})


class TransactionViewSet(viewsets.ModelViewSet):
    """
    Transaction tracking endpoints:
    - List transactions
    - Get transaction details
    - Generate reports
    """
    
    permission_classes = [
        IsAuthenticated,
        SubscriptionRequiredPermission,
        TenantIsolationPermission,
    ]
    throttle_classes = [SubscriptionTierThrottle]
    
    def get_queryset(self):
        """Get transactions for user's company"""
        company = getattr(self.request, 'company', None)
        
        if company:
            return Transaction.objects.filter(
                allocation__plot__estate__company=company
            )
        
        return Transaction.objects.none()
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get transaction statistics"""
        
        company = request.company
        from django.db.models import Sum, Count, Avg
        from datetime import timedelta
        
        last_30_days = timezone.now() - timedelta(days=30)
        
        stats = Transaction.objects.filter(
            allocation__plot__estate__company=company,
            created_at__gte=last_30_days
        ).aggregate(
            total_transactions=Count('id'),
            total_revenue=Sum('amount'),
            average_transaction=Avg('amount'),
        )
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export transactions as CSV"""
        
        # Check subscription allows export
        company = request.company
        if company.subscription_tier == 'starter':
            return Response(
                {'error': 'Data export requires Professional tier'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        import csv
        from django.http import HttpResponse
        
        transactions = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Transaction ID', 'Date', 'Amount', 'Status'])
        
        for txn in transactions:
            writer.writerow([txn.id, txn.created_at, txn.amount, txn.status])
        
        # Log export
        AuditLogger.log_export(
            user=request.user,
            company=company,
            export_type='transactions',
            record_count=transactions.count(),
            request=request
        )
        
        return response


def handle_charge_succeeded(charge):
    """Handle successful Stripe charge"""
    
    try:
        payment = Payment.objects.get(stripe_charge_id=charge.id)
        payment.status = 'completed'
        payment.save()
        
        logger.info(f"Charge succeeded: {charge.id}")
    
    except Exception as e:
        logger.error(f"Error handling charge succeeded: {e}")


def handle_charge_failed(charge):
    """Handle failed Stripe charge"""
    
    try:
        payment = Payment.objects.get(stripe_charge_id=charge.id)
        payment.status = 'failed'
        payment.save()
        
        logger.error(f"Charge failed: {charge.id}")
    
    except Exception as e:
        logger.error(f"Error handling charge failed: {e}")


def handle_subscription_deleted(subscription):
    """Handle subscription deletion"""
    
    try:
        company = Company.objects.get(stripe_customer_id=subscription.customer)
        company.subscription_status = 'cancelled'
        company.save()
        
        logger.info(f"Subscription cancelled for company: {company.id}")
    
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")
