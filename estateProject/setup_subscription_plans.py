#!/usr/bin/env python
"""Create subscription plans for multi-tenant SaaS"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import SubscriptionPlan

# Create Starter Plan
starter, created = SubscriptionPlan.objects.get_or_create(
    tier='starter',
    defaults={
        'name': 'Starter Plan',
        'description': 'Perfect for small real estate companies just getting started',
        'monthly_price': 15000,
        'annual_price': 162000,  # 10% discount
        'max_plots': 50,
        'max_agents': 1,
        'max_api_calls_daily': 1000,
        'features': {
            'reports': True,
            'bulk_import': False,
            'api_access': False,
            'custom_domain': False,
            'priority_support': False
        }
    }
)
print(f"{'✅ Created' if created else '⚠️  Exists'}: {starter.name} - ₦{starter.monthly_price:,.2f}/month")

# Create Professional Plan
professional, created = SubscriptionPlan.objects.get_or_create(
    tier='professional',
    defaults={
        'name': 'Professional Plan',
        'description': 'For growing companies managing multiple properties',
        'monthly_price': 45000,
        'annual_price': 486000,  # 10% discount
        'max_plots': 500,
        'max_agents': 10,
        'max_api_calls_daily': 10000,
        'features': {
            'reports': True,
            'bulk_import': True,
            'api_access': True,
            'custom_domain': False,
            'priority_support': True
        }
    }
)
print(f"{'✅ Created' if created else '⚠️  Exists'}: {professional.name} - ₦{professional.monthly_price:,.2f}/month")

# Create Enterprise Plan
enterprise, created = SubscriptionPlan.objects.get_or_create(
    tier='enterprise',
    defaults={
        'name': 'Enterprise Plan',
        'description': 'For large companies with unlimited needs',
        'monthly_price': 100000,
        'annual_price': 1080000,  # 10% discount
        'max_plots': 999999,  # Unlimited
        'max_agents': 999999,  # Unlimited
        'max_api_calls_daily': 100000,
        'features': {
            'reports': True,
            'bulk_import': True,
            'api_access': True,
            'custom_domain': True,
            'priority_support': True,
            'dedicated_account_manager': True,
            'white_label': True
        }
    }
)
print(f"{'✅ Created' if created else '⚠️  Exists'}: {enterprise.name} - ₦{enterprise.monthly_price:,.2f}/month")

print("\n✅ All subscription plans are ready!")
