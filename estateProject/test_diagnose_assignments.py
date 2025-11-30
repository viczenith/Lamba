#!/usr/bin/env python
"""
DIAGNOSTIC: Check if there are clients assigned to marketers via assigned_marketer field
that are NOT in ClientMarketerAssignment table
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from django.db.models import Count, Q, OuterRef, Subquery
from django.db.models.functions import Coalesce
from estateApp.models import (
    Company, CustomUser, ClientMarketerAssignment, 
    ClientUser, MarketerUser, MarketerAffiliation
)

print("\n" + "█"*120)
print("█" + "  🔍 DIAGNOSTIC: Checking for assigned_marketer vs ClientMarketerAssignment mismatches".center(118) + "█")
print("█"*120 + "\n")

all_companies = Company.objects.all().order_by('company_name')

for company in all_companies:
    print(f"\n🏢 Company: {company.company_name}")
    print("─" * 120)
    
    # Get all clients for this company
    clients_by_company_profile = CustomUser.objects.filter(role='client', company_profile=company)
    clients_by_assignment = CustomUser.objects.filter(
        id__in=ClientMarketerAssignment.objects.filter(
            company=company
        ).values_list('client_id', flat=True)
    ).exclude(id__in=clients_by_company_profile.values_list('pk', flat=True))
    
    all_clients = list(clients_by_company_profile) + list(clients_by_assignment)
    
    if not all_clients:
        print("  ⚠️  No clients for this company")
        continue
    
    print(f"  📌 Total clients: {len(all_clients)}")
    print()
    
    for client in all_clients:
        print(f"  📍 Client: {client.full_name} ({client.email})")
        
        # Check assigned_marketer field
        assigned_marketer = None
        if hasattr(client, 'assigned_marketer'):
            assigned_marketer = client.assigned_marketer
        
        if assigned_marketer:
            print(f"     ✅ assigned_marketer field: {assigned_marketer.full_name}")
        else:
            print(f"     ❌ assigned_marketer field: Not set")
        
        # Check ClientMarketerAssignment
        cma = ClientMarketerAssignment.objects.filter(
            client=client,
            company=company
        ).first()
        
        if cma:
            print(f"     ✅ ClientMarketerAssignment: {cma.marketer.full_name if cma.marketer else 'No marketer'}")
        else:
            print(f"     ❌ ClientMarketerAssignment: Not found")
        
        # Check if they match
        if assigned_marketer and cma:
            if assigned_marketer.id == cma.marketer.id:
                print(f"     ✅ MATCH")
            else:
                print(f"     ⚠️  MISMATCH: assigned_marketer={assigned_marketer.full_name} vs CMA={cma.marketer.full_name}")
        elif assigned_marketer and not cma:
            print(f"     🔴 MISSING: Client has assigned_marketer but NO ClientMarketerAssignment!")
        elif not assigned_marketer and cma:
            print(f"     🟡 ORPHANED: ClientMarketerAssignment exists but assigned_marketer not set")
        
        print()

print("\n" + "█"*120)
print("█" + "  ✅ DIAGNOSTIC COMPLETE".ljust(118) + "█")
print("█"*120 + "\n")
