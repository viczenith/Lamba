#!/usr/bin/env python
"""Test subscription serialization"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, SubscriptionPlan

print("Testing Subscription Serialization...")
print("=" * 70)

company = Company.objects.first()
if not company:
    print("❌ No company found")
    exit(1)

print(f"Company: {company.company_name}")
print(f"  - subscription_tier: {company.subscription_tier}")
print(f"  - subscription_status: {company.subscription_status}")
print(f"  - subscription_started_at: {company.subscription_started_at}")
print(f"  - subscription_ends_at: {company.subscription_ends_at}")
print(f"  - trial_ends_at: {company.trial_ends_at}")

# Get plan
plan = company.get_current_plan()
print(f"\nPlan: {plan}")
if plan:
    print(f"  - name: {plan.name}")
    print(f"  - tier: {plan.tier}")
    print(f"  - monthly_price: {plan.monthly_price} (type: {type(plan.monthly_price)})")
    print(f"  - max_plots: {plan.max_plots}")
    print(f"  - max_agents: {plan.max_agents}")
    print(f"  - max_api_calls_daily: {plan.max_api_calls_daily}")

# Get billing status
billing_status = company.get_billing_status()
print(f"\nBilling Status: {billing_status}")

# Get usage
usage = company.get_usage_percentage()
print(f"\nUsage: {usage}")

# Try to serialize as JSON
print("\n" + "=" * 70)
print("Testing JSON Serialization...")

try:
    # Build the response manually
    response_data = {
        'subscription': {
            'tier': company.subscription_tier,
            'status': company.subscription_status,
            'plan': {
                'name': plan.name if plan else 'Unknown',
                'monthly_price': float(plan.monthly_price) if plan else 0,
                'max_plots': plan.max_plots if plan else company.max_plots,
                'max_agents': plan.max_agents if plan else company.max_agents,
                'max_api_calls_daily': plan.max_api_calls_daily if plan else company.max_api_calls_daily,
            } if plan else None,
            'started_at': company.subscription_started_at.isoformat() if company.subscription_started_at else None,
            'renewal_date': company.subscription_ends_at.isoformat() if company.subscription_ends_at else None,
            'trial_ends_at': company.trial_ends_at.isoformat() if company.trial_ends_at else None,
        },
        'usage': {
            'plots': {
                'current': company.current_plots_count,
                'max': company.max_plots,
                'percentage': usage['plots'],
            },
            'agents': {
                'current': company.current_agents_count,
                'max': company.max_agents,
                'percentage': usage['agents'],
            },
            'api_calls': {
                'today': company.api_calls_today,
                'max_daily': company.max_api_calls_daily,
                'percentage': (company.api_calls_today / company.max_api_calls_daily * 100) if company.max_api_calls_daily > 0 else 0,
            },
        },
        'billing_status': billing_status,
        'days_remaining': None,
    }
    
    # Calculate days remaining
    from django.utils import timezone
    if company.subscription_ends_at:
        if hasattr(company.subscription_ends_at, 'date'):
            end_date = company.subscription_ends_at.date()
        else:
            end_date = company.subscription_ends_at
        response_data['days_remaining'] = (end_date - timezone.now().date()).days
    
    # Try to serialize
    json_str = json.dumps(response_data, default=str)
    print("✓ JSON Serialization: SUCCESS")
    print(f"  - Size: {len(json_str)} bytes")
    print(f"  - Content (first 500 chars): {json_str[:500]}...")
    
except Exception as e:
    print(f"❌ JSON Serialization Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
