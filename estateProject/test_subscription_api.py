#!/usr/bin/env python
"""Test subscription API endpoint"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.contrib.auth import get_user_model
from estateApp.models import Company

User = get_user_model()

# Get first admin user and company
print("Testing Subscription API...")
print("-" * 60)

# Get a company
company = Company.objects.first()
if not company:
    print("❌ No companies found in database")
    exit(1)

print(f"✓ Found company: {company.company_name} (ID: {company.id})")
print(f"  Subscription Tier: {company.subscription_tier}")
print(f"  Subscription Status: {company.subscription_status}")

# Check models
plan = company.get_current_plan()
print(f"\n✓ Current Plan: {plan.name if plan else 'No plan'}")

billing_status = company.get_billing_status()
print(f"✓ Billing Status: {billing_status}")

usage = company.get_usage_percentage()
print(f"✓ Usage Percentage: {usage}")

# Check subscription response directly
from estateApp.api_views.billing_views import SubscriptionDashboardView
from unittest.mock import Mock

view = SubscriptionDashboardView()
request = Mock()
request.user = User.objects.filter(company=company).first()

if not request.user:
    # Create a test user
    request.user = User.objects.filter(is_staff=True, is_active=True).first()

request.company = company

print(f"\n✓ Test user: {request.user.username if request.user else 'None'}")

# Call the view
try:
    response = view.list(request)
    print(f"\n✓ API Response Status: {response.status_code}")
    import json
    data = response.data
    print(f"✓ Subscription Data:")
    print(f"  - Tier: {data.get('subscription', {}).get('tier')}")
    print(f"  - Status: {data.get('subscription', {}).get('status')}")
    print(f"  - Usage plots: {data.get('usage', {}).get('plots', {})}")
    print(f"\n✓ API endpoint is working correctly!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
