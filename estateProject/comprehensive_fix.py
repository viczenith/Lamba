#!/usr/bin/env python
"""
COMPREHENSIVE DATA FIX - Ensure ALL data is properly linked to Company A
and fix any remaining isolation issues
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from estateApp.models import (
    CustomUser, Estate, PlotSize, PlotNumber, PlotSizeUnits,
    PlotAllocation, EstatePlot, EstateLayout, EstateMap,
    EstateFloorPlan, EstatePrototype, ProgressStatus,
    PropertyRequest, Transaction, Message, Company, PropertyPrice,
    PriceHistory
)
from django.db import transaction as db_transaction
from django.db.models import Q

def comprehensive_fix():
    print("\n" + "="*80)
    print("COMPREHENSIVE DATA FIX FOR COMPANY A")
    print("="*80)
    
    # Get Company A
    company_a = Company.objects.filter(email='estate@gmail.com').first()
    if not company_a:
        print("❌ ERROR: Company A not found!")
        return False
    
    print(f"\n✅ Company A Found: {company_a.company_name}")
    print(f"   Email: {company_a.email}")
    print(f"   ID: {company_a.id}")
    
    # Get Company B
    company_b = Company.objects.exclude(id=company_a.id).first()
    if company_b:
        print(f"\n✅ Company B Found: {company_b.company_name}")
        print(f"   Email: {company_b.email}")
        print(f"   ID: {company_b.id}")
    
    with db_transaction.atomic():
        print("\n" + "-"*80)
        print("STEP 1: ASSIGN ALL USERS TO COMPANY A (except Company B admins/support)")
        print("-"*80)
        
        # Get Company B staff (admins and support) to preserve
        company_b_staff_emails = []
        if company_b:
            company_b_staff = CustomUser.objects.filter(
                Q(email='akorvikkyy@gmail.com') |  # Company B admin
                Q(email__contains='company_b') |
                Q(role='support', company_profile=company_b)
            )
            company_b_staff_emails = list(company_b_staff.values_list('email', flat=True))
            print(f"\nPreserving {company_b_staff.count()} Company B staff members:")
            for email in company_b_staff_emails:
                print(f"  - {email}")
        
        # Assign all other users to Company A
        users_to_fix = CustomUser.objects.exclude(
            Q(email__in=company_b_staff_emails) |
            Q(is_superuser=True)  # Don't touch superusers
        )
        
        updated_users = users_to_fix.update(company_profile=company_a)
        print(f"\n✅ Updated {updated_users} users to Company A")
        
        # Show breakdown
        admins = CustomUser.objects.filter(role='admin', company_profile=company_a).count()
        clients = CustomUser.objects.filter(role='client', company_profile=company_a).count()
        marketers = CustomUser.objects.filter(role='marketer', company_profile=company_a).count()
        support = CustomUser.objects.filter(role='support', company_profile=company_a).count()
        
        print(f"\nCompany A now has:")
        print(f"  Admins: {admins}")
        print(f"  Clients: {clients}")
        print(f"  Marketers: {marketers}")
        print(f"  Support: {support}")
        
        print("\n" + "-"*80)
        print("STEP 2: ASSIGN ALL ESTATE-RELATED DATA TO COMPANY A")
        print("-"*80)
        
        models_to_fix = [
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
            ('ProgressStatus', ProgressStatus),
            ('Transaction', Transaction),
            ('Message', Message),
        ]
        
        for model_name, model_class in models_to_fix:
            count = model_class.objects.update(company=company_a)
            print(f"  ✅ {model_name}: {count} records → Company A")
        
        # Fix PropertyRequest if it has company field
        try:
            count = PropertyRequest.objects.update(company=company_a)
            print(f"  ✅ PropertyRequest: {count} records → Company A")
        except:
            pass
        
        print("\n" + "-"*80)
        print("STEP 3: VERIFY NO ORPHANED RECORDS")
        print("-"*80)
        
        orphaned_counts = {}
        all_good = True
        
        # Check users
        orphaned_users = CustomUser.objects.filter(company_profile__isnull=True, is_superuser=False).count()
        if orphaned_users > 0:
            print(f"  ⚠️  Users without company: {orphaned_users}")
            orphaned_counts['Users'] = orphaned_users
            all_good = False
        else:
            print(f"  ✅ Users: 0 orphaned")
        
        # Check other models
        for model_name, model_class in models_to_fix:
            orphaned = model_class.objects.filter(company__isnull=True).count()
            if orphaned > 0:
                print(f"  ⚠️  {model_name} without company: {orphaned}")
                orphaned_counts[model_name] = orphaned
                all_good = False
            else:
                print(f"  ✅ {model_name}: 0 orphaned")
        
        print("\n" + "-"*80)
        print("STEP 4: FINAL VERIFICATION")
        print("-"*80)
        
        # Count Company A data
        print(f"\nCompany A ({company_a.company_name}) Data:")
        print(f"  Users: {CustomUser.objects.filter(company_profile=company_a).count()}")
        print(f"  Estates: {Estate.objects.filter(company=company_a).count()}")
        print(f"  Plot Sizes: {PlotSize.objects.filter(company=company_a).count()}")
        print(f"  Plot Numbers: {PlotNumber.objects.filter(company=company_a).count()}")
        print(f"  Allocations: {PlotAllocation.objects.filter(company=company_a).count()}")
        print(f"  Transactions: {Transaction.objects.filter(company=company_a).count()}")
        print(f"  Messages: {Message.objects.filter(company=company_a).count()}")
        
        # Test dashboard queries
        print(f"\nDashboard Counts (what should display):")
        total_clients = CustomUser.objects.filter(role='client', company_profile=company_a).count()
        total_marketers = CustomUser.objects.filter(role='marketer', company_profile=company_a).count()
        total_allocations = PlotAllocation.objects.filter(
            payment_type='full',
            plot_number__isnull=False,
            company=company_a
        ).count()
        pending_allocations = PlotAllocation.objects.filter(
            payment_type='part',
            plot_number__isnull=True,
            company=company_a
        ).count()
        
        print(f"  Total Clients: {total_clients}")
        print(f"  Total Marketers: {total_marketers}")
        print(f"  Total Allocations: {total_allocations}")
        print(f"  Pending Allocations: {pending_allocations}")
        
        if company_b:
            print(f"\nCompany B ({company_b.company_name}) Data:")
            print(f"  Users: {CustomUser.objects.filter(company_profile=company_b).count()}")
            print(f"  Estates: {Estate.objects.filter(company=company_b).count()}")
        
        print("\n" + "="*80)
        if all_good and total_clients > 0 and total_marketers > 0:
            print("✅ ALL DATA SUCCESSFULLY FIXED!")
            print("✅ NO ORPHANED RECORDS!")
            print("✅ DASHBOARD SHOULD NOW DISPLAY ALL COUNTS CORRECTLY!")
            print("="*80)
            return True
        else:
            print("⚠️  SOME ISSUES REMAIN - CHECK LOGS ABOVE")
            print("="*80)
            return False

if __name__ == "__main__":
    success = comprehensive_fix()
    sys.exit(0 if success else 1)
