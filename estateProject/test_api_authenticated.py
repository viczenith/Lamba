#!/usr/bin/env python
"""
Test the dynamic marketer client count API with authenticated session
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from estateApp.views import api_marketer_client_counts
from estateApp.models import Company, CustomUser
import json

print("\n" + "="*100)
print("AUTHENTICATED API TEST: Dynamic Marketer Client Counts")
print("="*100 + "\n")

# Setup
company = Company.objects.filter(company_name='Lamba Real Homes').first()
admin = CustomUser.objects.filter(company_profile=company, role='admin').first()

if not company or not admin:
    print("❌ Setup failed")
    sys.exit(1)

print(f"✅ Company: {company.company_name}")
print(f"✅ Admin: {admin.full_name}\n")

# Create a mock authenticated request
factory = RequestFactory()
request = factory.get('/api/marketer-client-counts/')

# Add session middleware
middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session.save()

# Add auth middleware
middleware = AuthenticationMiddleware(lambda x: None)
middleware.process_request(request)

# Set user
request.user = admin
request.company = company

# Call the API view
print(f"Calling API endpoint with authenticated admin user...\n")
response = api_marketer_client_counts(request)

# Parse response
data = json.loads(response.content.decode('utf-8'))

print(f"Response Status: {response.status_code}")
print(f"Response JSON:\n")
print(json.dumps(data, indent=2, default=str))

# Verify response
print(f"\n✅ API Response Validation:")

if data.get('success'):
    print(f"   ✅ Success flag: True")
else:
    print(f"   ❌ Success flag: False")
    sys.exit(1)

marketers = data.get('marketers', [])
print(f"   ✅ Total marketers: {len(marketers)}")

# Check each marketer has required fields
all_valid = True
for m in marketers:
    required_fields = ['id', 'full_name', 'email', 'client_count']
    missing = [f for f in required_fields if f not in m]
    if missing:
        print(f"   ❌ Marketer {m.get('id')} missing fields: {missing}")
        all_valid = False
    else:
        print(f"   ✅ Marketer: {m['full_name']} - {m['client_count']} clients")

if 'timestamp' in data:
    print(f"   ✅ Timestamp provided: {data['timestamp']}")
else:
    print(f"   ⚠️  No timestamp in response")

if all_valid and len(marketers) == 4:
    print(f"\n" + "="*100)
    print("✅ DYNAMIC MARKETER CLIENT COUNT API WORKING CORRECTLY")
    print("="*100 + "\n")
    sys.exit(0)
else:
    print(f"\n❌ API validation failed")
    sys.exit(1)
