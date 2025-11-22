#!/usr/bin/env python
"""
Test dashboard counts to see what's being displayed
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import (
    CustomUser, Estate, PlotAllocation, Company, Message
)
from django.db.models import Q, Count, Prefetch

def test_dashboard_counts():
    print("\n" + "="*80)
    print("TESTING DASHBOARD COUNTS")
    print("="*80)
    
    # Get Company A
    company = Company.objects.filter(email='estate@gmail.com').first()
    if not company:
        print("❌ ERROR: Company A not found!")
        return
    
    print(f"\n✅ Company: {company.company_name} (ID: {company.id})")
    
    # Test the exact queries from admin_dashboard view
    print("\n" + "-"*80)
    print("TESTING EXACT DASHBOARD QUERIES")
    print("-"*80)
    
    # Total clients
    total_clients = CustomUser.objects.filter(role='client', company_profile=company).count()
    print(f"\ntotal_clients = CustomUser.objects.filter(role='client', company_profile=company).count()")
    print(f"Result: {total_clients}")
    
    # Total marketers
    total_marketers = CustomUser.objects.filter(role='marketer', company_profile=company).count()
    print(f"\ntotal_marketers = CustomUser.objects.filter(role='marketer', company_profile=company).count()")
    print(f"Result: {total_marketers}")
    
    # Total allocations (full payments with plot numbers)
    total_allocations = PlotAllocation.objects.filter(
        payment_type='full',
        plot_number__isnull=False,
        company=company
    ).count()
    print(f"\ntotal_allocations = PlotAllocation.objects.filter(")
    print(f"    payment_type='full',")
    print(f"    plot_number__isnull=False,")
    print(f"    company=company")
    print(f").count()")
    print(f"Result: {total_allocations}")
    
    # Pending allocations (part payments without plot numbers)
    pending_allocations = PlotAllocation.objects.filter(
        payment_type='part',
        plot_number__isnull=True,
        company=company
    ).count()
    print(f"\npending_allocations = PlotAllocation.objects.filter(")
    print(f"    payment_type='part',")
    print(f"    plot_number__isnull=True,")
    print(f"    company=company")
    print(f").count()")
    print(f"Result: {pending_allocations}")
    
    # Check ALL allocations
    print(f"\n" + "-"*80)
    print("CHECKING ALL ALLOCATIONS IN DETAIL")
    print("-"*80)
    
    all_allocations = PlotAllocation.objects.filter(company=company)
    print(f"\nTotal allocations for company: {all_allocations.count()}")
    
    for alloc in all_allocations:
        client_name = alloc.client.full_name if alloc.client else "N/A"
        plot_num = alloc.plot_number.number if alloc.plot_number else "NONE (Reserved)"
        print(f"  - {client_name}: payment_type={alloc.payment_type}, plot_number={plot_num}")
    
    # Summary
    print("\n" + "="*80)
    print("DASHBOARD DISPLAY SHOULD SHOW:")
    print("="*80)
    print(f"Total Clients: {total_clients}")
    print(f"Total Marketers: {total_marketers}")
    print(f"Total Allocations: {total_allocations}")
    print(f"Pending Allocations: {pending_allocations}")
    
    if total_clients == 0 or total_marketers == 0:
        print("\n❌ PROBLEM: Counts are showing 0 when data exists!")
        print("   This suggests the dashboard view is not getting the company correctly")
    else:
        print("\n✅ All counts are correct!")

if __name__ == "__main__":
    test_dashboard_counts()
