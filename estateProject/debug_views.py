#!/usr/bin/env python
"""Debug views to see what's being returned"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import CustomUser, PlotSize, PlotNumber, Company
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*80)
print("DEBUGGING CLIENT/MARKETER/PLOT DATA")
print("="*80)

# Get Company A
company_a = Company.objects.filter(email='estate@gmail.com').first()
print(f"\nCompany A: {company_a.company_name} (ID: {company_a.id})")

# Get admin user
admin = User.objects.filter(email='estate@gmail.com').first()
if admin:
    print(f"Admin User: {admin.email}")
    print(f"  company_profile: {admin.company_profile}")
    print(f"  company_profile ID: {admin.company_profile.id if admin.company_profile else 'None'}")

# Test ClientUser query
from estateApp.models import ClientUser, MarketerUser

print("\n" + "-"*80)
print("TESTING CLIENT QUERY")
print("-"*80)

# Direct query
clients_direct = CustomUser.objects.filter(role='client', company_profile=company_a)
print(f"\nDirect CustomUser query: {clients_direct.count()} clients")

# ClientUser query
try:
    clients_via_clientuser = ClientUser.objects.filter(role='client', company_profile=company_a)
    print(f"ClientUser query: {clients_via_clientuser.count()} clients")
    for client in clients_via_clientuser[:3]:
        print(f"  - {client.email} ({client.full_name})")
except Exception as e:
    print(f"ClientUser query FAILED: {e}")

print("\n" + "-"*80)
print("TESTING MARKETER QUERY")
print("-"*80)

# Direct query
marketers_direct = CustomUser.objects.filter(role='marketer', company_profile=company_a)
print(f"\nDirect CustomUser query: {marketers_direct.count()} marketers")

# MarketerUser query
try:
    marketers_via_marketeruser = MarketerUser.objects.filter(role='marketer', company_profile=company_a)
    print(f"MarketerUser query: {marketers_via_marketeruser.count()} marketers")
    for marketer in marketers_via_marketeruser[:3]:
        print(f"  - {marketer.email} ({marketer.full_name})")
except Exception as e:
    print(f"MarketerUser query FAILED: {e}")

print("\n" + "-"*80)
print("TESTING PLOT SIZE QUERY")
print("-"*80)

plot_sizes = PlotSize.objects.filter(company=company_a)
print(f"\nPlotSize query: {plot_sizes.count()} plot sizes")
for ps in plot_sizes:
    print(f"  - {ps.size} ({ps.size_unit})")

print("\n" + "-"*80)
print("TESTING PLOT NUMBER QUERY")
print("-"*80)

plot_numbers = PlotNumber.objects.filter(company=company_a)
print(f"\nPlotNumber query: {plot_numbers.count()} plot numbers")
for pn in plot_numbers[:5]:
    print(f"  - {pn.number}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Clients (CustomUser): {clients_direct.count()}")
print(f"Marketers (CustomUser): {marketers_direct.count()}")
print(f"Plot Sizes: {plot_sizes.count()}")
print(f"Plot Numbers: {plot_numbers.count()}")
