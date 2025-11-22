#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, Company

print("=" * 70)
print("DATABASE INVESTIGATION")
print("=" * 70)

print("\n--- SUPERUSERS/STAFF ---")
superusers = CustomUser.objects.filter(is_superuser=True)
print(f"Superusers: {superusers.count()}")
for su in superusers:
    print(f"  • {su.email}: role={su.role}, admin_level={su.admin_level}")
    print(f"    company_profile={su.company_profile_id}, company={su.company}")
    print()

print("\n--- ALL ADMIN USERS ---")
admins = CustomUser.objects.filter(role='admin')
print(f"Admin users: {admins.count()}")
for admin in admins:
    print(f"  • {admin.email}: admin_level={admin.admin_level}")
    print(f"    company_profile={admin.company_profile_id}, company={admin.company}")
    print()

print("\n--- COMPANIES IN DATABASE ---")
companies = Company.objects.all()
print(f"Total companies: {companies.count()}")
for company in companies:
    print(f"  • {company.company_name} (ID={company.id})")
    print(f"    Email: {company.email}, Location: {company.location}")
    print(f"    CEO: {company.ceo_name}, Active: {company.is_active}")
    print()

print("\n--- CLIENTS WITHOUT COMPANY ---")
clients_no_company = CustomUser.objects.filter(role='client', company_profile__isnull=True)
print(f"Clients without company: {clients_no_company.count()}")
for client in clients_no_company[:5]:
    print(f"  • {client.email}: company={client.company}")

print("\n--- MARKETERS WITHOUT COMPANY ---")
marketers_no_company = CustomUser.objects.filter(role='marketer', company_profile__isnull=True)
print(f"Marketers without company: {marketers_no_company.count()}")
for marketer in marketers_no_company[:5]:
    print(f"  • {marketer.email}: company={marketer.company}")

print("\n✅ Investigation Complete")
