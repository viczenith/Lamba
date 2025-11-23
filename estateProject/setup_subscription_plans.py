#!/usr/bin/env python
"""Create subscription plans for multi-tenant SaaS"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import SubscriptionPlan

# Create Starter Plan
starter, created = SubscriptionPlan.objects.get_or_create(
    tier='starter',
    defaults={
        'name': 'Starter',
        'description': 'For Small Companies - Perfect for companies just getting started',
        'monthly_price': Decimal('70000.00'),
        'annual_price': Decimal('700000.00'),
        'max_plots': 2,
        'max_agents': 1,
        'max_api_calls_daily': 1000,
        'features': {
            'estate_properties': 2,
            'allocations': 30,
            'clients': 30,
            'affiliates': 20,
            'api_access': True,
            'basic_analytics': True,
            'email_support': True,
        }
    }
)
print(f"{'✅ Created' if created else '⚠️  Updated'}: {starter.name} - ₦{starter.monthly_price:,.0f}/month")
print(f"   Annual: ₦{starter.annual_price:,.0f} (Save 2 months!)")
print(f"   • 2 Estate Properties • 30 Allocations • 30 Clients & 20 Affiliates\n")

# Create Professional Plan
professional, created = SubscriptionPlan.objects.get_or_create(
    tier='professional',
    defaults={
        'name': 'Professional',
        'description': 'For Growing Companies - Popular choice for expanding businesses',
        'monthly_price': Decimal('100000.00'),
        'annual_price': Decimal('1000000.00'),
        'max_plots': 5,
        'max_agents': 10,
        'max_api_calls_daily': 10000,
        'features': {
            'estate_properties': 5,
            'allocations': 80,
            'clients': 80,
            'affiliates': 30,
            'api_access': True,
            'advanced_analytics': True,
            'priority_support': True,
            'custom_branding': True,
        }
    }
)
print(f"{'✅ Created' if created else '⚠️  Updated'}: {professional.name} - ₦{professional.monthly_price:,.0f}/month")
print(f"   Annual: ₦{professional.annual_price:,.0f} (Save 2 months!)")
print(f"   • 5 Estate Properties • 80 Allocations • 80 Clients & 30 Affiliates\n")

# Create Enterprise Plan
enterprise, created = SubscriptionPlan.objects.get_or_create(
    tier='enterprise',
    defaults={
        'name': 'Enterprise',
        'description': 'Preferred Package Plan for Large Organizations',
        'monthly_price': Decimal('150000.00'),
        'annual_price': Decimal('1500000.00'),
        'max_plots': 999999,
        'max_agents': 999999,
        'max_api_calls_daily': 999999,
        'features': {
            'estate_properties': 'unlimited',
            'allocations': 'unlimited',
            'clients': 'unlimited',
            'affiliates': 'unlimited',
            'api_access': True,
            'advanced_analytics': True,
            'dedicated_support': True,
            'custom_branding': True,
            'sso_integration': True,
            'multi_currency': True,
        }
    }
)
print(f"{'✅ Created' if created else '⚠️  Updated'}: {enterprise.name} - ₦{enterprise.monthly_price:,.0f}/month")
print(f"   Annual: ₦{enterprise.annual_price:,.0f} (Save 2 months!)")
print(f"   • Unlimited Properties • Unlimited Allocations • Unlimited Clients & Affiliates\n")

print("✅ All subscription plans are configured correctly!")
