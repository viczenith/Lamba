"""
Comprehensive Billing & Subscription Management Views
Handles plan selection, upgrades, downgrades, and payment processing
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
import json
import logging
import requests
import hashlib
import hmac

from .models import Company, CustomUser
from superAdmin.models import SubscriptionPlan
from .subscription_billing_models import SubscriptionBillingModel, BillingHistory
from .payment_integration import PaystackPaymentProcessor

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
PAYSTACK_PUBLIC_KEY = getattr(settings, 'PAYSTACK_PUBLIC_KEY', None)


def get_user_company(request):
    """Helper to get company from request"""
    company = getattr(request, 'company', None)
    if not company:
        company = getattr(request.user, 'company_profile', None)
    if not company:
        company = getattr(request.user, 'company', None)
    return company


@login_required
@require_http_methods(["GET"])
def get_billing_context(request):
    """
    Get complete billing context for the billing page
    Returns subscription status, plans, history, and user's current plan
    """
    company = get_user_company(request)
    if not company:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    try:
        # Get or create subscription billing
        billing, created = SubscriptionBillingModel.objects.get_or_create(
            company=company,
            defaults={
                'status': 'trial',
                'trial_started_at': timezone.now(),
                'trial_ends_at': timezone.now() + timedelta(days=14),
                'billing_cycle': 'monthly',
                'auto_renew': False,
                'payment_method': 'free_trial',
            }
        )
        
        billing.refresh_status()
        
        # Get current plan details
        current_plan = billing.current_plan
        plan_tier = current_plan.tier if current_plan else 'starter'
        plan_name = current_plan.name if current_plan else 'Trial'
        
        # Get all available plans
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('monthly_price')
        logger.info(f"📊 Found {plans.count()} active subscription plans")
        logger.info(f"📋 Plans: {[f'{p.name} ({p.tier})' for p in plans]}")
        plans_data = []
        
        plan_hierarchy = {'starter': 1, 'professional': 2, 'enterprise': 3}
        current_tier_level = plan_hierarchy.get(plan_tier, 0)
        
        for plan in plans:
            plan_tier_level = plan_hierarchy.get(plan.tier, 0)
            
            # Determine if this is current plan
            is_current = plan.tier == plan_tier and billing.status in ['active', 'trial']
            
            # Determine if this is an upgrade, downgrade, or current
            relationship = 'current' if is_current else ('upgrade' if plan_tier_level > current_tier_level else 'downgrade')
            
            plan_dict = {
                'id': plan.id,
                'name': plan.name,
                'tier': plan.tier,
                'description': plan.description,
                'monthly_price': float(plan.monthly_price),
                'annual_price': float(plan.annual_price or plan.monthly_price * 10),
                'max_plots': plan.max_plots,
                'max_agents': plan.max_agents,
                'max_estates': plan.max_estates if hasattr(plan, 'max_estates') else 999999,
                'max_clients': plan.max_clients if hasattr(plan, 'max_clients') else 999999,
                'max_allocations': plan.max_allocations if hasattr(plan, 'max_allocations') else 999999,
                'max_affiliates': plan.max_affiliates if hasattr(plan, 'max_affiliates') else 999999,
                'features': plan.features,
                'is_active': plan.is_active,
                'is_current': is_current,
                'relationship': relationship,
                'tier_level': plan_tier_level
            }
            logger.info(f"✅ Added plan: {plan.name} - ${plan.monthly_price}")
            plans_data.append(plan_dict)
        
        logger.info(f"📦 Returning {len(plans_data)} plans to frontend")
        
        # Get billing history
        billing_history = BillingHistory.objects.filter(
            billing=billing
        ).order_by('-created_at')[:20]
        
        history_data = [{
            'id': bh.id,
            'invoice_number': bh.invoice_number,
            'amount': float(bh.amount),
            'status': bh.state,
            'date': bh.created_at.isoformat(),
            'description': bh.description,
            'payment_method': bh.payment_method
        } for bh in billing_history]
        
        # Calculate subscription status details
        end_date = billing.subscription_ends_at or billing.trial_ends_at
        days_remaining = 0
        if end_date and end_date > timezone.now():
            days_remaining = (end_date - timezone.now()).days
        
        # Check for subscription warnings
        is_expiring_soon = days_remaining > 0 and days_remaining <= 7
        is_expired = billing.status in ['grace', 'expired', 'suspended']
        is_grace_period = billing.is_grace_period()
        grace_period_expired = billing.status == 'expired'
        
        grace_period_end = None
        if billing.grace_period_ends_at:
            grace_period_end = billing.grace_period_ends_at.isoformat()
        
        return JsonResponse({
            'success': True,
            'subscription': {
                'id': billing.id,
                'status': billing.status,
                'plan_tier': plan_tier,
                'plan_name': plan_name,
                'is_trial': billing.is_trial(),
                'is_active': billing.is_active(),
                'billing_cycle': billing.billing_cycle,
                'amount': float(billing.monthly_amount if billing.billing_cycle == 'monthly' else billing.annual_amount),
                'auto_renew': billing.auto_renew,
                'payment_method': billing.payment_method,
                'subscription_end_date': end_date.isoformat() if end_date else None,
                'days_remaining': days_remaining,
                'is_expiring_soon': is_expiring_soon,
                'is_expired': is_expired,
                'is_grace_period': is_grace_period,
                'grace_period_expired': grace_period_expired,
                'grace_period_end_date': grace_period_end,
                'is_trial_expiration': billing.is_trial() and is_expiring_soon,
            },
            'plans': plans_data,
            'billing_history': history_data,
            'paystack_public_key': PAYSTACK_PUBLIC_KEY
        })
        
    except Exception as e:
        logger.error(f"Error getting billing context: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_protect
def validate_plan_change(request):
    """
    Validate if a plan change is allowed and return warnings if downgrading
    """
    company = get_user_company(request)
    if not company:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        new_plan_tier = data.get('plan_tier')
        
        if not new_plan_tier:
            return JsonResponse({'error': 'Plan tier required'}, status=400)
        
        # Get current and new plans
        billing = SubscriptionBillingModel.objects.get(company=company)
        current_plan = billing.current_plan
        new_plan = SubscriptionPlan.objects.get(tier=new_plan_tier)
        
        plan_hierarchy = {'starter': 1, 'professional': 2, 'enterprise': 3}
        current_tier_level = plan_hierarchy.get(current_plan.tier if current_plan else 'starter', 0)
        new_tier_level = plan_hierarchy.get(new_plan_tier, 0)
        
        is_downgrade = new_tier_level < current_tier_level
        is_upgrade = new_tier_level > current_tier_level
        is_same = new_tier_level == current_tier_level
        
        # If it's the same plan, just allow renewal
        if is_same:
            return JsonResponse({
                'success': True,
                'action': 'renew',
                'message': 'This will renew your current subscription'
            })
        
        # If it's an upgrade, always allow
        if is_upgrade:
            return JsonResponse({
                'success': True,
                'action': 'upgrade',
                'message': f'Upgrading from {current_plan.name if current_plan else "Trial"} to {new_plan.name}'
            })
        
        # If it's a downgrade, check usage and warn
        if is_downgrade:
            from .models import Estate, ClientUser, MarketerUser, PlotAllocation
            
            # Check current usage
            current_estates = Estate.objects.filter(company=company).count()
            current_clients = ClientUser.objects.filter(company=company).count()
            current_marketers = MarketerUser.objects.filter(company_profile=company).count()
            current_allocations = PlotAllocation.objects.filter(company=company).count()
            
            # Check new plan limits
            new_estate_limit = new_plan.features.get('estate_properties', 999999)
            new_allocation_limit = new_plan.features.get('allocations', 999999)
            new_client_limit = new_plan.features.get('clients', 999999)
            new_affiliate_limit = new_plan.features.get('affiliates', 999999)
            
            # Convert 'unlimited' to large number
            if isinstance(new_estate_limit, str) and new_estate_limit.lower() == 'unlimited':
                new_estate_limit = 999999
            if isinstance(new_allocation_limit, str) and new_allocation_limit.lower() == 'unlimited':
                new_allocation_limit = 999999
            if isinstance(new_client_limit, str) and new_client_limit.lower() == 'unlimited':
                new_client_limit = 999999
            if isinstance(new_affiliate_limit, str) and new_affiliate_limit.lower() == 'unlimited':
                new_affiliate_limit = 999999
            
            warnings = []
            exceeded_limits = []
            
            # Check if current usage exceeds new limits
            if current_estates > int(new_estate_limit):
                warnings.append(f'You currently have {current_estates} estate properties, but the {new_plan.name} plan only allows {new_estate_limit}')
                exceeded_limits.append('estate_properties')
            
            if current_allocations > int(new_allocation_limit):
                warnings.append(f'You currently have {current_allocations} allocations, but the {new_plan.name} plan only allows {new_allocation_limit}')
                exceeded_limits.append('allocations')
            
            if current_clients > int(new_client_limit):
                warnings.append(f'You currently have {current_clients} clients, but the {new_plan.name} plan only allows {new_client_limit}')
                exceeded_limits.append('clients')
            
            if current_marketers > int(new_affiliate_limit):
                warnings.append(f'You currently have {current_marketers} affiliates, but the {new_plan.name} plan only allows {new_affiliate_limit}')
                exceeded_limits.append('affiliates')
            
            if warnings:
                return JsonResponse({
                    'success': True,
                    'action': 'downgrade',
                    'requires_confirmation': True,
                    'warnings': warnings,
                    'exceeded_limits': exceeded_limits,
                    'current_usage': {
                        'estates': current_estates,
                        'allocations': current_allocations,
                        'clients': current_clients,
                        'marketers': current_marketers
                    },
                    'new_limits': {
                        'estates': int(new_estate_limit),
                        'allocations': int(new_allocation_limit),
                        'clients': int(new_client_limit),
                        'affiliates': int(new_affiliate_limit)
                    },
                    'message': f'⚠️ Warning: Downgrading from {current_plan.name} to {new_plan.name} will limit your features. Some functionality may be disabled.'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'action': 'downgrade',
                    'message': f'Downgrading from {current_plan.name} to {new_plan.name}'
                })
        
        return JsonResponse({'success': True, 'action': 'allowed'})
        
    except SubscriptionBillingModel.DoesNotExist:
        return JsonResponse({'error': 'No active subscription found'}, status=404)
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'error': 'Invalid plan'}, status=400)
    except Exception as e:
        logger.error(f"Error validating plan change: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_protect
def initiate_payment(request):
    """
    Initiate payment for subscription (new, upgrade, or renewal)
    Supports both Paystack and Bank Transfer
    """
    company = get_user_company(request)
    if not company:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        plan_tier = data.get('plan_tier')
        billing_cycle = data.get('billing_cycle', 'monthly')
        payment_method = data.get('payment_method', 'paystack')
        
        if not plan_tier:
            return JsonResponse({'error': 'Plan tier required'}, status=400)
        
        # Get plan
        new_plan = SubscriptionPlan.objects.get(tier=plan_tier)
        
        # Calculate amount
        amount = new_plan.annual_price if billing_cycle == 'annual' else new_plan.monthly_price
        
        # Get or create billing record
        billing, created = SubscriptionBillingModel.objects.get_or_create(company=company)
        
        # Generate reference
        import uuid
        reference = f"SUB-{company.id}-{uuid.uuid4().hex[:8].upper()}"
        
        if payment_method == 'paystack':
            # Initialize Paystack transaction
            transaction_data = PaystackPaymentProcessor.initialize_transaction(
                company,
                request.user.email or company.email,
                float(amount),
                plan_tier,
                billing_cycle
            )
            
            if not transaction_data:
                return JsonResponse({'error': 'Failed to initialize payment'}, status=500)
            
            # Log pending transaction
            BillingHistory.objects.create(
                billing=billing,
                transaction_type='charge',
                state='pending',
                amount=amount,
                currency='NGN',
                description=f"Subscription payment - {new_plan.name} ({billing_cycle})",
                transaction_id=transaction_data['reference'],
                billing_date=timezone.now(),
                due_date=timezone.now().date(),
                invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                payment_method='paystack'
            )
            
            return JsonResponse({
                'success': True,
                'payment_method': 'paystack',
                'authorization_url': transaction_data['authorization_url'],
                'reference': transaction_data['reference'],
                'amount': float(amount)
            })
        
        elif payment_method == 'bank_transfer':
            # For bank transfer, create a dedicated virtual account using Paystack
            # or return static bank details
            
            # Option 1: Use Paystack Dedicated Virtual Account (DVA)
            dva_data = create_dedicated_virtual_account(company, request.user.email or company.email)
            
            if dva_data:
                # Log pending transaction
                BillingHistory.objects.create(
                    billing=billing,
                    transaction_type='charge',
                    state='pending',
                    amount=amount,
                    currency='NGN',
                    description=f"Bank transfer - {new_plan.name} ({billing_cycle})",
                    transaction_id=reference,
                    billing_date=timezone.now(),
                    due_date=timezone.now().date(),
                    invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                    payment_method='bank_transfer'
                )
                
                return JsonResponse({
                    'success': True,
                    'payment_method': 'bank_transfer',
                    'bank_details': dva_data,
                    'reference': reference,
                    'amount': float(amount),
                    'plan_name': new_plan.name,
                    'billing_cycle': billing_cycle
                })
            else:
                # Fallback to static bank details
                return JsonResponse({
                    'success': True,
                    'payment_method': 'bank_transfer',
                    'bank_details': {
                        'bank_name': 'First Bank of Nigeria',
                        'account_number': '3124567890',
                        'account_name': 'Real Estate MS Limited',
                        'payment_reference': reference
                    },
                    'reference': reference,
                    'amount': float(amount),
                    'plan_name': new_plan.name,
                    'billing_cycle': billing_cycle
                })
        
        else:
            return JsonResponse({'error': 'Invalid payment method'}, status=400)
        
    except SubscriptionPlan.DoesNotExist:
        return JsonResponse({'error': 'Invalid plan'}, status=400)
    except Exception as e:
        logger.error(f"Error initiating payment: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def create_dedicated_virtual_account(company, email):
    """
    Create a dedicated virtual account for the company using Paystack DVA
    This allows customers to receive a unique account number for payments
    """
    if not PAYSTACK_SECRET_KEY:
        return None
    
    url = "https://api.paystack.co/dedicated_account"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "customer": email,
        "preferred_bank": "wema-bank",  # or "titan-paystack"
        "subaccount": None,  # Optional: link to subaccount
        "first_name": company.company_name.split()[0] if company.company_name else "Company",
        "last_name": company.company_name.split()[-1] if company.company_name and len(company.company_name.split()) > 1 else "User",
        "phone": company.phone_number or "+2348000000000"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        if data.get('status'):
            account_data = data['data']
            return {
                'bank_name': account_data.get('bank', {}).get('name', 'Wema Bank'),
                'account_number': account_data.get('account_number'),
                'account_name': account_data.get('account_name'),
                'is_dynamic': True
            }
        else:
            logger.error(f"Paystack DVA creation failed: {data.get('message')}")
            return None
    except Exception as e:
        logger.error(f"Error creating dedicated virtual account: {str(e)}")
        return None


@csrf_exempt
@require_POST
def paystack_webhook_handler(request):
    """
    Handle Paystack webhooks for payment notifications
    Verifies signature and processes successful payments
    """
    # Verify webhook signature
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    if not signature:
        logger.error("Paystack webhook: No signature provided")
        return JsonResponse({'error': 'No signature'}, status=400)
    
    payload = request.body
    
    try:
        # Compute signature
        hash_object = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        )
        computed_signature = hash_object.hexdigest()
        
        if signature != computed_signature:
            logger.error("Paystack webhook: Invalid signature")
            return JsonResponse({'error': 'Invalid signature'}, status=400)
        
        # Parse event data
        event_data = json.loads(payload.decode('utf-8'))
        event = event_data.get('event')
        data = event_data.get('data', {})
        
        logger.info(f"Paystack webhook received: {event}")
        
        if event == 'charge.success':
            # Extract metadata
            metadata = data.get('metadata', {})
            company_id = metadata.get('company_id')
            plan_tier = metadata.get('plan_tier')
            billing_cycle = metadata.get('billing_cycle', 'monthly')
            
            if not company_id:
                logger.error("Paystack webhook: No company_id in metadata")
                return JsonResponse({'error': 'Missing company_id'}, status=400)
            
            try:
                company = Company.objects.get(id=company_id)
                billing = SubscriptionBillingModel.objects.get(company=company)
                
                # Get the plan
                plan = SubscriptionPlan.objects.get(tier=plan_tier)
                
                # Update subscription
                with transaction.atomic():
                    billing.current_plan = plan
                    billing.status = 'active'
                    billing.billing_cycle = billing_cycle
                    billing.last_payment_date = timezone.now()
                    billing.payment_method = 'paystack'
                    billing.paystack_subscription_code = data.get('reference')
                    
                    # Set subscription dates
                    billing.subscription_started_at = timezone.now()
                    if billing_cycle == 'annual':
                        billing.subscription_ends_at = timezone.now() + timedelta(days=365)
                        billing.annual_amount = Decimal(data.get('amount', 0)) / 100
                    else:
                        billing.subscription_ends_at = timezone.now() + timedelta(days=30)
                        billing.monthly_amount = Decimal(data.get('amount', 0)) / 100
                    
                    billing.next_billing_date = billing.subscription_ends_at.date()
                    
                    # Clear grace period if any
                    billing.grace_period_started_at = None
                    billing.grace_period_ends_at = None
                    
                    billing.save()
                    billing._sync_company_subscription_fields()
                    
                    # Update billing history
                    BillingHistory.objects.filter(
                        billing=billing,
                        transaction_id=data.get('reference'),
                        state='pending'
                    ).update(
                        state='completed',
                        paid_date=timezone.now()
                    )
                    
                    # Create new billing record if not exists
                    if not BillingHistory.objects.filter(transaction_id=data.get('reference')).exists():
                        BillingHistory.objects.create(
                            billing=billing,
                            transaction_type='charge',
                            state='completed',
                            amount=Decimal(data.get('amount', 0)) / 100,
                            currency='NGN',
                            description=f"Subscription payment - {plan.name} ({billing_cycle})",
                            transaction_id=data.get('reference'),
                            billing_date=timezone.now(),
                            due_date=timezone.now().date(),
                            paid_date=timezone.now(),
                            invoice_number=f"PST-{data.get('reference', '')[:20]}",
                            payment_method='paystack'
                        )
                
                logger.info(f"Payment successful for company {company_id}, plan {plan_tier}")
                
                # TODO: Send confirmation email
                
                return JsonResponse({'status': 'success'})
                
            except (Company.DoesNotExist, SubscriptionBillingModel.DoesNotExist, SubscriptionPlan.DoesNotExist) as e:
                logger.error(f"Paystack webhook error: {str(e)}")
                return JsonResponse({'error': str(e)}, status=400)
        
        # Handle other events as needed
        elif event == 'dedicatedaccount.assign.success':
            # Dedicated virtual account assigned
            logger.info(f"Dedicated account assigned: {data}")
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        logger.error("Paystack webhook: Invalid JSON")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Paystack webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_protect
def confirm_bank_transfer(request):
    """
    User confirms they've made a bank transfer
    Mark transaction as pending verification
    """
    company = get_user_company(request)
    if not company:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        reference = data.get('reference')
        
        if not reference:
            return JsonResponse({'error': 'Reference required'}, status=400)
        
        billing = SubscriptionBillingModel.objects.get(company=company)
        
        # Update billing history
        BillingHistory.objects.filter(
            billing=billing,
            transaction_id=reference,
            state='pending'
        ).update(
            state='verification_pending',
            description='Bank transfer confirmation received - pending verification'
        )
        
        logger.info(f"Bank transfer confirmation received for company {company.id}, reference {reference}")
        
        # TODO: Send notification to admin for manual verification
        
        return JsonResponse({
            'success': True,
            'message': 'Transfer confirmation received. Your subscription will be activated within 24 hours after verification.'
        })
        
    except SubscriptionBillingModel.DoesNotExist:
        return JsonResponse({'error': 'No subscription found'}, status=404)
    except Exception as e:
        logger.error(f"Error confirming bank transfer: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_invoices(request):
    """
    Get all invoices for the company
    """
    company = get_user_company(request)
    if not company:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    try:
        billing = SubscriptionBillingModel.objects.get(company=company)
        
        invoices = BillingHistory.objects.filter(
            billing=billing,
            transaction_type='charge'
        ).order_by('-created_at')[:50]
        
        invoices_data = [{
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'amount': float(inv.amount),
            'currency': inv.currency,
            'status': inv.state,
            'date': inv.created_at.isoformat(),
            'paid_date': inv.paid_date.isoformat() if inv.paid_date else None,
            'description': inv.description,
            'payment_method': inv.payment_method
        } for inv in invoices]
        
        return JsonResponse({
            'success': True,
            'invoices': invoices_data
        })
        
    except SubscriptionBillingModel.DoesNotExist:
        return JsonResponse({
            'success': True,
            'invoices': []
        })
    except Exception as e:
        logger.error(f"Error getting invoices: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def validate_promo_code(request):
    """
    Validate a promo code and return discount details
    """
    from .models import PromoCode
    from django.utils import timezone
    
    company = get_user_company(request)
    if not company:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        plan_id = data.get('plan_id')
        amount = Decimal(str(data.get('amount', 0)))
        
        if not code:
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': 'Promo code is required'
            })
        
        # Find the promo code
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
        except PromoCode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': 'Invalid promo code'
            })
        
        # Check if promo code is valid
        if not promo.is_valid():
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': 'This promo code has expired or reached its usage limit'
            })
        
        # Check validity dates
        now = timezone.now().date()
        if promo.valid_from and now < promo.valid_from:
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': f'This promo code is not valid yet. Valid from {promo.valid_from}'
            })
        
        if promo.valid_until and now > promo.valid_until:
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': 'This promo code has expired'
            })
        
        # Check minimum amount
        if promo.minimum_amount and amount < promo.minimum_amount:
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': f'Minimum order amount of ₦{promo.minimum_amount:,.0f} required'
            })
        
        # Check applicable plans
        if promo.applicable_plans:
            applicable_plan_ids = promo.applicable_plans if isinstance(promo.applicable_plans, list) else []
            if plan_id and applicable_plan_ids and plan_id not in applicable_plan_ids:
                return JsonResponse({
                    'success': False,
                    'valid': False,
                    'message': 'This promo code is not applicable to the selected plan'
                })
        
        # Calculate discount
        discount_amount = promo.calculate_discount(amount)
        
        return JsonResponse({
            'success': True,
            'valid': True,
            'message': 'Promo code applied successfully',
            'promo_code': {
                'id': promo.id,
                'code': promo.code,
                'discount_type': promo.discount_type,
                'discount_value': float(promo.discount_value),
                'discount_amount': float(discount_amount),
                'description': promo.description,
                'minimum_amount': float(promo.minimum_amount) if promo.minimum_amount else None,
                'applicable_plans': promo.applicable_plans
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(f"Error validating promo code: {str(e)}")
        return JsonResponse({'success': False, 'message': 'An error occurred'}, status=500)
