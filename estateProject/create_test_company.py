#!/usr/bin/env python
"""Create test company to verify system"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, SubscriptionPlan
from datetime import datetime, timedelta

# Get starter plan
starter_plan = SubscriptionPlan.objects.get(tier='starter')

# Create test company
company, created = Company.objects.get_or_create(
    company_name='Test Real Estate Company',
    defaults={
        'registration_number': 'RC123456',
        'registration_date': datetime.now().date(),
        'location': 'Lagos, Nigeria',
        'ceo_name': 'John Doe',
        'ceo_dob': datetime(1980, 1, 1).date(),
        'email': 'test@company.com',
        'phone': '08012345678',
        'is_active': True,
        # Subscription fields
        'subscription_tier': 'starter',
        'subscription_status': 'trial',
        'subscription_started_at': datetime.now(),
        'trial_ends_at': datetime.now() + timedelta(days=14),
        'max_plots': starter_plan.max_plots,
        'max_agents': starter_plan.max_agents,
        'max_api_calls_daily': starter_plan.max_api_calls_daily,
        'current_plots_count': 0,
        'current_agents_count': 0,
        'api_calls_today': 0,
    }
)

if created:
    print(f"✅ Created test company: {company.company_name}")
    print(f"   Subscription: {company.subscription_tier} ({company.subscription_status})")
    print(f"   Trial ends: {company.trial_ends_at.strftime('%Y-%m-%d')}")
    print(f"   Limits: {company.max_plots} plots, {company.max_agents} agents")
else:
    print(f"⚠️  Company already exists: {company.company_name}")

print(f"\n📊 Total companies: {Company.objects.count()}")
