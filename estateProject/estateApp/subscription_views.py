"""
Subscription & Billing Management Views for Company Admin
Handles subscription plans, billing, payments, and renewal
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import json
from decimal import Decimal

from .models import Company, SubscriptionPlan
from .subscription_billing_models import SubscriptionBillingModel, BillingHistory, SubscriptionFeatureAccess
from .subscription_access import subscription_required, can_create_client_required
from .payment_integration import StripePaymentProcessor, PaystackPaymentProcessor
from .email_notifications import SubscriptionEmailNotifications


# ============================================================================
# SUBSCRIPTION PLAN VIEWS
# ============================================================================

@login_required
@require_http_methods(["GET"])
def get_subscription_plans(request):
    """
    API endpoint to fetch all available subscription plans
    Used by JavaScript to populate plan selection UI
    """
    try:
        plans = SubscriptionPlan.objects.all().values(
            'id', 'name', 'price', 'properties_limit', 'users_limit', 
            'marketers_limit', 'has_analytics', 'description'
        )
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': plan['id'],
                'name': plan['name'],
                'price': float(plan['price']),
                'properties_limit': plan['properties_limit'],
                'users_limit': plan['users_limit'],
                'marketers_limit': plan['marketers_limit'],
                'has_analytics': plan['has_analytics'],
                'description': plan['description']
            })
        
        return JsonResponse({'ok': True, 'plans': plans_data})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_subscription_status(request):
    """
    API endpoint to fetch current subscription status for the company
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        
        try:
            subscription = SubscriptionBillingModel.objects.get(company=company)
            
            return JsonResponse({
                'ok': True,
                'subscription': {
                    'plan_name': subscription.subscription_plan.name,
                    'amount': float(subscription.amount),
                    'status': subscription.get_current_status(),
                    'starts_at': subscription.subscription_starts_at.isoformat(),
                    'ends_at': subscription.subscription_ends_at.isoformat(),
                    'days_remaining': (subscription.subscription_ends_at - timezone.now()).days,
                    'payment_method': subscription.payment_method,
                    'is_grace_period': subscription.is_grace_period()
                }
            })
        except SubscriptionBillingModel.DoesNotExist:
            return JsonResponse({'ok': True, 'subscription': None})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ============================================================================
# SUBSCRIPTION MANAGEMENT VIEWS
# ============================================================================

@login_required
@require_http_methods(["GET"])
@subscription_required
def subscription_dashboard(request):
    """
    Full subscription dashboard view
    Shows subscription status, usage metrics, billing history
    """
    company = get_object_or_404(Company, admin=request.user)
    
    try:
        subscription = SubscriptionBillingModel.objects.get(company=company)
    except SubscriptionBillingModel.DoesNotExist:
        subscription = None
    
    # Get billing history
    billing_history = BillingHistory.objects.filter(
        subscription=subscription
    ).order_by('-created_at')[:10] if subscription else []
    
    # Get usage metrics
    from .models import ClientUser, MarketingExecutive, Estate
    total_properties = Estate.objects.filter(company=company).count()
    total_clients = ClientUser.objects.filter(company=company).count()
    total_marketers = MarketingExecutive.objects.filter(company=company).count()
    total_allocations = 0  # Assuming there's an allocation model
    
    context = {
        'company': company,
        'subscription': subscription,
        'billing_history': billing_history,
        'total_properties': total_properties,
        'total_clients': total_clients,
        'total_marketers': total_marketers,
        'total_allocations': total_allocations,
    }
    
    return render(request, 'admin_side/company_profile.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def renew_subscription(request):
    """
    Initiate subscription renewal
    Validates renewal request and prepares payment
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        data = json.loads(request.body)
        payment_method = data.get('payment_method')
        
        if not payment_method or payment_method not in ['stripe', 'paystack']:
            return JsonResponse({'ok': False, 'error': 'Invalid payment method'}, status=400)
        
        try:
            subscription = SubscriptionBillingModel.objects.get(company=company)
        except SubscriptionBillingModel.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'No active subscription'}, status=400)
        
        # Create renewal billing history entry
        BillingHistory.objects.create(
            subscription=subscription,
            transaction_type='renewal',
            amount=subscription.amount,
            description=f'Renewal initiated for {subscription.subscription_plan.name} plan'
        )
        
        # Store payment method in session for next step
        request.session['pending_renewal'] = {
            'company_id': company.id,
            'subscription_id': subscription.id,
            'amount': str(subscription.amount),
            'payment_method': payment_method
        }
        
        return JsonResponse({
            'ok': True,
            'message': 'Renewal initiated. Please proceed to payment.',
            'next_step': 'payment'
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def upgrade_subscription(request):
    """
    Handle subscription plan upgrade
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        data = json.loads(request.body)
        new_plan_id = data.get('plan_id')
        
        new_plan = get_object_or_404(SubscriptionPlan, id=new_plan_id)
        
        try:
            current_subscription = SubscriptionBillingModel.objects.get(company=company)
        except SubscriptionBillingModel.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'No current subscription'}, status=400)
        
        # Calculate proration if applicable
        days_used = (timezone.now() - current_subscription.subscription_starts_at).days
        days_total = (current_subscription.subscription_ends_at - current_subscription.subscription_starts_at).days
        
        # Simple proration logic
        current_daily_rate = current_subscription.amount / Decimal(days_total)
        new_daily_rate = new_plan.price / Decimal(days_total)
        daily_difference = new_daily_rate - current_daily_rate
        proration_amount = daily_difference * Decimal(days_total - days_used)
        
        # Store upgrade details in session
        request.session['pending_upgrade'] = {
            'company_id': company.id,
            'subscription_id': current_subscription.id,
            'new_plan_id': new_plan_id,
            'new_plan_name': new_plan.name,
            'new_amount': str(new_plan.price),
            'proration_amount': str(proration_amount)
        }
        
        # Log upgrade initiation
        BillingHistory.objects.create(
            subscription=current_subscription,
            transaction_type='upgrade',
            amount=proration_amount,
            description=f'Upgrade initiated from {current_subscription.subscription_plan.name} to {new_plan.name}'
        )
        
        return JsonResponse({
            'ok': True,
            'message': 'Upgrade initiated',
            'proration_amount': float(proration_amount),
            'next_step': 'payment'
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ============================================================================
# PAYMENT PROCESSING VIEWS
# ============================================================================

@login_required
@require_http_methods(["POST"])
@csrf_protect
def process_payment(request):
    """
    Main payment processing endpoint
    Routes to Stripe or Paystack based on payment method
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        data = json.loads(request.body)
        payment_method = data.get('payment_method', 'stripe')
        
        # Get pending transaction from session
        pending = request.session.get('pending_renewal') or request.session.get('pending_upgrade')
        
        if not pending:
            return JsonResponse({'ok': False, 'error': 'No pending transaction'}, status=400)
        
        try:
            subscription = SubscriptionBillingModel.objects.get(id=pending['subscription_id'])
        except SubscriptionBillingModel.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Subscription not found'}, status=400)
        
        try:
            if payment_method == 'stripe':
                processor = StripePaymentProcessor()
                payment_intent = processor.create_payment_intent(
                    company=company,
                    subscription=subscription,
                    amount=Decimal(pending['amount'])
                )
                return JsonResponse({
                    'ok': True,
                    'client_secret': payment_intent['client_secret'],
                    'payment_method': 'stripe'
                })
            
            elif payment_method == 'paystack':
                processor = PaystackPaymentProcessor()
                transaction_data = processor.initialize_transaction(
                    company=company,
                    subscription=subscription,
                    amount=Decimal(pending['amount'])
                )
                return JsonResponse({
                    'ok': True,
                    'authorization_url': transaction_data['authorization_url'],
                    'reference': transaction_data['reference'],
                    'payment_method': 'paystack'
                })
            else:
                return JsonResponse({'ok': False, 'error': 'Invalid payment method'}, status=400)
        
        except Exception as e:
            # Log payment error
            BillingHistory.objects.create(
                subscription=subscription,
                transaction_type='payment_failed',
                amount=Decimal(pending['amount']),
                description=f'Payment initiation failed: {str(e)}'
            )
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def confirm_stripe_payment(request):
    """
    Confirm and process Stripe payment
    Called after Stripe payment intent is confirmed on frontend
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        data = json.loads(request.body)
        payment_intent_id = data.get('payment_intent_id')
        
        pending = request.session.get('pending_renewal') or request.session.get('pending_upgrade')
        
        if not pending or not payment_intent_id:
            return JsonResponse({'ok': False, 'error': 'Invalid request'}, status=400)
        
        with transaction.atomic():
            try:
                subscription = SubscriptionBillingModel.objects.get(id=pending['subscription_id'])
                
                # Verify payment with Stripe
                processor = StripePaymentProcessor()
                payment_intent = processor.verify_payment(payment_intent_id)
                
                if payment_intent['status'] != 'succeeded':
                    return JsonResponse({'ok': False, 'error': 'Payment verification failed'}, status=400)
                
                # Update subscription
                subscription.subscription_starts_at = timezone.now()
                subscription.subscription_ends_at = timezone.now() + timedelta(days=30)
                subscription.payment_method = 'stripe'
                subscription.transaction_id = payment_intent_id
                subscription.status = 'active'
                subscription.save()
                
                # Log transaction
                BillingHistory.objects.create(
                    subscription=subscription,
                    transaction_type='charge',
                    amount=subscription.amount,
                    description=f'Subscription payment processed via Stripe - {subscription.subscription_plan.name}'
                )
                
                # Send confirmation email
                SubscriptionEmailNotifications.send_subscription_renewed_email(
                    company,
                    subscription.subscription_ends_at
                )
                
                # Clear pending transaction
                if 'pending_renewal' in request.session:
                    del request.session['pending_renewal']
                if 'pending_upgrade' in request.session:
                    del request.session['pending_upgrade']
                
                return JsonResponse({
                    'ok': True,
                    'message': 'Payment successful! Your subscription has been renewed.',
                    'redirect': 'company_profile'
                })
            
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def confirm_paystack_payment(request):
    """
    Confirm and process Paystack payment
    Called after user returns from Paystack payment page
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        data = json.loads(request.body)
        reference = data.get('reference')
        
        pending = request.session.get('pending_renewal') or request.session.get('pending_upgrade')
        
        if not pending or not reference:
            return JsonResponse({'ok': False, 'error': 'Invalid request'}, status=400)
        
        with transaction.atomic():
            try:
                subscription = SubscriptionBillingModel.objects.get(id=pending['subscription_id'])
                
                # Verify payment with Paystack
                processor = PaystackPaymentProcessor()
                payment_result = processor.verify_transaction(reference)
                
                if not payment_result['status']:
                    return JsonResponse({'ok': False, 'error': 'Payment verification failed'}, status=400)
                
                # Update subscription
                subscription.subscription_starts_at = timezone.now()
                subscription.subscription_ends_at = timezone.now() + timedelta(days=30)
                subscription.payment_method = 'paystack'
                subscription.transaction_id = reference
                subscription.status = 'active'
                subscription.save()
                
                # Log transaction
                BillingHistory.objects.create(
                    subscription=subscription,
                    transaction_type='charge',
                    amount=subscription.amount,
                    description=f'Subscription payment processed via Paystack - {subscription.subscription_plan.name}'
                )
                
                # Send confirmation email
                SubscriptionEmailNotifications.send_subscription_renewed_email(
                    company,
                    subscription.subscription_ends_at
                )
                
                # Clear pending transaction
                if 'pending_renewal' in request.session:
                    del request.session['pending_renewal']
                if 'pending_upgrade' in request.session:
                    del request.session['pending_upgrade']
                
                return JsonResponse({
                    'ok': True,
                    'message': 'Payment successful! Your subscription has been renewed.',
                    'redirect': 'company_profile'
                })
            
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ============================================================================
# BILLING HISTORY & INVOICES
# ============================================================================

@login_required
@require_http_methods(["GET"])
def get_billing_history(request):
    """
    API endpoint to fetch billing history
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        
        try:
            subscription = SubscriptionBillingModel.objects.get(company=company)
        except SubscriptionBillingModel.DoesNotExist:
            return JsonResponse({'ok': True, 'history': []})
        
        history = BillingHistory.objects.filter(
            subscription=subscription
        ).order_by('-created_at').values(
            'id', 'transaction_type', 'amount', 'description', 'created_at'
        )
        
        history_data = []
        for entry in history:
            history_data.append({
                'id': entry['id'],
                'type': entry['transaction_type'],
                'amount': float(entry['amount']),
                'description': entry['description'],
                'date': entry['created_at'].isoformat()
            })
        
        return JsonResponse({'ok': True, 'history': history_data})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_invoice(request, invoice_id):
    """
    Download invoice as PDF
    """
    try:
        company = get_object_or_404(Company, admin=request.user)
        
        try:
            subscription = SubscriptionBillingModel.objects.get(company=company)
            billing_entry = BillingHistory.objects.get(id=invoice_id, subscription=subscription)
        except (SubscriptionBillingModel.DoesNotExist, BillingHistory.DoesNotExist):
            return JsonResponse({'ok': False, 'error': 'Invoice not found'}, status=404)
        
        # Generate invoice PDF (implementation depends on PDF library used)
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        from django.http import HttpResponse
        
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        
        # Add invoice content
        pdf.drawString(100, 750, f"Invoice #{billing_entry.id}")
        pdf.drawString(100, 730, f"Date: {billing_entry.created_at.strftime('%Y-%m-%d')}")
        pdf.drawString(100, 710, f"Company: {company.company_name}")
        pdf.drawString(100, 690, f"Amount: ₦{billing_entry.amount}")
        pdf.drawString(100, 670, f"Type: {billing_entry.transaction_type}")
        pdf.drawString(100, 650, f"Description: {billing_entry.description}")
        
        pdf.showPage()
        pdf.save()
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{billing_entry.id}.pdf"'
        return response
    
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ============================================================================
# SUBSCRIPTION MODALS & CONTEXT
# ============================================================================

def subscription_context_for_company_profile(request, company):
    """
    Prepare subscription context for company profile template
    Called from company_profile view
    """
    try:
        subscription = SubscriptionBillingModel.objects.get(company=company)
        
        # Get feature access
        features = SubscriptionFeatureAccess.objects.filter(
            subscription=subscription
        ).values_list('feature_name', 'is_enabled')
        
        billing_history = BillingHistory.objects.filter(
            subscription=subscription
        ).order_by('-created_at')[:10]
        
        context = {
            'subscription': subscription,
            'subscription_status': subscription.get_current_status(),
            'warning_level': subscription.get_warning_level(),
            'features': dict(features),
            'billing_history': billing_history,
            'days_remaining': max(0, (subscription.subscription_ends_at - timezone.now()).days),
            'is_grace_period': subscription.is_grace_period(),
        }
    except SubscriptionBillingModel.DoesNotExist:
        context = {
            'subscription': None,
            'subscription_status': 'inactive',
            'warning_level': None,
            'features': {},
            'billing_history': [],
            'days_remaining': 0,
            'is_grace_period': False,
        }
    
    return context
