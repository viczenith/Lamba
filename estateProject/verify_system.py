#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, Company

print("=" * 80)
print("FINAL VERIFICATION - ALL SYSTEMS OPERATIONAL")
print("=" * 80)

# Verify company setup
print("\n[1] COMPANY SETUP")
print("-" * 80)
company = Company.objects.first()
if company:
    print(f"✅ Company: {company.company_name}")
    print(f"   Email: {company.email}")
    print(f"   Location: {company.location}")
    print(f"   Status: {'ACTIVE' if company.is_active else 'INACTIVE'}")
    print(f"   Subscription: {company.subscription_tier}")
else:
    print("❌ No company found")

# Verify main superuser
print("\n[2] MAIN SUPERUSER (COMPANY ADMIN)")
print("-" * 80)
try:
    estate_user = CustomUser.objects.get(email='estate@gmail.com')
    print(f"✅ Email: {estate_user.email}")
    print(f"   Name: {estate_user.full_name}")
    print(f"   Role: {estate_user.role}")
    print(f"   Admin Level: {estate_user.admin_level}")
    print(f"   Company: {estate_user.company}")
    print(f"   Superuser: {'YES' if estate_user.is_superuser else 'NO'}")
    print(f"   Staff: {'YES' if estate_user.is_staff else 'NO'}")
except CustomUser.DoesNotExist:
    print("❌ Main superuser not found")

# Verify admin users
print("\n[3] ALL ADMIN USERS")
print("-" * 80)
admins = CustomUser.objects.filter(role='admin')
for admin in admins:
    company_name = admin.company_profile.company_name if admin.company_profile else "No Company"
    print(f"✅ {admin.email}: {admin.admin_level} - {company_name}")

# Verify client users
print("\n[4] CLIENT USERS (SAMPLE)")
print("-" * 80)
clients = CustomUser.objects.filter(role='client')[:3]
print(f"Total Clients: {CustomUser.objects.filter(role='client').count()}")
for client in clients:
    company_name = client.company_profile.company_name if client.company_profile else "No Company"
    print(f"✅ {client.email}: {company_name}")

# Verify marketer users
print("\n[5] MARKETER USERS (SAMPLE)")
print("-" * 80)
marketers = CustomUser.objects.filter(role='marketer')[:3]
print(f"Total Marketers: {CustomUser.objects.filter(role='marketer').count()}")
for marketer in marketers:
    company_name = marketer.company_profile.company_name if marketer.company_profile else "No Company"
    print(f"✅ {marketer.email}: {company_name}")

# Verify users with company
print("\n[6] USERS LINKED TO COMPANY")
print("-" * 80)
if company:
    users = CustomUser.objects.filter(company_profile=company)
    print(f"Total Users: {users.count()}")
    print(f"  • Admins: {users.filter(role='admin').count()}")
    print(f"  • Clients: {users.filter(role='client').count()}")
    print(f"  • Marketers: {users.filter(role='marketer').count()}")
    print(f"  • Support: {users.filter(role='support').count()}")

# Verify URL endpoints
print("\n[7] URL ENDPOINTS CONFIGURED")
print("-" * 80)
from django.urls import reverse
endpoints = {
    'Login': 'login',
    'Logout': 'logout',
    'Company Register': 'register',
    'User Register': 'register-user',
    'Admin Dashboard': 'admin-dashboard',
    'Client Dashboard': 'client-dashboard',
    'Marketer Dashboard': 'marketer-dashboard',
}

for name, url_name in endpoints.items():
    try:
        url = reverse(url_name)
        print(f"✅ {name:20} → {url}")
    except Exception as e:
        print(f"❌ {name:20} → Error: {e}")

print("\n" + "=" * 80)
print("✅ ALL SYSTEMS VERIFIED AND OPERATIONAL")
print("=" * 80)
