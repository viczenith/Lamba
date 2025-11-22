#!/usr/bin/env python
"""Test subscription API with string company ID (like middleware sets it)"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from estateApp.models import Company
from estateApp.api_views.billing_views import SubscriptionDashboardView

User = get_user_model()

print("=" * 70)
print("TEST: Subscription API with String Company ID")
print("=" * 70)

# Setup
company = Company.objects.first()
user = User.objects.filter(is_staff=True, is_active=True).first()

if not company or not user:
    print("❌ Missing company or user")
    exit(1)

print(f"✓ Company: {company.company_name} (ID: {company.id})")
print(f"✓ User: {user.username}")

# Create request with STRING company ID (like middleware does)
factory = APIRequestFactory()
request = factory.get('/api/subscription/')
request.user = user
request.company = str(company.id)  # ← SET AS STRING, not object

print(f"\n✓ Request company type: {type(request.company)} = '{request.company}'")

# Call view
view = SubscriptionDashboardView()
view.format_kwarg = None

print("\nCalling API view with string company ID...")
try:
    response = view.list(request)
    print(f"✓ Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.data
        print(f"✓ Subscription: {data.get('subscription', {}).get('tier')}")
        print(f"✓ Status: {data.get('subscription', {}).get('status')}")
        print(f"✓ Days remaining: {data.get('days_remaining')}")
        print("\n✅ SUCCESS! String company ID is handled correctly!")
    else:
        print(f"❌ Error response: {response.data}")
        
except Exception as e:
    print(f"❌ API Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
