#!/usr/bin/env python
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, Company
from django.utils import timezone

print("=" * 70)
print("FIXING DATABASE FOR SINGLE-COMPANY ARCHITECTURE")
print("=" * 70)

# Step 1: Create the main company (Lamba Real Estate)
print("\n[STEP 1] Creating main company...")

company, created = Company.objects.get_or_create(
    registration_number='LAMBA-001',
    defaults={
        'company_name': 'Lamba Real Estate',
        'registration_date': timezone.now().date(),
        'location': 'Nigeria',
        'ceo_name': 'Victor Godwin',
        'ceo_dob': '1990-01-01',
        'email': 'estate@gmail.com',
        'phone': '+2349000000000',
        'subscription_tier': 'enterprise',
        'subscription_status': 'active',
        'is_active': True,
    }
)

if created:
    print(f"✅ Created company: {company.company_name} (ID={company.id})")
else:
    print(f"✓ Company already exists: {company.company_name} (ID={company.id})")

# Step 2: Update superuser (estate@gmail.com)
print("\n[STEP 2] Updating main superuser...")
try:
    estate_user = CustomUser.objects.get(email='estate@gmail.com')
    estate_user.role = 'admin'
    estate_user.admin_level = 'company'
    estate_user.company_profile = company
    estate_user.company = company.company_name
    estate_user.is_staff = True
    estate_user.is_superuser = True
    estate_user.save()
    print(f"✅ Updated: {estate_user.email}")
    print(f"   - Role: {estate_user.role}")
    print(f"   - Admin Level: {estate_user.admin_level}")
    print(f"   - Company: {estate_user.company}")
except CustomUser.DoesNotExist:
    print("❌ estate@gmail.com not found!")

# Step 3: Update other admin users
print("\n[STEP 3] Updating other admin users...")
from django.db.models import Q
other_admins = CustomUser.objects.filter(role='admin').exclude(Q(email='estate@gmail.com') | Q(email='admin@system.com'))
updated_count = 0
for admin in other_admins:
    if admin.company_profile is None:
        admin.company_profile = company
        admin.company = company.company_name
        admin.admin_level = 'company'
        admin.save()
        updated_count += 1
        print(f"✅ Updated: {admin.email}")

if updated_count == 0:
    print("✓ No other admin users to update")

# Step 4: Link all clients to company
print("\n[STEP 4] Linking clients to company...")
clients = CustomUser.objects.filter(role='client')
updated = 0
for client in clients:
    if client.company_profile is None:
        client.company_profile = company
        client.company = company.company_name
        client.save()
        updated += 1

print(f"✅ Updated {updated} clients with company_profile")

# Step 5: Link all marketers to company
print("\n[STEP 5] Linking marketers to company...")
marketers = CustomUser.objects.filter(role='marketer')
updated = 0
for marketer in marketers:
    if marketer.company_profile is None:
        marketer.company_profile = company
        marketer.company = company.company_name
        marketer.save()
        updated += 1

print(f"✅ Updated {updated} marketers with company_profile")

# Step 6: Verify
print("\n[STEP 6] VERIFICATION")
print("-" * 70)

company_users = CustomUser.objects.filter(company_profile=company)
print(f"\nUsers linked to '{company.company_name}':")
print(f"  • Total: {company_users.count()}")
print(f"  • Admins: {company_users.filter(role='admin').count()}")
print(f"  • Clients: {company_users.filter(role='client').count()}")
print(f"  • Marketers: {company_users.filter(role='marketer').count()}")

print("\n" + "=" * 70)
print("✅ DATABASE MIGRATION COMPLETE")
print("=" * 70)
