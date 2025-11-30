#!/usr/bin/env python
"""
Debug: Check if API is returning updated client count for marketer
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from estateApp.models import Company, CustomUser, ClientUser, MarketerUser
from estateApp.views import get_all_marketers_for_company
import json

company = Company.objects.filter(company_name='Lamba Real Homes').first()

print("\n" + "="*100)
print("DEBUG: Checking client count for Victor Marketer")
print("="*100 + "\n")

# Find Victor Marketer (ID 15)
victor_marketer = CustomUser.objects.filter(id=15, role='marketer').first()

if not victor_marketer:
    print("❌ Victor Marketer not found")
    sys.exit(1)

print(f"Marketer: {victor_marketer.full_name} (ID: {victor_marketer.id})")
print(f"Email: {victor_marketer.email}")
print(f"Company: {victor_marketer.company_profile}\n")

# Method 1: Direct query on MarketerUser
print("[Method 1] Direct count from MarketerUser.clients:")
if hasattr(victor_marketer, 'marketeruser'):
    mu = victor_marketer.marketeruser
    direct_count = mu.clients.filter(company_profile=company).count()
    print(f"  Count: {direct_count}")
    print(f"  Clients: {list(mu.clients.filter(company_profile=company).values_list('full_name', flat=True))}")
else:
    print(f"  ❌ Not a MarketerUser instance")
    # Try to get via reverse relation
    try:
        mu = MarketerUser.objects.get(id=victor_marketer.id)
        direct_count = mu.clients.filter(company_profile=company).count()
        print(f"  Count (via MarketerUser.objects): {direct_count}")
        print(f"  Clients: {list(mu.clients.filter(company_profile=company).values_list('full_name', flat=True))}")
    except:
        print("  ❌ Could not get MarketerUser")

# Method 2: Query the API helper function
print("\n[Method 2] Via get_all_marketers_for_company helper:")
marketers = get_all_marketers_for_company(company)
for m in marketers:
    if m.id == 15:
        print(f"  Marketer: {m.full_name}")
        print(f"  Client count: {m.client_count}")
        break
else:
    print("  ❌ Marketer not found in helper result")

# Method 3: Check ClientUser directly
print("\n[Method 3] Direct query on ClientUser table:")
clients_for_victor = ClientUser.objects.filter(
    assigned_marketer__id=15,
    company_profile=company
)
print(f"  Count: {clients_for_victor.count()}")
for client in clients_for_victor:
    print(f"    - {client.full_name} ({client.email})")

# Method 4: Check via ClientMarketerAssignment
print("\n[Method 4] Via ClientMarketerAssignment:")
from estateApp.models import ClientMarketerAssignment
assignments = ClientMarketerAssignment.objects.filter(
    marketer__id=15,
    company=company
)
print(f"  Count: {assignments.count()}")
for a in assignments:
    print(f"    - {a.client.full_name}")

print("\n" + "="*100)
