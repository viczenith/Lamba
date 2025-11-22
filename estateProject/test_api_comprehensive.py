#!/usr/bin/env python
"""Comprehensive subscription API test"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from estateApp.models import Company
from estateApp.api_views.billing_views import SubscriptionDashboardView

User = get_user_model()

print("=" * 70)
print("COMPREHENSIVE SUBSCRIPTION API TEST")
print("=" * 70)

# Setup
company = Company.objects.first()
user = User.objects.filter(is_staff=True, is_active=True).first()

if not company or not user:
    print("❌ Missing company or user")
    exit(1)

print(f"✓ Company: {company.company_name}")
print(f"✓ User: {user.username}")

# Create request
factory = APIRequestFactory()
request = factory.get('/api/subscription/')
request.user = user
request.company = company

# Call view
view = SubscriptionDashboardView()
view.format_kwarg = None

print("\nCalling API view...")
try:
    response = view.list(request)
    print(f"✓ Response Status: {response.status_code}")
    
    if response.status_code == 200:
        # Try to JSON serialize the response
        print("\nAttempting JSON serialization...")
        try:
            json_data = json.dumps(response.data, default=str, indent=2)
            print("✓ JSON Serialization: SUCCESS")
            print(f"\nResponse Data Sample (first 1000 chars):")
            print(json_data[:1000])
            print("...")
        except Exception as e:
            print(f"❌ JSON Error: {e}")
            print(f"\nResponse data structure:")
            print(f"  Keys: {response.data.keys()}")
            
            # Check each section
            for key in response.data:
                print(f"\n  [{key}]:")
                try:
                    json.dumps(response.data[key], default=str)
                    print(f"    ✓ Serializable")
                except Exception as err:
                    print(f"    ❌ Error: {err}")
                    print(f"    Value: {response.data[key]}")
    else:
        print(f"❌ Error response: {response.data}")
        
except Exception as e:
    print(f"❌ API Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
