#!/usr/bin/env python
"""
COMPREHENSIVE TEST: Verify marketer client counts work for ALL companies
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from django.db.models import Count, Q, OuterRef, Subquery
from django.db.models.functions import Coalesce
from estateApp.models import (
    Company, CustomUser, ClientMarketerAssignment, 
    MarketerAffiliation, ClientUser, MarketerUser
)

print("\n" + "█"*120)
print("█" + "  🔍 TESTING: Marketer Client Counts Across ALL Companies".center(118) + "█")
print("█"*120 + "\n")

# Get all companies
all_companies = Company.objects.all().order_by('company_name')

print(f"📊 Total Companies: {all_companies.count()}\n")
print("─" * 120)

for company in all_companies:
    print(f"\n🏢 Company: {company.company_name} (ID: {company.id})")
    print(f"   Slug: {company.slug}")
    print("   " + "─" * 110)
    
    # Get all marketers (both primary and affiliated)
    marketers_primary = CustomUser.objects.filter(role='marketer', company_profile=company)
    
    # Get affiliated marketers
    affiliation_marketer_ids = MarketerAffiliation.objects.filter(
        company=company
    ).values_list('marketer_id', flat=True).distinct()
    
    marketers_affiliated = CustomUser.objects.filter(
        id__in=affiliation_marketer_ids
    ).exclude(
        id__in=marketers_primary.values_list('pk', flat=True)
    )
    
    # Combine all marketer IDs
    all_marketer_ids = set(marketers_primary.values_list('pk', flat=True)) | set(
        marketers_affiliated.values_list('pk', flat=True)
    )
    
    print(f"   📌 Primary marketers: {marketers_primary.count()}")
    print(f"   📌 Affiliated marketers: {marketers_affiliated.count()}")
    print(f"   📌 Total marketers: {len(all_marketer_ids)}")
    
    if not all_marketer_ids:
        print(f"   ⚠️  No marketers found for this company")
        print()
        continue
    
    # Get client counts using Subquery
    client_count_subquery = ClientMarketerAssignment.objects.filter(
        marketer_id=OuterRef('id'),
        company=company
    ).values('marketer_id').annotate(
        count=Count('id')
    ).values('count')
    
    # Get all marketers with correct client counts
    marketers_with_counts = CustomUser.objects.filter(id__in=all_marketer_ids).annotate(
        client_count=Subquery(client_count_subquery)
    ).annotate(
        client_count=Coalesce('client_count', 0)
    ).order_by('full_name')
    
    print(f"\n   📋 Marketers with Client Counts:")
    print(f"   " + "─" * 110)
    
    total_clients_in_company = 0
    
    for marketer in marketers_with_counts:
        count = marketer.client_count
        total_clients_in_company += count
        
        # Visual indicator
        if count > 0:
            status = "✅"
        else:
            status = "⚪"
        
        print(f"   {status} {marketer.full_name:<30} ({marketer.email:<35}) → {count} client(s)")
    
    # Verify total using ClientMarketerAssignment
    total_assignments = ClientMarketerAssignment.objects.filter(
        company=company
    ).count()
    
    print(f"\n   " + "─" * 110)
    print(f"   📊 Total client-marketer assignments: {total_assignments}")
    print(f"   📊 Sum of all marketer counts: {total_clients_in_company}")
    
    if total_assignments == total_clients_in_company:
        print(f"   ✅ VERIFICATION: Counts match!")
    else:
        print(f"   ⚠️  MISMATCH: Assignments ({total_assignments}) ≠ Counts ({total_clients_in_company})")
    
    # Show actual assignments
    if total_assignments > 0:
        print(f"\n   📌 Detailed Assignments:")
        assignments = ClientMarketerAssignment.objects.filter(
            company=company
        ).select_related('marketer', 'client')
        
        for assignment in assignments:
            marketer_name = assignment.marketer.full_name if assignment.marketer else "Unknown"
            client_name = assignment.client.full_name if assignment.client else "Unknown"
            print(f"      • {marketer_name} → {client_name}")
    
    print("\n" + "─" * 120)

print("\n" + "█"*120)
print("█" + "  ✅ TEST COMPLETE: All companies checked".ljust(118) + "█")
print("█"*120 + "\n")
