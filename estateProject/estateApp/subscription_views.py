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
    Returns plans with monthly/annual pricing and full features
    """
    try:
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('monthly_price')
        
        plans_data = []
        for plan in plans:
            # Calculate annual savings (2 months free)
            annual_price = plan.annual_price or (plan.monthly_price * 10)
            annual_savings = (plan.monthly_price * 12) - annual_price
            
            plans_data.append({
                'id': plan.id,
                'name': plan.name,
                'tier': plan.tier,
                'description': plan.description,
                # Pricing
                'monthly_price': float(plan.monthly_price),
                'annual_price': float(annual_price),
                'annual_savings': float(annual_savings),
                # Limits
                'max_plots': plan.max_plots,
                'max_agents': plan.max_agents,
                'max_api_calls_daily': plan.max_api_calls_daily,
                # Features from JSON
                'features': plan.features or {},
                # UI flags
                'is_popular': plan.tier == 'professional',
                'is_preferred': plan.tier == 'enterprise',
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
        company = getattr(request, 'company', None)
        if not company:
            company_profile = getattr(request.user, 'company_profile', None)
            company = getattr(company_profile, 'company', None) if company_profile else None
        if not company:
            company = getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'ok': False, 'error': 'No company context'}, status=400)

        company_profile = getattr(request.user, 'company_profile', None)
        profile_company = getattr(company_profile, 'company', None) if company_profile else None
        if profile_company and company and getattr(profile_company, 'id', None) != getattr(company, 'id', None):
            return JsonResponse({'ok': False, 'error': 'Company context mismatch'}, status=403)
        
        billing = SubscriptionBillingModel.objects.select_related('current_plan').filter(company=company).first()
        if not billing:
            end_at = company.subscription_ends_at or company.trial_ends_at
            days_remaining = 0
            if end_at and end_at > timezone.now():
                days_remaining = (end_at - timezone.now()).days
            return JsonResponse({
                'ok': True,
                'subscription': {
                    'plan_name': company.get_subscription_tier_display() if hasattr(company, 'get_subscription_tier_display') else (company.subscription_tier or 'N/A'),
                    'tier': company.subscription_tier,
                    'amount': 0,
                    'status': company.subscription_status,
                    'billing_period': 'monthly',
                    'starts_at': (company.subscription_started_at.isoformat() if company.subscription_started_at else None),
                    'ends_at': (end_at.isoformat() if end_at else None),
                    'days_remaining': days_remaining,
                    'payment_method': None,
                    'is_grace_period': bool(getattr(company, 'is_read_only_mode', False)) or (company.subscription_status == 'grace_period'),
                    'is_trial': company.subscription_status == 'trial',
                    'is_active': company.subscription_status == 'active',
                }
            })

        billing.refresh_status()
        plan = billing.current_plan
        end_at = billing.get_expiration_datetime() or billing.subscription_ends_at or billing.trial_ends_at
        days_remaining = 0
        if end_at and end_at > timezone.now():
            days_remaining = (end_at - timezone.now()).days

        amount = 0
        if plan:
            amount = plan.annual_price if billing.billing_cycle == 'annual' else plan.monthly_price
        return JsonResponse({
            'ok': True,
            'subscription': {
                'plan_name': plan.name if plan else company.get_subscription_tier_display(),
                'tier': plan.tier if plan else company.subscription_tier,
                'amount': float(amount) if amount else 0,
                'status': billing.status,
                'billing_period': billing.billing_cycle,
                'starts_at': (billing.subscription_started_at.isoformat() if billing.subscription_started_at else None),
                'ends_at': (end_at.isoformat() if end_at else None),
                'days_remaining': days_remaining,
                'payment_method': billing.payment_method,
                'is_grace_period': billing.is_grace_period(),
                'is_trial': billing.is_trial(),
                'is_active': billing.is_active(),
            }
        })
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
        company = getattr(request, 'company', None)
        if not company:
            company_profile = getattr(request.user, 'company_profile', None)
            company = getattr(company_profile, 'company', None) if company_profile else None
        if not company:
            company = getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'ok': False, 'error': 'No company context'}, status=400)

        company_profile = getattr(request.user, 'company_profile', None)
        profile_company = getattr(company_profile, 'company', None) if company_profile else None
        if profile_company and company and getattr(profile_company, 'id', None) != getattr(company, 'id', None):
            return JsonResponse({'ok': False, 'error': 'Company context mismatch'}, status=403)

        billing = SubscriptionBillingModel.objects.filter(company=company).first()
        if not billing:
            return JsonResponse({'ok': True, 'history': []})

        history_qs = BillingHistory.objects.filter(
            billing=billing
        ).order_by('-billing_date')[:200]

        history_data = []
        for entry in history_qs:
            history_data.append({
                'id': entry.id,
                'type': entry.transaction_type,
                'state': entry.state,
                'amount': float(entry.amount),
                'description': entry.description,
                'invoice_number': entry.invoice_number,
                'date': (entry.billing_date.isoformat() if entry.billing_date else entry.created_at.isoformat()),
            })

        return JsonResponse({'ok': True, 'history': history_data})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def update_payment_method(request):
    """Set default payment method for the current company (tenant-safe).

    Accepts: payment_method, auto_renew, billing_email, billing_contact
    Note: This endpoint does NOT collect or store raw card data.
    It only stores which provider the company prefers for billing (e.g. paystack/bank_transfer).
    """
    try:
        company = getattr(request, 'company', None)
        if not company:
            company_profile = getattr(request.user, 'company_profile', None)
            company = getattr(company_profile, 'company', None) if company_profile else None
        if not company:
            company = getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'ok': False, 'error': 'No company context'}, status=400)

        company_profile = getattr(request.user, 'company_profile', None)
        profile_company = getattr(company_profile, 'company', None) if company_profile else None
        if profile_company and company and getattr(profile_company, 'id', None) != getattr(company, 'id', None):
            return JsonResponse({'ok': False, 'error': 'Company context mismatch'}, status=403)

        payload = json.loads(request.body or '{}')
        payment_method = payload.get('payment_method')
        auto_renew = payload.get('auto_renew')
        billing_email = payload.get('billing_email')
        billing_contact = payload.get('billing_contact')

        # Validate payment method - only allow paystack and bank_transfer (not stripe)
        allowed_methods = {'paystack', 'bank_transfer'}
        if payment_method not in allowed_methods:
            return JsonResponse({
                'ok': False, 
                'error': f'Invalid payment method. Allowed: {", ".join(allowed_methods)}'
            }, status=400)

        billing, _created = SubscriptionBillingModel.objects.get_or_create(company=company)

        # Track which fields to update
        update_fields = ['payment_method']
        billing.payment_method = payment_method
        
        if isinstance(auto_renew, bool):
            billing.auto_renew = auto_renew
            update_fields.append('auto_renew')
        
        if billing_email is not None:
            # Validate email format if provided
            billing_email = str(billing_email).strip() if billing_email else None
            if billing_email:
                from django.core.validators import validate_email
                from django.core.exceptions import ValidationError
                try:
                    validate_email(billing_email)
                    billing.billing_email = billing_email
                    update_fields.append('billing_email')
                except ValidationError:
                    return JsonResponse({'ok': False, 'error': 'Invalid billing email format'}, status=400)
            else:
                billing.billing_email = None
                update_fields.append('billing_email')
        
        if billing_contact is not None:
            billing.billing_contact = str(billing_contact).strip()[:100] if billing_contact else None
            update_fields.append('billing_contact')
        
        billing.save(update_fields=update_fields)

        return JsonResponse({
            'ok': True,
            'payment_method': billing.payment_method,
            'auto_renew': billing.auto_renew,
            'billing_email': billing.billing_email,
            'billing_contact': billing.billing_contact,
        })
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def download_invoice(request, invoice_id):
    """
    Download invoice as PDF
    """
    try:
        company = getattr(request, 'company', None) or getattr(request.user, 'company_profile', None)
        if not company:
            return JsonResponse({'ok': False, 'error': 'No company context'}, status=400)

        billing = SubscriptionBillingModel.objects.filter(company=company).first()
        if not billing:
            return JsonResponse({'ok': False, 'error': 'Subscription billing not found'}, status=404)

        try:
            billing_entry = BillingHistory.objects.get(id=invoice_id, billing=billing)
        except BillingHistory.DoesNotExist:
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
        # SubscriptionFeatureAccess is keyed by plan in the enhanced model.
        plan = subscription.current_plan
        features_qs = SubscriptionFeatureAccess.objects.filter(
            plan=plan
        ).values_list('feature_name', 'is_enabled') if plan else []
        
        billing_history = BillingHistory.objects.filter(
            billing=subscription
        ).order_by('-created_at')[:10]
        
        context = {
            'subscription': subscription,
            'subscription_status': subscription.status,
            'warning_level': subscription.get_warning_level(),
            'features': dict(features_qs),
            'billing_history': billing_history,
            'days_remaining': subscription.get_days_remaining(),
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


# ============================================================================
# SUBSCRIPTION RECEIPT GENERATION
# ============================================================================

@login_required
@require_http_methods(["GET"])
def generate_subscription_receipt(request, transaction_id):
    """
    Generate and download a PDF receipt for a subscription payment
    """
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa
    import io
    
    try:
        # Resolve company from tenant-aware request context first
        company = getattr(request, 'company', None)
        if not company:
            company_profile = getattr(request.user, 'company_profile', None)
            company = getattr(company_profile, 'company', None) if company_profile else None
        if not company:
            company = getattr(request.user, 'company', None)
        if not company:
            return HttpResponse("Company not found", status=404)
        
        # Try to get from BillingHistory first
        try:
            billing_transaction = BillingHistory.objects.get(
                id=transaction_id,
                billing__company=company
            )
            
            receipt_data = {
                'transaction_id': billing_transaction.id,
                'invoice_number': billing_transaction.invoice_number,
                'transaction_date': billing_transaction.created_at,
                'transaction_type': billing_transaction.transaction_type,
                'description': billing_transaction.description or 'Subscription Payment',
                'amount': billing_transaction.amount,
                'payment_method': billing_transaction.payment_method or 'N/A',
                'reference': billing_transaction.transaction_id or f'TXN-{billing_transaction.id:06d}',
                'status': 'Completed',
                'company_name': company.company_name,
                'company_address': getattr(company, 'office_address', '') or getattr(company, 'location', '') or 'N/A',
                'company_email': getattr(company, 'email', '') or 'N/A',
                'plan_name': (getattr(getattr(company, 'billing', None), 'current_plan', None).name if getattr(company, 'billing', None) and getattr(company.billing, 'current_plan', None) else (company.subscription_tier or 'N/A')),
            }
        except BillingHistory.DoesNotExist:
            return HttpResponse("Transaction not found", status=404)
        
        # Generate HTML for PDF conversion
        receipt_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Payment Receipt - {receipt_data['invoice_number']}</title>
            <style>
                @page {{
                    size: A4;
                    margin: 1.5cm;
                }}
                body {{
                    font-family: Helvetica, Arial, sans-serif;
                    font-size: 12px;
                    color: #333;
                    line-height: 1.4;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 3px solid #16a34a;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }}
                .header h1 {{
                    color: #16a34a;
                    margin: 0;
                    font-size: 28px;
                }}
                .header p {{
                    margin: 5px 0;
                    color: #666;
                    font-size: 11px;
                }}
                .receipt-badge {{
                    background: #dcfce7;
                    color: #16a34a;
                    padding: 8px 20px;
                    display: inline-block;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 14px;
                    margin-top: 10px;
                }}
                .info-section {{
                    margin-bottom: 20px;
                    padding: 15px;
                    background: #f9fafb;
                    border-radius: 8px;
                }}
                .info-section h3 {{
                    color: #16a34a;
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 5px;
                }}
                .info-row {{
                    margin: 8px 0;
                }}
                .info-label {{
                    color: #6b7280;
                    font-size: 11px;
                }}
                .info-value {{
                    font-weight: bold;
                    color: #111;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background: #16a34a;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-size: 12px;
                }}
                td {{
                    padding: 12px;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .amount-cell {{
                    text-align: right;
                    font-weight: bold;
                }}
                .total-row td {{
                    background: #f0fdf4;
                    font-weight: bold;
                    font-size: 14px;
                }}
                .total-amount {{
                    color: #16a34a;
                    font-size: 18px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 10px;
                }}
                .watermark {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-45deg);
                    font-size: 80px;
                    color: rgba(22, 163, 74, 0.05);
                    font-weight: bold;
                    z-index: -1;
                }}
            </style>
        </head>
        <body>
            <div class="watermark">PAID</div>
            
            <div class="header">
                <h1>PAYMENT RECEIPT</h1>
                <p>Invoice: {receipt_data['invoice_number']}</p>
                <div class="receipt-badge">✓ PAYMENT SUCCESSFUL</div>
            </div>
            
            <table style="margin-bottom: 25px;">
                <tr>
                    <td style="width: 50%; vertical-align: top; border: none; padding: 0;">
                        <div class="info-section">
                            <h3>BILL TO</h3>
                            <div class="info-row">
                                <div class="info-value">{receipt_data['company_name']}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-label">{receipt_data['company_address']}</div>
                            </div>
                            <div class="info-row">
                                <div class="info-label">{receipt_data['company_email']}</div>
                            </div>
                        </div>
                    </td>
                    <td style="width: 50%; vertical-align: top; border: none; padding: 0 0 0 15px;">
                        <div class="info-section">
                            <h3>RECEIPT DETAILS</h3>
                            <div class="info-row">
                                <span class="info-label">Date: </span>
                                <span class="info-value">{receipt_data['transaction_date'].strftime('%B %d, %Y')}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Reference: </span>
                                <span class="info-value">{receipt_data['reference']}</span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">Payment Method: </span>
                                <span class="info-value">{receipt_data['payment_method']}</span>
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
            
            <table>
                <thead>
                    <tr>
                        <th style="width: 50%;">Description</th>
                        <th style="width: 25%;">Plan</th>
                        <th style="width: 25%; text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{receipt_data['description']}</td>
                        <td>{receipt_data['plan_name'].title()}</td>
                        <td class="amount-cell">₦{receipt_data['amount']:,.2f}</td>
                    </tr>
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="2" style="text-align: right;">TOTAL PAID:</td>
                        <td class="amount-cell total-amount">₦{receipt_data['amount']:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
            
            <div class="footer">
                <p><strong>Thank you for your payment!</strong></p>
                <p>This is a computer-generated receipt and does not require a signature.</p>
                <p>For any inquiries, please contact our support team.</p>
                <p style="margin-top: 15px; color: #9ca3af;">Generated on {receipt_data['transaction_date'].strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
        </body>
        </html>
        """
        
        # Create PDF from HTML using xhtml2pdf
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(receipt_html.encode("UTF-8")), result)
        
        if pdf.err:
            return HttpResponse("Error generating PDF", status=500)
        
        # Return PDF response
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Receipt_{receipt_data["invoice_number"]}.pdf"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating receipt: {str(e)}", status=500)
