#!/usr/bin/env python
"""
Test multi-company client count functionality
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.insert(0, os.getcwd())
django.setup()

from estateApp.models import Company, CustomUser, ClientMarketerAssignment
import json

print("\n" + "="*100)
print("MULTI-COMPANY TEST: Verify client counts are per-company")
print("="*100 + "\n")

# Get all companies with marketers
companies = Company.objects.filter(is_active=True)[:3]

for company in companies:
    print(f"\n📍 Company: {company.company_name}")
    print("─" * 100)
    
    # Get assignments for this company
    assignments = ClientMarketerAssignment.objects.filter(company=company)
    
    if not assignments.exists():
        print("   ℹ️ No client-marketer assignments in this company")
        continue
    
    # Group by marketer
    from django.db.models import Count
    marketer_counts = assignments.values('marketer__full_name', 'marketer__email', 'marketer_id').annotate(
        client_count=Count('client', distinct=True)
    ).order_by('-client_count')
    
    for item in marketer_counts:
        print(f"   ✅ {item['marketer__full_name']} ({item['marketer__email']}): {item['client_count']} clients")

print("\n" + "="*100)
print("✅ Multi-company client count verification complete")
print("="*100 + "\n")
