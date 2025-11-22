#!/usr/bin/env python
import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company
from django.utils import timezone
import uuid

print("=" * 80)
print("POPULATING LAMBA REAL ESTATE COMPANY WITH COMPLETE DETAILS")
print("=" * 80)

# Get the company
company = Company.objects.get(company_name='Lamba Real Estate')

print("\n[STEP 1] Current Company Details")
print("-" * 80)
print(f"Company Name: {company.company_name}")
print(f"Email: {company.email}")
print(f"Phone: {company.phone}")
print(f"Location: {company.location}")
print(f"CEO: {company.ceo_name}")
print(f"Registration #: {company.registration_number}")

# Update with full details (as if from the registration form)
print("\n[STEP 2] Updating Company with Full Details")
print("-" * 80)

company.company_name = 'Lamba Real Estate'
company.registration_number = 'LAMBA-REALESTATE-001'
company.registration_date = datetime(2023, 1, 15).date()
company.location = 'Lagos, Nigeria'
company.ceo_name = 'Victor Godwin Akor'
company.ceo_dob = datetime(1990, 5, 20).date()
company.email = 'estate@gmail.com'
company.phone = '+2349031234567'
company.billing_email = 'billing@lamba.com'

# SaaS Configuration
company.subscription_tier = 'enterprise'
company.subscription_status = 'active'
company.trial_ends_at = timezone.now() + timedelta(days=14)
company.subscription_ends_at = None  # Active indefinitely

# Set limits based on Enterprise tier
company.max_plots = 999999  # Unlimited
company.max_agents = 999999  # Unlimited
company.max_api_calls_daily = 100000  # Very high

# Customization
company.theme_color = '#667eea'
company.custom_domain = 'lamba.estate'

# Generate API Key
company.api_key = f'lamba_live_{uuid.uuid4().hex[:32]}'

# Status
company.is_active = True

# Save
company.save()

print(f"✅ Company Name: {company.company_name}")
print(f"✅ Registration #: {company.registration_number}")
print(f"✅ Registration Date: {company.registration_date}")
print(f"✅ Location: {company.location}")
print(f"✅ CEO: {company.ceo_name}")
print(f"✅ CEO DOB: {company.ceo_dob}")
print(f"✅ Email: {company.email}")
print(f"✅ Phone: {company.phone}")
print(f"✅ Billing Email: {company.billing_email}")

print("\n[STEP 3] SaaS Configuration")
print("-" * 80)
print(f"✅ Subscription Tier: {company.subscription_tier.upper()}")
print(f"✅ Subscription Status: {company.subscription_status.upper()}")
print(f"✅ Trial Ends At: {company.trial_ends_at}")
print(f"✅ Max Plots: UNLIMITED ({company.max_plots})")
print(f"✅ Max Agents: UNLIMITED ({company.max_agents})")
print(f"✅ Max API Calls/Day: {company.max_api_calls_daily:,}")

print("\n[STEP 4] Customization & Security")
print("-" * 80)
print(f"✅ Custom Domain: {company.custom_domain}")
print(f"✅ Theme Color: {company.theme_color}")
print(f"✅ API Key: {company.api_key[:20]}...{company.api_key[-10:]}")

print("\n[STEP 5] Associated Users")
print("-" * 80)
users = company.users.all()
print(f"Total Users: {users.count()}")
print(f"  • Admins: {users.filter(role='admin').count()}")
print(f"  • Clients: {users.filter(role='client').count()}")
print(f"  • Marketers: {users.filter(role='marketer').count()}")

print("\n[STEP 6] Company Admin Details")
print("-" * 80)
admins = users.filter(role='admin')
for admin in admins:
    print(f"✅ {admin.email}")
    print(f"   - Name: {admin.full_name}")
    print(f"   - Admin Level: {admin.admin_level}")
    print(f"   - Superuser: {'YES' if admin.is_superuser else 'NO'}")
    print()

print("=" * 80)
print("✅ LAMBA REAL ESTATE COMPANY NOW FULLY CONFIGURED AS TENANT")
print("=" * 80)

print("\n📋 COMPANY SUMMARY:")
print("-" * 80)
print(f"Name:            {company.company_name}")
print(f"Type:            Real Estate Management")
print(f"Registration:    {company.registration_number}")
print(f"Location:        {company.location}")
print(f"Status:          {'🟢 ACTIVE' if company.is_active else '🔴 INACTIVE'}")
print(f"Tier:            {company.subscription_tier.upper()} (Unlimited Everything)")
print(f"Users:           {users.count()} (3 Admins + 11 Clients + 5 Marketers)")
print(f"Contact:         {company.email} | {company.phone}")
print(f"Billing:         {company.billing_email}")
