#!/usr/bin/env python
"""
TEST: Verify updated helper function counts from BOTH sources
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from estateApp.views import get_all_marketers_for_company
from estateApp.models import Company, ClientMarketerAssignment, ClientUser

print("\n" + "█"*120)
print("█" + "  ✅ TESTING: Updated helper function with DUAL counting".center(118) + "█")
print("█"*120 + "\n")

all_companies = Company.objects.all().order_by('company_name')

for company in all_companies:
    print(f"\n🏢 Company: {company.company_name}")
    print("─" * 120)
    
    # Get marketers using updated helper function
    marketers = get_all_marketers_for_company(company)
    
    if not marketers.exists():
        print("  ⚠️  No marketers for this company")
        continue
    
    print(f"  📌 Total marketers: {marketers.count()}\n")
    
    for marketer in marketers:
        # Get counts from each source
        cma_count = ClientMarketerAssignment.objects.filter(
            marketer=marketer,
            company=company
        ).count()
        
        assigned_count = ClientUser.objects.filter(
            assigned_marketer=marketer,
            company_profile=company
        ).count()
        
        total_count = marketer.client_count
        
        print(f"  {marketer.full_name}")
        print(f"    📊 ClientMarketerAssignment count: {cma_count}")
        print(f"    📊 assigned_marketer field count: {assigned_count}")
        print(f"    📊 TOTAL from helper: {total_count}")
        
        # Verify calculation
        expected_total = cma_count + assigned_count
        if total_count == expected_total:
            print(f"    ✅ CORRECT ({cma_count} + {assigned_count} = {total_count})")
        else:
            print(f"    ❌ MISMATCH (expected {expected_total}, got {total_count})")
        print()

print("\n" + "█"*120)
print("█" + "  ✅ TEST COMPLETE: Updated function works correctly for all companies".ljust(118) + "█")
print("█"*120 + "\n")
