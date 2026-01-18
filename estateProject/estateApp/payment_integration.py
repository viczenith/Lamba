"""
Payment Gateway Integration - Stripe & Paystack
Handles subscription payments, webhooks, and billing
"""

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal
import stripe
import logging
import json
import hashlib
import hmac

logger = logging.getLogger(__name__)

# Configure Payment Gateways
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
PAYSTACK_SECRET_KEY = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
PAYSTACK_PUBLIC_KEY = getattr(settings, 'PAYSTACK_PUBLIC_KEY', None)


# ============================================================================
# STRIPE INTEGRATION
# ============================================================================

class StripePaymentProcessor:
    """Handle Stripe payment processing"""
    
    @staticmethod
    def create_customer(company, email):
        """Create Stripe customer for company"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=company.company_name,
                metadata={
                    'company_id': company.id,
                    'company_name': company.company_name
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {str(e)}")
            return None
    
    @staticmethod
    def create_subscription(customer_id, price_id, company, billing_cycle='monthly'):
        """Create Stripe subscription"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'company_id': company.id,
                    'billing_cycle': billing_cycle
                }
            )
            return {
                'subscription_id': subscription.id,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None,
                'status': subscription.status
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {str(e)}")
            return None
    
    @staticmethod
    def create_payment_intent(amount, company, plan_tier, billing_cycle='monthly'):
        """Create payment intent for one-time payment"""
        try:
            amount_cents = int(amount * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='ngn',
                metadata={
                    'company_id': company.id,
                    'plan_tier': plan_tier,
                    'billing_cycle': billing_cycle
                }
            )
            
            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': amount,
                'currency': 'NGN'
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment intent creation failed: {str(e)}")
            return None
    
    @staticmethod
    def confirm_payment(payment_intent_id):
        """Confirm payment intent status"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'status': intent.status,
                'amount': Decimal(intent.amount) / 100,
                'currency': intent.currency
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment confirmation failed: {str(e)}")
            return None


# ============================================================================
# PAYSTACK INTEGRATION
# ============================================================================

class PaystackPaymentProcessor:
    """Handle Paystack payment processing"""
    
    @staticmethod
    def initialize_transaction(company, email, amount, plan_tier, billing_cycle='monthly'):
        """Initialize Paystack transaction"""
        import requests
        
        url = "https://api.paystack.co/transaction/initialize"
        
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        # Amount in kobo (Paystack smallest unit)
        amount_kobo = int(amount * 100)
        
        payload = {
            "email": email,
            "amount": amount_kobo,
            "metadata": {
                "company_id": company.id,
                "company_name": company.company_name,
                "plan_tier": plan_tier,
                "billing_cycle": billing_cycle
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get('status'):
                return {
                    'authorization_url': data['data']['authorization_url'],
                    'access_code': data['data']['access_code'],
                    'reference': data['data']['reference'],
                    'amount': amount
                }
            else:
                logger.error(f"Paystack init failed: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Paystack transaction init error: {str(e)}")
            return None
    
    @staticmethod
    def verify_transaction(reference):
        """Verify Paystack transaction status"""
        import requests
        
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()
            
            if data.get('status'):
                transaction = data['data']
                return {
                    'status': transaction['status'],
                    'amount': Decimal(transaction['amount']) / 100,
                    'reference': transaction['reference'],
                    'authorization': transaction.get('authorization', {})
                }
            else:
                logger.error(f"Paystack verify failed: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Paystack transaction verify error: {str(e)}")
            return None
    
    @staticmethod
    def create_subscription_plan(plan_tier, amount, interval='monthly'):
        """Create recurring plan on Paystack"""
        import requests
        
        url = "https://api.paystack.co/plan"
        
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        # Convert interval to Paystack format
        interval_map = {
            'monthly': 'monthly',
            'quarterly': 'quarterly',
            'half-yearly': 'biannually',
            'yearly': 'annually'
        }
        
        amount_kobo = int(amount * 100)
        
        payload = {
            "name": f"Lamba {plan_tier.title()} Plan",
            "description": f"₦{amount:,.0f} per month",
            "amount": amount_kobo,
            "interval": interval_map.get(interval, 'monthly'),
            "plan_code": f"PLAN_{plan_tier.upper()}_{interval.upper()}"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if data.get('status'):
                return data['data']['plan_code']
            else:
                logger.error(f"Paystack plan creation failed: {data.get('message')}")
                return None
        except Exception as e:
            logger.error(f"Paystack plan creation error: {str(e)}")
            return None


# ============================================================================
# DJANGO VIEWS - PAYMENT ENDPOINTS
# ============================================================================

@login_required
@require_POST
def create_stripe_payment(request, company_slug):
    """Create Stripe payment for subscription"""
    from estateApp.models import Company
    from superAdmin.models import SubscriptionPlan
    from estateApp.subscription_billing_models import SubscriptionBillingModel
    
    try:
        company = Company.objects.get(slug=company_slug)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    # Check permissions
    if request.user.company != company:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    plan_tier = request.POST.get('plan_tier')
    billing_cycle = request.POST.get('billing_cycle', 'monthly')
    
    try:
        plan = SubscriptionPlan.objects.get(tier=plan_tier)
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'error': 'Invalid plan'}, status=400)
    
    # Get or create billing record
    billing, created = SubscriptionBillingModel.objects.get_or_create(company=company)
    
    # Determine amount
    amount = plan.annual_price if billing_cycle == 'annual' else plan.monthly_price
    
    # Create payment intent
    intent_data = StripePaymentProcessor.create_payment_intent(
        float(amount),
        company,
        plan_tier,
        billing_cycle
    )
    
    if not intent_data:
        return JsonResponse({'error': 'Payment intent creation failed'}, status=500)
    
    return JsonResponse({
        'status': 'success',
        'client_secret': intent_data['client_secret'],
        'payment_intent_id': intent_data['payment_intent_id'],
        'amount': str(intent_data['amount']),
        'currency': intent_data['currency']
    })


@login_required
@require_POST
def create_paystack_payment(request, company_slug):
    """Create Paystack payment for subscription"""
    from estateApp.models import Company
    from superAdmin.models import SubscriptionPlan
    from estateApp.subscription_billing_models import SubscriptionBillingModel
    
    try:
        company = Company.objects.get(slug=company_slug)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    # Check permissions
    if request.user.company != company:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    plan_tier = request.POST.get('plan_tier')
    billing_cycle = request.POST.get('billing_cycle', 'monthly')
    
    try:
        plan = SubscriptionPlan.objects.get(tier=plan_tier)
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'error': 'Invalid plan'}, status=400)
    
    # Get or create billing record
    billing, created = SubscriptionBillingModel.objects.get_or_create(company=company)
    
    # Determine amount
    amount = plan.annual_price if billing_cycle == 'annual' else plan.monthly_price
    
    # Initialize Paystack transaction
    transaction_data = PaystackPaymentProcessor.initialize_transaction(
        company,
        request.user.email,
        float(amount),
        plan_tier,
        billing_cycle
    )
    
    if not transaction_data:
        return JsonResponse({'error': 'Payment initialization failed'}, status=500)
    
    return JsonResponse({
        'status': 'success',
        'authorization_url': transaction_data['authorization_url'],
        'access_code': transaction_data['access_code'],
        'reference': transaction_data['reference'],
        'amount': str(transaction_data['amount'])
    })


# ============================================================================
# WEBHOOK HANDLERS
# ============================================================================

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    from estateApp.models import Company
    from estateApp.subscription_billing_models import SubscriptionBillingModel, BillingHistory
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        )
    except ValueError as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature error: {str(e)}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle different event types
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        company_id = payment_intent['metadata'].get('company_id')
        
        try:
            company = Company.objects.get(id=company_id)
            billing = company.billing
            
            # Update billing record
            billing.last_payment_date = timezone.now()
            billing.payment_method = 'stripe'
            billing.stripe_subscription_id = payment_intent['id']
            billing.status = 'active'
            
            # Set subscription dates based on billing cycle
            billing_cycle = payment_intent['metadata'].get('billing_cycle', 'monthly')
            from datetime import timedelta
            if billing_cycle == 'annual':
                billing.subscription_ends_at = timezone.now() + timedelta(days=365)
            else:
                billing.subscription_ends_at = timezone.now() + timedelta(days=30)
            
            billing.save()
            
            # Log transaction
            BillingHistory.objects.create(
                billing=billing,
                transaction_type='charge',
                state='completed',
                amount=Decimal(payment_intent['amount']) / 100,
                currency=payment_intent['currency'].upper(),
                description=f"Subscription payment - {billing_cycle}",
                transaction_id=payment_intent['id'],
                billing_date=timezone.now(),
                due_date=timezone.now().date(),
                paid_date=timezone.now(),
                invoice_number=f"STR-{payment_intent['id'][:20]}",
                payment_method='stripe'
            )
            
            logger.info(f"Payment succeeded for company {company_id}")
        except Company.DoesNotExist:
            logger.error(f"Company {company_id} not found")
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        company_id = payment_intent['metadata'].get('company_id')
        
        try:
            company = Company.objects.get(id=company_id)
            billing = company.billing
            
            # Log failed transaction
            BillingHistory.objects.create(
                billing=billing,
                transaction_type='charge',
                state='failed',
                amount=Decimal(payment_intent['amount']) / 100,
                currency=payment_intent['currency'].upper(),
                description=f"Payment failed - {payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}",
                transaction_id=payment_intent['id'],
                billing_date=timezone.now(),
                due_date=timezone.now().date(),
                invoice_number=f"STR-{payment_intent['id'][:20]}",
                payment_method='stripe'
            )
            
            logger.warning(f"Payment failed for company {company_id}")
        except Company.DoesNotExist:
            logger.error(f"Company {company_id} not found")
    
    return JsonResponse({'status': 'success'})


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhooks"""
    from estateApp.models import Company
    from estateApp.subscription_billing_models import SubscriptionBillingModel, BillingHistory
    
    # Verify webhook signature
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    payload = request.body
    
    hash_object = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        payload,
        hashlib.sha512
    )
    
    computed_signature = hash_object.hexdigest()
    
    if signature != computed_signature:
        logger.error("Paystack webhook signature verification failed")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if data['event'] == 'charge.success':
        payment_data = data['data']
        company_id = payment_data['metadata'].get('company_id')
        
        try:
            company = Company.objects.get(id=company_id)
            billing = company.billing
            
            # Update billing record
            billing.last_payment_date = timezone.now()
            billing.payment_method = 'paystack'
            billing.paystack_subscription_code = payment_data['reference']
            billing.status = 'active'
            
            # Set subscription dates
            billing_cycle = payment_data['metadata'].get('billing_cycle', 'monthly')
            from datetime import timedelta
            if billing_cycle == 'annual':
                billing.subscription_ends_at = timezone.now() + timedelta(days=365)
            else:
                billing.subscription_ends_at = timezone.now() + timedelta(days=30)
            
            billing.save()
            
            # Log transaction
            BillingHistory.objects.create(
                billing=billing,
                transaction_type='charge',
                state='completed',
                amount=Decimal(payment_data['amount']) / 100,
                currency='NGN',
                description=f"Subscription payment - {billing_cycle}",
                transaction_id=payment_data['reference'],
                billing_date=timezone.now(),
                due_date=timezone.now().date(),
                paid_date=timezone.now(),
                invoice_number=f"PST-{payment_data['reference'][:20]}",
                payment_method='paystack'
            )
            
            logger.info(f"Paystack payment succeeded for company {company_id}")
        except Company.DoesNotExist:
            logger.error(f"Company {company_id} not found")
    
    return JsonResponse({'status': 'success'})


# ============================================================================
# SETTINGS CONFIGURATION
# ============================================================================

"""
Add to settings.py:

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Paystack Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')

# Payment Settings
PAYMENT_SETTINGS = {
    'DEFAULT_CURRENCY': 'NGN',
    'STRIPE_ENABLED': True,
    'PAYSTACK_ENABLED': True,
    'PAYMENT_TIMEOUT': 300,  # seconds
    'WEBHOOK_ENDPOINTS': {
        'stripe': '/webhooks/stripe/',
        'paystack': '/webhooks/paystack/',
    }
}
"""

"""
Add to urls.py:

# Webhook endpoints
path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
path('webhooks/paystack/', paystack_webhook, name='paystack_webhook'),

# Payment endpoints
path('api/payment/stripe/create/', create_stripe_payment, name='create_stripe_payment'),
path('api/payment/paystack/create/', create_paystack_payment, name='create_paystack_payment'),
"""
