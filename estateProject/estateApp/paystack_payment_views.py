"""
Paystack Payment Integration for Subscription Management
Handles payment verification and bank transfer virtual accounts
"""
import logging
import requests
import hashlib
import hmac
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import json

from estateApp.models import Company, Transaction, Estate, CustomUser, MarketerAffiliation, ClientMarketerAssignment
from superAdmin.models import SubscriptionPlan

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
PAYSTACK_BASE_URL = 'https://api.paystack.co'


@login_required
@require_http_methods(["POST"])
def validate_downgrade(request):
    """
    Validate if company can downgrade to selected plan based on current usage
    Returns usage comparison and whether downgrade is allowed
    """
    try:
        data = json.loads(request.body)
        target_plan_id = data.get('plan_id')
        
        if not target_plan_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing plan ID'
            }, status=400)
        
        # Get company
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'message': 'Company not found'
            }, status=404)
        
        # Define plan limits
        plan_limits = {
            'starter': {
                'max_estates': 25,
                'max_allocations': 50,
                'max_clients': 100,
                'max_marketers': 5,
                'max_properties': 50,
            },
            'professional': {
                'max_estates': 100,
                'max_allocations': 200,
                'max_clients': 500,
                'max_marketers': 25,
                'max_properties': 200,
            },
            'enterprise': {
                'max_estates': -1,  # Unlimited
                'max_allocations': -1,
                'max_clients': -1,
                'max_marketers': -1,
                'max_properties': -1,
            }
        }
        
        target_limits = plan_limits.get(target_plan_id.lower(), {})
        if not target_limits:
            return JsonResponse({
                'success': False,
                'message': 'Invalid plan ID'
            }, status=400)
        
        # Calculate current usage
        current_estates = Estate.objects.filter(company=company).count()
        
        # Count allocations (transactions)
        from estateApp.models import Transaction as TxnModel
        current_allocations = TxnModel.objects.filter(
            company=company,
            transaction_type__in=['full_payment', 'part_payment']
        ).count()
        
        # Count clients (primary + affiliated)
        primary_clients = CustomUser.objects.filter(
            role='client',
            company_profile=company
        ).count()
        affiliated_clients = ClientMarketerAssignment.objects.filter(
            company=company
        ).values('client_id').distinct().count()
        current_clients = primary_clients + affiliated_clients
        
        # Count marketers (primary + affiliated)
        primary_marketers = CustomUser.objects.filter(
            role='marketer',
            company_profile=company
        ).count()
        affiliated_marketers = MarketerAffiliation.objects.filter(
            company=company
        ).values('marketer_id').distinct().count()
        current_marketers = primary_marketers + affiliated_marketers
        
        # Count properties (same as estates for now)
        current_properties = current_estates
        
        # Check if current usage exceeds target limits
        exceeds = []
        usage_comparison = []
        
        resources = [
            ('estates', current_estates, target_limits['max_estates'], 'Estate Properties'),
            ('allocations', current_allocations, target_limits['max_allocations'], 'Allocations'),
            ('clients', current_clients, target_limits['max_clients'], 'Clients'),
            ('marketers', current_marketers, target_limits['max_marketers'], 'Marketers/Affiliates'),
            ('properties', current_properties, target_limits['max_properties'], 'Properties'),
        ]
        
        for resource_key, current_count, limit, display_name in resources:
            # -1 means unlimited
            if limit == -1:
                status = 'within'
                overage = 0
            elif current_count > limit:
                status = 'exceeds'
                overage = current_count - limit
                exceeds.append({
                    'resource': display_name,
                    'current': current_count,
                    'limit': limit,
                    'overage': overage
                })
            else:
                status = 'within'
                overage = 0
            
            usage_comparison.append({
                'resource': display_name,
                'current': current_count,
                'limit': limit if limit != -1 else 'Unlimited',
                'status': status,
                'overage': overage
            })
        
        can_downgrade = len(exceeds) == 0
        
        return JsonResponse({
            'success': True,
            'can_downgrade': can_downgrade,
            'usage_comparison': usage_comparison,
            'exceeds': exceeds,
            'message': 'Downgrade validation complete'
        })
        
    except Exception as e:
        logger.error(f'Downgrade validation error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def verify_paystack_payment(request):
    """
    Verify Paystack payment and activate subscription
    """
    try:
        data = json.loads(request.body)
        reference = data.get('reference')
        plan_id = data.get('plan_id')
        billing_cycle = data.get('billing_cycle', 'monthly')
        promo_code = data.get('promo_code', '')

        if not reference or not plan_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing payment reference or plan ID'
            }, status=400)

        # Get company
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'message': 'Company not found'
            }, status=404)

        # Verify payment with Paystack
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        response = requests.get(
            f'{PAYSTACK_BASE_URL}/transaction/verify/{reference}',
            headers=headers
        )

        if response.status_code != 200:
            return JsonResponse({
                'success': False,
                'message': 'Payment verification failed'
            }, status=400)

        payment_data = response.json()

        if not payment_data.get('status') or payment_data['data'].get('status') != 'success':
            return JsonResponse({
                'success': False,
                'message': 'Payment was not successful'
            }, status=400)

        # Get plan
        try:
            plan = SubscriptionPlan.objects.get(name__iexact=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Subscription plan not found'
            }, status=404)

        # Calculate subscription end date
        if billing_cycle == 'annual':
            end_date = timezone.now() + timedelta(days=365)
        else:
            end_date = timezone.now() + timedelta(days=30)

        # Activate subscription
        with transaction.atomic():
            # Update company subscription
            company.subscription_plan = plan
            company.subscription_tier = plan.name.lower()
            company.subscription_status = 'active'
            company.subscription_start_date = timezone.now()
            company.subscription_end_date = end_date
            company.subscription_billing_cycle = billing_cycle
            
            # Reset trial flags if any
            company.is_trial = False
            
            # Update limits based on plan
            if plan.name.lower() == 'enterprise':
                company.max_plots = -1  # Unlimited
                company.max_agents = -1
                company.max_clients = -1
                company.max_properties = -1
            else:
                # Set limited values based on plan
                if plan.name.lower() == 'professional':
                    company.max_plots = 100
                    company.max_agents = 25
                    company.max_clients = 500
                    company.max_properties = 200
                elif plan.name.lower() == 'starter':
                    company.max_plots = 25
                    company.max_agents = 5
                    company.max_clients = 100
                    company.max_properties = 50
            
            company.save()

            # Record transaction
            amount = payment_data['data']['amount'] / 100  # Convert from kobo to naira
            Transaction.objects.create(
                company=company,
                transaction_type='subscription',
                amount=Decimal(str(amount)),
                status='completed',
                payment_method='paystack',
                reference_number=reference,
                description=f'{plan.name} Subscription - {billing_cycle.capitalize()}',
                metadata={
                    'plan': plan.name,
                    'billing_cycle': billing_cycle,
                    'promo_code': promo_code,
                    'paystack_data': payment_data['data']
                }
            )

            logger.info(f'Subscription activated for company {company.id}: {plan.name} - {billing_cycle}')

        return JsonResponse({
            'success': True,
            'message': 'Subscription activated successfully',
            'subscription': {
                'plan': plan.name,
                'billing_cycle': billing_cycle,
                'end_date': end_date.isoformat(),
            }
        })

    except Exception as e:
        logger.error(f'Payment verification error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_virtual_account(request):
    """
    Generate Paystack dedicated virtual account for bank transfer
    """
    try:
        data = json.loads(request.body)
        reference = data.get('reference')
        plan_id = data.get('plan_id')
        plan_name = data.get('plan_name')
        billing_cycle = data.get('billing_cycle', 'monthly')
        amount = data.get('amount')
        promo_code = data.get('promo_code', '')
        discount = data.get('discount', 0)

        if not reference or not plan_id or not amount:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)

        # Get company
        company = request.user.company
        if not company:
            return JsonResponse({
                'success': False,
                'message': 'Company not found'
            }, status=404)

        # Create or get dedicated virtual account with Paystack
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        # Check if customer exists
        customer_code = None
        if hasattr(company, 'paystack_customer_code') and company.paystack_customer_code:
            customer_code = company.paystack_customer_code
        else:
            # Create customer
            customer_payload = {
                'email': request.user.email,
                'first_name': company.name,
                'last_name': 'Subscription',
                'phone': company.phone_number if hasattr(company, 'phone_number') else '',
            }

            customer_response = requests.post(
                f'{PAYSTACK_BASE_URL}/customer',
                json=customer_payload,
                headers=headers
            )

            if customer_response.status_code == 200:
                customer_data = customer_response.json()
                if customer_data.get('status'):
                    customer_code = customer_data['data']['customer_code']
                    # Save customer code to company
                    company.paystack_customer_code = customer_code
                    company.save(update_fields=['paystack_customer_code'])

        if not customer_code:
            return JsonResponse({
                'success': False,
                'message': 'Failed to create customer account'
            }, status=400)

        # Create dedicated virtual account
        dva_payload = {
            'customer': customer_code,
            'preferred_bank': 'wema-bank',  # You can make this configurable
        }

        dva_response = requests.post(
            f'{PAYSTACK_BASE_URL}/dedicated_account',
            json=dva_payload,
            headers=headers
        )

        if dva_response.status_code != 200:
            return JsonResponse({
                'success': False,
                'message': 'Failed to generate virtual account'
            }, status=400)

        dva_data = dva_response.json()

        if not dva_data.get('status'):
            return JsonResponse({
                'success': False,
                'message': 'Failed to generate virtual account'
            }, status=400)

        account_data = dva_data['data']

        # Store transaction pending record
        Transaction.objects.create(
            company=company,
            transaction_type='subscription_pending',
            amount=Decimal(str(amount)),
            status='pending',
            payment_method='bank_transfer',
            reference_number=reference,
            description=f'{plan_name} Subscription - {billing_cycle.capitalize()} (Pending Transfer)',
            metadata={
                'plan_id': plan_id,
                'plan_name': plan_name,
                'billing_cycle': billing_cycle,
                'promo_code': promo_code,
                'discount': discount,
                'account_number': account_data.get('account_number'),
                'account_name': account_data.get('account_name'),
                'bank_name': account_data.get('bank', {}).get('name', 'Wema Bank'),
            }
        )

        return JsonResponse({
            'success': True,
            'account': {
                'account_number': account_data.get('account_number'),
                'account_name': account_data.get('account_name'),
                'bank_name': account_data.get('bank', {}).get('name', 'Wema Bank'),
                'bank_id': account_data.get('bank', {}).get('id'),
            },
            'reference': reference,
        })

    except Exception as e:
        logger.error(f'Virtual account generation error: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """
    Handle Paystack webhooks for payment notifications
    Especially important for bank transfer confirmations
    """
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Paystack-Signature')
        body = request.body.decode('utf-8')

        hash_object = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha512
        )
        expected_signature = hash_object.hexdigest()

        if signature != expected_signature:
            logger.warning('Invalid Paystack webhook signature')
            return JsonResponse({'status': 'invalid signature'}, status=400)

        # Process webhook event
        event_data = json.loads(body)
        event_type = event_data.get('event')

        if event_type == 'charge.success':
            # Payment successful
            data = event_data.get('data', {})
            reference = data.get('reference')
            
            if reference:
                # Find pending transaction
                try:
                    txn = Transaction.objects.get(
                        reference_number=reference,
                        status='pending'
                    )
                    
                    # Get plan from metadata
                    plan_id = txn.metadata.get('plan_id')
                    billing_cycle = txn.metadata.get('billing_cycle', 'monthly')
                    
                    # Get plan
                    plan = SubscriptionPlan.objects.get(name__iexact=plan_id)
                    
                    # Calculate end date
                    if billing_cycle == 'annual':
                        end_date = timezone.now() + timedelta(days=365)
                    else:
                        end_date = timezone.now() + timedelta(days=30)
                    
                    # Activate subscription
                    with transaction.atomic():
                        company = txn.company
                        company.subscription_plan = plan
                        company.subscription_tier = plan.name.lower()
                        company.subscription_status = 'active'
                        company.subscription_start_date = timezone.now()
                        company.subscription_end_date = end_date
                        company.subscription_billing_cycle = billing_cycle
                        company.is_trial = False
                        
                        # Update limits
                        if plan.name.lower() == 'enterprise':
                            company.max_plots = -1
                            company.max_agents = -1
                            company.max_clients = -1
                            company.max_properties = -1
                        else:
                            if plan.name.lower() == 'professional':
                                company.max_plots = 100
                                company.max_agents = 25
                                company.max_clients = 500
                                company.max_properties = 200
                            elif plan.name.lower() == 'starter':
                                company.max_plots = 25
                                company.max_agents = 5
                                company.max_clients = 100
                                company.max_properties = 50
                        
                        company.save()
                        
                        # Update transaction
                        txn.status = 'completed'
                        txn.transaction_type = 'subscription'
                        txn.metadata['webhook_data'] = data
                        txn.save()
                        
                        logger.info(f'Webhook: Subscription activated for company {company.id}')
                
                except Transaction.DoesNotExist:
                    logger.warning(f'Webhook: Transaction not found for reference {reference}')
                except Exception as e:
                    logger.error(f'Webhook processing error: {str(e)}')

        return JsonResponse({'status': 'success'})

    except Exception as e:
        logger.error(f'Webhook error: {str(e)}')
        return JsonResponse({'status': 'error'}, status=500)
