#!/usr/bin/env python
"""
Test script to verify both logout routes work correctly:
1. /logout/ - redirects to /login/ (for company admin, client, marketer)
2. /tenant-admin/logout/ - redirects to /tenant-admin/login/ (for system admin)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from estateApp.models import CustomUser

print("\n" + "="*80)
print("Testing Separate Logout Routes")
print("="*80 + "\n")

# Create test client
client = Client()

# Get users
regular_user = CustomUser.objects.filter(role__in=['admin', 'client', 'marketer'], admin_level__isnull=True).first() or \
               CustomUser.objects.filter(role='admin', admin_level='company').first()

system_admin = CustomUser.objects.filter(role='admin', admin_level='system').first()

print("TEST SETUP")
print("-" * 80)
print(f"Regular user: {regular_user.email if regular_user else 'NOT FOUND'}")
print(f"System admin: {system_admin.email if system_admin else 'NOT FOUND'}\n")

# Test 1: Regular user logout
print("TEST 1: Regular User Logout")
print("-" * 80)

if regular_user:
    # Set password
    test_password = 'admin123'
    regular_user.set_password(test_password)
    regular_user.save()
    
    # Login
    client.post(reverse('login'), {
        'email': regular_user.email,
        'password': test_password
    })
    
    # Logout
    logout_response = client.post(reverse('logout'), follow=False)
    print(f"Status: {logout_response.status_code}")
    print(f"Redirect to: {logout_response.get('Location', 'N/A')}")
    
    if logout_response.status_code == 302:
        location = logout_response.get('Location', '')
        if '/login/' in location:
            print("✓ Regular user logout redirects to /login/\n")
        else:
            print(f"✗ Wrong redirect: {location}\n")
    else:
        print(f"✗ Wrong status code: {logout_response.status_code}\n")
else:
    print("✗ No regular user found\n")

# Test 2: System admin logout
print("TEST 2: System Admin Logout")
print("-" * 80)

if system_admin:
    # Set password
    test_password = 'admin123'
    system_admin.set_password(test_password)
    system_admin.save()
    
    # Login (tenant-admin-login uses email by default in CustomAuthenticationForm)
    client.post(reverse('tenant-admin-login'), {
        'email': system_admin.email,
        'password': test_password
    })
    
    # Logout
    logout_response = client.post(reverse('tenant-admin-logout'), follow=False)
    print(f"Status: {logout_response.status_code}")
    print(f"Redirect to: {logout_response.get('Location', 'N/A')}")
    
    if logout_response.status_code == 302:
        location = logout_response.get('Location', '')
        if '/tenant-admin/login/' in location:
            print("✓ System admin logout redirects to /tenant-admin/login/\n")
        else:
            print(f"✗ Wrong redirect: {location}\n")
    else:
        print(f"✗ Wrong status code: {logout_response.status_code}\n")
else:
    print("✗ No system admin user found\n")

print("=" * 80)
print("Test Complete")
print("=" * 80 + "\n")
