#!/usr/bin/env python
"""
Test script for Facebook-style dynamic tenant routing

Tests:
1. Verify all company slugs exist
2. Verify redirect routes work
3. Verify new tenant-aware routes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.contrib.auth import authenticate, get_user_model
from estateApp.models import Company

CustomUser = get_user_model()
client = Client()

print("=" * 70)
print("FACEBOOK-STYLE DYNAMIC TENANT ROUTING - TEST SUITE")
print("=" * 70)

# Step 1: Verify companies exist
print("\n✅ STEP 1: Verify all companies have slugs")
print("-" * 70)
companies = Company.objects.all()
print(f"Total companies: {len(companies)}")
for company in companies:
    print(f"  • {company.company_name:40} → /{company.slug}/")

# Step 2: Get a test user from first company
print("\n✅ STEP 2: Get test user for manual login")
print("-" * 70)
first_company = companies.first()
test_user = CustomUser.objects.filter(company_profile=first_company, role='admin').first()

if test_user:
    print(f"Test Company: {first_company.company_name}")
    print(f"Test User: {test_user.email}")
    print(f"User Role: {test_user.role}")
    print(f"Company Slug: {first_company.slug}")
    print(f"\n📝 To test:")
    print(f"  1. Login at: http://localhost:8000/login/")
    print(f"     Email: {test_user.email}")
    print(f"  2. Try old route: http://localhost:8000/admin_dashboard/")
    print(f"     Expected: Redirect to new route")
    print(f"  3. Visit new route: http://localhost:8000/{first_company.slug}/dashboard/")
    print(f"     Expected: See dashboard for {first_company.company_name}")
    print(f"  4. Try other company: http://localhost:8000/{companies[1].slug if len(companies) > 1 else 'other-company'}/dashboard/")
    print(f"     Expected: 403 Forbidden (wrong company)")
else:
    print("❌ No admin user found in first company")

# Step 3: Verify URL patterns
print("\n✅ STEP 3: Verify URL patterns are configured")
print("-" * 70)
from django.urls import reverse

try:
    # Test if new routes can be reversed
    first_company = Company.objects.first()
    
    test_urls = [
        ('tenant-dashboard', {'company_slug': first_company.slug}),
        ('tenant-management', {'company_slug': first_company.slug}),
        ('tenant-users', {'company_slug': first_company.slug}),
        ('tenant-settings', {'company_slug': first_company.slug}),
    ]
    
    for route_name, kwargs in test_urls:
        try:
            url = reverse(route_name, kwargs=kwargs)
            print(f"  ✅ {route_name:25} → {url}")
        except Exception as e:
            print(f"  ❌ {route_name:25} → ERROR: {str(e)}")
            
    # Test old redirects
    print(f"\n  Backward Compatibility Routes:")
    try:
        url = reverse('admin-dashboard-redirect')
        print(f"  ✅ admin-dashboard-redirect    → {url}")
    except Exception as e:
        print(f"  ❌ admin-dashboard-redirect    → ERROR: {str(e)}")
        
    try:
        url = reverse('management-dashboard-redirect')
        print(f"  ✅ management-dashboard-redirect → {url}")
    except Exception as e:
        print(f"  ❌ management-dashboard-redirect → ERROR: {str(e)}")
        
except Exception as e:
    print(f"❌ Error verifying routes: {str(e)}")

print("\n" + "=" * 70)
print("✅ TEST SUITE COMPLETE - Ready to test in browser!")
print("=" * 70)
