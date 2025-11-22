#!/usr/bin/env python
"""
Test script to verify logout redirects to login page correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from estateApp.models import CustomUser

print("\n" + "="*80)
print("Testing Logout Flow - Tenant Isolation Fix")
print("="*80 + "\n")

# Create test client
client = Client()

# Get an existing admin user or create one
test_user = CustomUser.objects.filter(role='admin').first()
if not test_user:
    test_user = CustomUser.objects.first()

if not test_user:
    print("✗ No users found in database. Cannot run test.")
    exit(1)

# Store original password for testing
test_email = test_user.email
test_password = 'admin123'
test_user.set_password(test_password)
test_user.save()

print(f"✓ Using existing user: {test_email}")
print(f"✓ User company: {test_user.company_profile if hasattr(test_user, 'company_profile') else 'N/A'}\n")

# Test 1: Login
print("TEST 1: Login")
print("-" * 40)
login_response = client.post(reverse('login'), {
    'email': test_email,
    'password': test_password
}, follow=False)

print(f"Status: {login_response.status_code}")
if login_response.status_code in [200, 302]:
    print("✓ Login successful\n")
else:
    print(f"✗ Login failed: {login_response.status_code}\n")

# Test 2: Check session is set
print("TEST 2: Check Authenticated Session")
print("-" * 40)
home_response = client.get(reverse('home'), follow=False)
print(f"Home page status: {home_response.status_code}")
if home_response.status_code == 200:
    print("✓ User is authenticated\n")
else:
    print(f"✗ User not authenticated\n")

# Test 3: Logout
print("TEST 3: Logout")
print("-" * 40)
logout_response = client.post(reverse('logout'), follow=False)
print(f"Logout response status: {logout_response.status_code}")
print(f"Logout response location: {logout_response.get('Location', 'N/A')}")

# Check if response is a redirect
if logout_response.status_code in [301, 302]:
    location = logout_response.get('Location', '')
    if 'login' in location.lower():
        print("✓ Logout redirects to login page correctly")
    else:
        print(f"✗ Logout redirects to wrong location: {location}")
else:
    print(f"Response body: {logout_response.content.decode()}")

# Test 4: Follow redirect and check landing page
print("\nTEST 4: Follow Redirect")
print("-" * 40)
redirected_response = client.post(reverse('logout'), follow=True)
print(f"Final status after redirect: {redirected_response.status_code}")

# Check if we're on login page
if 'login' in str(redirected_response.content).lower():
    print("✓ Successfully redirected to login page")
elif 'unauthorized' in str(redirected_response.content).lower():
    print("✗ Got unauthorized error (tenant isolation issue)")
    print(f"Response: {redirected_response.content.decode()[:500]}")
else:
    print("? Unclear response after redirect")

print("\n" + "="*80)
print("Logout Fix Verification Complete")
print("="*80 + "\n")
