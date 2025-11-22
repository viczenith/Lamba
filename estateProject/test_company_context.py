#!/usr/bin/env python
"""
Test company context extraction during request processing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from estateApp.models import Company
from estateApp.views import get_request_company

User = get_user_model()

# Get Company A and user
company_a = Company.objects.filter(email='estate@gmail.com').first()
admin_user = User.objects.filter(email='estate@gmail.com').first()

if not company_a:
    print("❌ Company A not found!")
    exit(1)

if not admin_user:
    print("❌ Admin user not found!")
    exit(1)

print(f"Company A: {company_a.company_name} (ID: {company_a.id})")
print(f"Admin User: {admin_user.email}")
print(f"  company_profile: {admin_user.company_profile}")
print(f"  company_profile ID: {admin_user.company_profile.id if admin_user.company_profile else None}")
print()

# Create a fake request
factory = RequestFactory()
request = factory.get('/client')
request.user = admin_user

print("=== TEST 1: Request without request.company attribute ===")
company = get_request_company(request)
print(f"Result: {company}")
print(f"Result ID: {company.id if company else None}")
print()

print("=== TEST 2: Request with request.company set ===")
request.company = company_a
company = get_request_company(request)
print(f"Result: {company}")
print(f"Result ID: {company.id if company else None}")
print()

print("=== TEST 3: Request with request.company as string ID ===")
request.company = str(company_a.id)
company = get_request_company(request)
print(f"Result: {company}")
print(f"Result ID: {company.id if company else None}")
print()

# Test the actual view queries
print("=== TEST 4: Simulate client view query ===")
from estateApp.models import ClientUser
request.company = company_a
company = get_request_company(request)
if company:
    clients = ClientUser.objects.filter(role='client', company_profile=company)
    print(f"Clients found: {clients.count()}")
    for client in clients[:3]:
        print(f"  - {client.email} ({client.full_name})")
else:
    print("❌ company is None - no clients will be returned")
print()

print("=== TEST 5: Simulate marketer_list view query ===")
from estateApp.models import MarketerUser
if company:
    marketers = MarketerUser.objects.filter(company_profile=company)
    print(f"Marketers found: {marketers.count()}")
    for marketer in marketers[:3]:
        print(f"  - {marketer.email} ({marketer.full_name})")
else:
    print("❌ company is None - no marketers will be returned")
print()

print("=== SUMMARY ===")
print(f"User has company_profile: {admin_user.company_profile is not None}")
print(f"get_request_company works when request.company set: {request.company is not None}")
print(f"get_request_company works without request.company: {admin_user.company_profile is not None}")
print("\n⚠️ If middleware doesn't set request.company, get_request_company MUST rely on user.company_profile")
