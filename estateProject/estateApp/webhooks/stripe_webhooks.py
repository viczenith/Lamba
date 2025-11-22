"""
Stripe webhook handlers for payment processing and subscription management.
Handles: checkout sessions, subscription updates, payment intents, invoices.
"""
import os
import logging
import stripe
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from estateApp.models import Company, Invoice, Payment
from estateApp.notifications.email_service import EmailService

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')


@csrf_exempt
def stripe_webhook(request):
    """
    Webhook endpoint for Stripe events.
    Handles: checkout.session.completed, customer.subscription.updated, etc.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle different event types
    event_type = event['type']
    event_data = event['data']['object']
    
    try:
        if event_type == 'checkout.session.completed':
            handle_checkout_session_completed(event_data)
        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(event_data)
        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(event_data)
        elif event_type == 'payment_intent.succeeded':
            handle_payment_intent_succeeded(event_data)
        elif event_type == 'payment_intent.payment_failed':
            handle_payment_intent_payment_failed(event_data)
        elif event_type == 'invoice.paid':
            handle_invoice_paid(event_data)
        elif event_type == 'invoice.payment_failed':
            handle_invoice_payment_failed(event_data)
        else:
            logger.info(f"Unhandled event type: {event_type}")
    except Exception as e:
        logger.error(f"Error handling Stripe event {event_type}: {e}", exc_info=True)
        return JsonResponse({'error': 'Event processing failed'}, status=500)
    
    return JsonResponse({'status': 'success'})


def handle_checkout_session_completed(session):
    """
    Handle completed checkout session.
    Creates/updates subscription in our database.
    """
    try:
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        # Find company by stripe_customer_id
        company = Company.objects.get(stripe_customer_id=customer_id)
        
        # Update company subscription
        company.stripe_customer_id = customer_id
        company.subscription_status = 'active'
        company.subscription_ends_at = timezone.now() + timezone.timedelta(days=30)
        company.save(update_fields=['subscription_status', 'subscription_ends_at'])
        
        logger.info(f"Checkout completed for company {company.company_name}")
        
        # Send confirmation email
        EmailService.send_email(
            subject=f"✅ Your {company.subscription_tier.upper()} subscription is active",
            template_name='emails/subscription_renewed.html',
            context={
                'company': company,
                'tier': company.subscription_tier,
                'renewal_date': company.subscription_ends_at,
            },
            recipient_list=[company.billing_email or company.email],
        )
        
    except Company.DoesNotExist:
        logger.error(f"Company not found for Stripe customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling checkout completion: {e}", exc_info=True)


def handle_subscription_updated(subscription):
    """
    Handle subscription update (tier change, renewal, etc.)
    """
    try:
        customer_id = subscription.get('customer')
        status_val = subscription.get('status')
        
        company = Company.objects.get(stripe_customer_id=customer_id)
        
        # Map Stripe status to our status
        if status_val == 'active':
            company.subscription_status = 'active'
        elif status_val == 'past_due':
            company.subscription_status = 'active'  # Still active but payment overdue
        elif status_val == 'canceled':
            company.subscription_status = 'cancelled'
        
        company.save(update_fields=['subscription_status'])
        
        logger.info(f"Subscription updated for company {company.company_name}: {status_val}")
        
    except Company.DoesNotExist:
        logger.error(f"Company not found for Stripe customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}", exc_info=True)


def handle_subscription_deleted(subscription):
    """
    Handle subscription cancellation.
    """
    try:
        customer_id = subscription.get('customer')
        company = Company.objects.get(stripe_customer_id=customer_id)
        
        company.subscription_status = 'cancelled'
        company.save(update_fields=['subscription_status'])
        
        logger.info(f"Subscription cancelled for company {company.company_name}")
        
        # Send cancellation email
        EmailService.send_email(
            subject="Your subscription has been cancelled",
            template_name='emails/subscription_cancelled.html',
            context={
                'company': company,
            },
            recipient_list=[company.billing_email or company.email],
        )
        
    except Company.DoesNotExist:
        logger.error(f"Company not found for Stripe customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}", exc_info=True)


def handle_payment_intent_succeeded(payment_intent):
    """
    Handle successful payment intent.
    """
    try:
        invoice_ref = payment_intent.get('metadata', {}).get('invoice_id')
        if not invoice_ref:
            return
        
        invoice = Invoice.objects.get(pk=invoice_ref)
        amount = Decimal(payment_intent.get('amount', 0)) / 100  # Convert from cents
        
        # Create payment record
        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method='stripe',
            payment_reference=payment_intent.get('id'),
        )
        
        # Update invoice if fully paid
        total_paid = sum(p.amount for p in invoice.payments.all())
        if total_paid >= invoice.total_amount:
            invoice.status = 'paid'
            invoice.save(update_fields=['status'])
        
        logger.info(f"Payment succeeded for invoice {invoice.invoice_number}")
        
    except Exception as e:
        logger.error(f"Error handling payment intent success: {e}", exc_info=True)


def handle_payment_intent_payment_failed(payment_intent):
    """
    Handle failed payment intent.
    """
    try:
        invoice_ref = payment_intent.get('metadata', {}).get('invoice_id')
        if not invoice_ref:
            return
        
        invoice = Invoice.objects.get(pk=invoice_ref)
        error_message = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
        
        logger.error(f"Payment failed for invoice {invoice.invoice_number}: {error_message}")
        
        # Send failure notification
        EmailService.send_payment_failed_email(invoice.company, error_message)
        
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}", exc_info=True)


def handle_invoice_paid(stripe_invoice):
    """
    Handle paid invoice from Stripe.
    """
    try:
        customer_id = stripe_invoice.get('customer')
        company = Company.objects.get(stripe_customer_id=customer_id)
        amount = Decimal(stripe_invoice.get('total', 0)) / 100
        
        logger.info(f"Invoice paid from Stripe: customer={customer_id}, amount={amount}")
        
    except Company.DoesNotExist:
        logger.error(f"Company not found for Stripe customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling Stripe invoice paid: {e}", exc_info=True)


def handle_invoice_payment_failed(stripe_invoice):
    """
    Handle failed invoice payment from Stripe.
    """
    try:
        customer_id = stripe_invoice.get('customer')
        company = Company.objects.get(stripe_customer_id=customer_id)
        
        logger.warning(f"Invoice payment failed from Stripe: customer={customer_id}")
        
        # Send failure notification
        EmailService.send_payment_failed_email(
            company,
            "Your payment could not be processed. Please update your payment method."
        )
        
    except Company.DoesNotExist:
        logger.error(f"Company not found for Stripe customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling Stripe invoice payment failed: {e}", exc_info=True)


class CreateCheckoutSessionView(APIView):
    """
    Create a Stripe checkout session for subscription purchase.
    
    POST /api/billing/checkout-session/
    {
        "company_id": 1,
        "tier": "professional",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel"
    }
    """
    
    def post(self, request):
        try:
            company_id = request.data.get('company_id')
            tier = request.data.get('tier', 'starter')
            success_url = request.data.get('success_url', 'http://localhost:3000/dashboard')
            cancel_url = request.data.get('cancel_url', 'http://localhost:3000/billing')
            
            company = Company.objects.get(pk=company_id)
            
            # Pricing tiers
            pricing = {
                'starter': 1500,      # ₦15,000 in kobo
                'professional': 4500,  # ₦45,000
                'enterprise': 10000,   # ₦100,000 (negotiate)
            }
            
            price_in_kobo = pricing.get(tier, pricing['starter']) * 100  # Convert to kobo
            
            # Create Stripe customer if not exists
            if not company.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=company.billing_email or company.email,
                    name=company.company_name,
                    metadata={'company_id': company.pk},
                )
                company.stripe_customer_id = customer.id
                company.save(update_fields=['stripe_customer_id'])
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=company.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'ngn',
                        'product_data': {
                            'name': f'{tier.upper()} Subscription',
                            'description': f'Real Estate SaaS - {tier.title()} Plan',
                        },
                        'unit_amount': int(price_in_kobo),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'company_id': company.pk,
                    'tier': tier,
                },
            )
            
            return Response({
                'session_id': session.id,
                'checkout_url': session.url,
                'company': company.company_name,
                'tier': tier,
            })
            
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
