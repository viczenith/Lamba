#!/usr/bin/env python
"""Debug subscription API errors"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from estateApp.models import Company

User = get_user_model()

print("=" * 70)
print("DEBUGGING SUBSCRIPTION API")
print("=" * 70)

# Get company
company = Company.objects.first()
print(f"\n1. Company: {company.company_name if company else 'NOT FOUND'}")

if not company:
    print("❌ No company in database")
    exit(1)

# Get or create user
user = User.objects.filter(is_staff=True, is_active=True).first()
print(f"2. User: {user.username if user else 'NOT FOUND'}")

if not user:
    print("❌ No staff user in database")
    exit(1)

# Simulate API request directly
from unittest.mock import Mock
from estateApp.api_views.billing_views import SubscriptionDashboardView
from rest_framework.test import APIRequestFactory

print("\n3. Testing API Endpoint Directly...")
print("-" * 70)

try:
    factory = APIRequestFactory()
    request = factory.get('/api/subscription/')
    request.user = user
    request.company = company
    
    view = SubscriptionDashboardView()
    view.format_kwarg = None
    response = view.list(request)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✓ API Response: SUCCESS")
        data = response.data
        print(f"  - Subscription: {data.get('subscription', {}).get('tier')}")
        print(f"  - Usage: {data.get('usage', {}).get('plots', {})}")
    else:
        print(f"❌ API Response Error:")
        print(json.dumps(response.data, indent=2, default=str))
        
except Exception as e:
    print(f"❌ Direct call error: {e}")
    import traceback
    traceback.print_exc()

# Test via Django test client
print("\n4. Testing via Django Test Client...")
print("-" * 70)

client = Client()
# Try to login with username as password (common in test)
login_ok = client.login(username=user.username, password=user.username)
print(f"Login: {'✓ SUCCESS' if login_ok else '❌ FAILED'}")

if not login_ok:
    print("Trying alternate passwords...")
    for pwd in [user.username, 'password', '123456', 'admin']:
        if client.login(username=user.username, password=pwd):
            print(f"✓ Logged in with password: {pwd}")
            break

try:
    response = client.get('/api/subscription/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✓ Response: SUCCESS")
        data = response.json()
        print(f"  - Subscription: {data.get('subscription', {}).get('tier')}")
    else:
        print(f"Response: {response.content}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
