#!/usr/bin/env python
"""
Comprehensive Tenant Isolation Verification Script
Verifies complete data isolation across all features for multi-tenant system
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import (
    CustomUser, Estate, PlotSize, PlotNumber, PlotSizeUnits,
    PlotAllocation, EstatePlot, EstateLayout, EstateMap,
    EstateFloorPlan, EstatePrototype, ProgressStatus,
    PropertyRequest, Transaction, Message, Company
)
from django.db.models import Count, Q

def print_header(title):
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}\n")

def print_section(title):
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}")

def verify_isolation():
    print_header("COMPREHENSIVE TENANT ISOLATION VERIFICATION")
    
    # Get both companies
    companies = Company.objects.all().order_by('id')
    if companies.count() < 2:
        print("❌ ERROR: Need at least 2 companies to verify isolation")
        return
    
    company_a = companies[0]  # Lamba Real Estate
    company_b = companies[1]  # Lamba Properties Limited
    
    print(f"Company A: {company_a.company_name} ({company_a.id})")
    print(f"Company B: {company_b.company_name} ({company_b.id})")
    
    # ===== 1. USER ISOLATION =====
    print_section("1. USER ISOLATION (CLIENTS, MARKETERS, ADMINS)")
    
    for company, label in [(company_a, 'A'), (company_b, 'B')]:
        admins = CustomUser.objects.filter(role='admin', company_profile=company).count()
        clients = CustomUser.objects.filter(role='client', company_profile=company).count()
        marketers = CustomUser.objects.filter(role='marketer', company_profile=company).count()
        support = CustomUser.objects.filter(role='support', company_profile=company).count()
        
        print(f"\nCompany {label} ({company.company_name}):")
        print(f"  Admins: {admins}")
        print(f"  Clients: {clients}")
        print(f"  Marketers: {marketers}")
        print(f"  Support: {support}")
    
    # Check for orphaned users
    orphaned = CustomUser.objects.filter(company_profile__isnull=True).count()
    if orphaned > 0:
        print(f"\n⚠️  WARNING: {orphaned} users without company assignment")
        orphaned_users = CustomUser.objects.filter(company_profile__isnull=True)
        for user in orphaned_users:
            print(f"    - {user.email} ({user.role})")
    else:
        print(f"\n✅ All users assigned to companies")
    
    # ===== 2. ESTATE & PLOT ISOLATION =====
    print_section("2. ESTATE & PLOT DATA")
    
    models_to_check = [
        ('Estate', Estate),
        ('PlotSize', PlotSize),
        ('PlotNumber', PlotNumber),
        ('PlotSizeUnits', PlotSizeUnits),
        ('PlotAllocation', PlotAllocation),
        ('EstatePlot', EstatePlot),
        ('EstateLayout', EstateLayout),
        ('EstateMap', EstateMap),
        ('EstateFloorPlan', EstateFloorPlan),
        ('EstatePrototype', EstatePrototype),
    ]
    
    for model_name, model_class in models_to_check:
        count_a = model_class.objects.filter(company=company_a).count()
        count_b = model_class.objects.filter(company=company_b).count()
        total = model_class.objects.count()
        orphaned = model_class.objects.filter(company__isnull=True).count()
        
        print(f"\n{model_name}:")
        print(f"  Company A: {count_a}")
        print(f"  Company B: {count_b}")
        print(f"  Total: {total}")
        
        if orphaned > 0:
            print(f"  ⚠️  Orphaned (no company): {orphaned}")
        
        if count_a + count_b + orphaned != total:
            print(f"  ❌ DATA LEAK DETECTED! Counts don't match!")
    
    # ===== 3. TRANSACTION ISOLATION =====
    print_section("3. TRANSACTIONS & PAYMENTS")
    
    for company, label in [(company_a, 'A'), (company_b, 'B')]:
        txn_count = Transaction.objects.filter(company=company).count()
        
        print(f"\nCompany {label} ({company.company_name}):")
        print(f"  Total Transactions: {txn_count}")
    
    orphaned_txn = Transaction.objects.filter(company__isnull=True).count()
    if orphaned_txn > 0:
        print(f"\n⚠️  WARNING: {orphaned_txn} transactions without company")
    else:
        print(f"\n✅ All transactions assigned to companies")
    
    # ===== 4. MESSAGE/CHAT ISOLATION =====
    print_section("4. MESSAGES & CHAT")
    
    for company, label in [(company_a, 'A'), (company_b, 'B')]:
        msg_count = Message.objects.filter(company=company).count()
        unread = Message.objects.filter(company=company, is_read=False).count()
        
        print(f"\nCompany {label} ({company.company_name}):")
        print(f"  Total Messages: {msg_count}")
        print(f"  Unread: {unread}")
    
    orphaned_msg = Message.objects.filter(company__isnull=True).count()
    if orphaned_msg > 0:
        print(f"\n⚠️  WARNING: {orphaned_msg} messages without company")
    else:
        print(f"\n✅ All messages assigned to companies")
    
    # ===== 5. PROGRESS STATUS ISOLATION =====
    print_section("5. PROGRESS STATUS")
    
    for company, label in [(company_a, 'A'), (company_b, 'B')]:
        progress_count = ProgressStatus.objects.filter(company=company).count()
        print(f"Company {label}: {progress_count} progress records")
    
    # ===== 6. CROSS-CONTAMINATION CHECK =====
    print_section("6. CROSS-CONTAMINATION VERIFICATION")
    
    # Check if Company A users are assigned to Company B data
    print("\nChecking if Company A users are linked to Company B data...")
    company_a_users = CustomUser.objects.filter(company_profile=company_a)
    
    cross_contamination_found = False
    
    for user in company_a_users:
        # Check allocations
        wrong_allocations = PlotAllocation.objects.filter(
            client=user,
            company=company_b
        ).count()
        
        if wrong_allocations > 0:
            print(f"  ❌ User {user.email} (Company A) has {wrong_allocations} allocations in Company B!")
            cross_contamination_found = True
        
        # Check transactions
        wrong_transactions = Transaction.objects.filter(
            client=user,
            company=company_b
        ).count()
        
        if wrong_transactions > 0:
            print(f"  ❌ User {user.email} (Company A) has {wrong_transactions} transactions in Company B!")
            cross_contamination_found = True
        
        # Check messages
        wrong_messages = Message.objects.filter(
            sender=user,
            company=company_b
        ).count()
        
        if wrong_messages > 0:
            print(f"  ❌ User {user.email} (Company A) has {wrong_messages} messages in Company B!")
            cross_contamination_found = True
    
    # Check reverse: Company B users linked to Company A data
    print("\nChecking if Company B users are linked to Company A data...")
    company_b_users = CustomUser.objects.filter(company_profile=company_b)
    
    for user in company_b_users:
        wrong_allocations = PlotAllocation.objects.filter(
            client=user,
            company=company_a
        ).count()
        
        if wrong_allocations > 0:
            print(f"  ❌ User {user.email} (Company B) has {wrong_allocations} allocations in Company A!")
            cross_contamination_found = True
        
        wrong_transactions = Transaction.objects.filter(
            client=user,
            company=company_a
        ).count()
        
        if wrong_transactions > 0:
            print(f"  ❌ User {user.email} (Company B) has {wrong_transactions} transactions in Company A!")
            cross_contamination_found = True
        
        wrong_messages = Message.objects.filter(
            sender=user,
            company=company_a
        ).count()
        
        if wrong_messages > 0:
            print(f"  ❌ User {user.email} (Company B) has {wrong_messages} messages in Company A!")
            cross_contamination_found = True
    
    if not cross_contamination_found:
        print("\n✅ NO CROSS-CONTAMINATION FOUND!")
        print("   All users correctly linked to their company's data only.")
    
    # ===== FINAL SUMMARY =====
    print_header("ISOLATION VERIFICATION SUMMARY")
    
    total_issues = 0
    
    # Count orphaned records
    orphaned_counts = {
        'Users': CustomUser.objects.filter(company_profile__isnull=True).count(),
        'Estates': Estate.objects.filter(company__isnull=True).count(),
        'PlotSizes': PlotSize.objects.filter(company__isnull=True).count(),
        'PlotNumbers': PlotNumber.objects.filter(company__isnull=True).count(),
        'Transactions': Transaction.objects.filter(company__isnull=True).count(),
        'Messages': Message.objects.filter(company__isnull=True).count(),
    }
    
    print("\nOrphaned Records (no company assignment):")
    for key, count in orphaned_counts.items():
        if count > 0:
            print(f"  ⚠️  {key}: {count}")
            total_issues += count
        else:
            print(f"  ✅ {key}: 0")
    
    print(f"\nCross-contamination: {'❌ FOUND' if cross_contamination_found else '✅ NONE'}")
    
    if total_issues == 0 and not cross_contamination_found:
        print("\n" + "="*80)
        print("🎉 PERFECT ISOLATION! All data correctly isolated by company!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print(f"⚠️  ISSUES FOUND: {total_issues} orphaned records")
        if cross_contamination_found:
            print("❌ Cross-contamination detected!")
        print("="*80)
    
    return total_issues == 0 and not cross_contamination_found

if __name__ == "__main__":
    success = verify_isolation()
    sys.exit(0 if success else 1)
