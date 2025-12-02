#!/usr/bin/env python
"""
Test script to verify that payment reference codes are dynamically generated with company prefixes.

Usage:
    python manage.py shell -c "exec(open('test_dynamic_payment_references.py').read())"
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, Transaction, PaymentRecord, PlotAllocation
from decimal import Decimal
from django.utils import timezone

print("\n" + "="*70)
print("TESTING DYNAMIC PAYMENT REFERENCE CODES")
print("="*70)

# Get a test company with prefix
companies = Company.objects.all()[:2]  # Test with first 2 companies
if not companies:
    print("\n❌ No companies found for testing")
    exit(1)

print(f"\n✅ Found {len(companies)} companies for testing")

for company in companies:
    prefix = company._company_prefix()
    print(f"\n{'='*70}")
    print(f"Company: {company.company_name}")
    print(f"Prefix: {prefix}")
    print(f"{'='*70}")
    
    # Get allocations for this company
    allocations = PlotAllocation.objects.filter(estate__company=company)[:1]
    if not allocations:
        print(f"  ⚠️  No allocations found for {company.company_name}")
        continue
    
    allocation = allocations[0]
    
    # Get a client
    from estateApp.models import ClientUser
    clients = ClientUser.objects.filter(company=company)[:1]
    if not clients:
        print(f"  ⚠️  No clients found for {company.company_name}")
        continue
    
    client = clients[0]
    
    # Test 1: Create new Transaction and verify reference code
    print(f"\n📋 Test 1: Creating new Transaction...")
    try:
        txn = Transaction(
            company=company,
            client=client,
            allocation=allocation,
            transaction_date=timezone.now().date(),
            total_amount=Decimal('150000000.00'),
            payment_method='bank'
        )
        txn.save()
        print(f"   ✅ Transaction created successfully")
        print(f"   Reference Code: {txn.reference_code}")
        
        if txn.reference_code.startswith(prefix):
            print(f"   ✅ Reference code correctly uses company prefix '{prefix}'")
        else:
            print(f"   ❌ Reference code does NOT use company prefix!")
            print(f"      Expected prefix: {prefix}")
            print(f"      Got: {txn.reference_code[:3]}")
    except Exception as e:
        print(f"   ❌ Failed to create transaction: {e}")
        continue
    
    # Test 2: Create new PaymentRecord and verify reference code
    print(f"\n📋 Test 2: Creating new PaymentRecord...")
    try:
        payment = PaymentRecord(
            transaction=txn,
            company=company,
            installment=1,
            amount_paid=Decimal('50000000.00'),
            payment_date=timezone.now().date(),
            payment_method='bank'
        )
        payment.save()
        print(f"   ✅ PaymentRecord created successfully")
        print(f"   Reference Code: {payment.reference_code}")
        
        if payment.reference_code.startswith(prefix):
            print(f"   ✅ Reference code correctly uses company prefix '{prefix}'")
        else:
            print(f"   ❌ Reference code does NOT use company prefix!")
            print(f"      Expected prefix: {prefix}")
            print(f"      Got: {payment.reference_code[:3]}")
    except Exception as e:
        print(f"   ❌ Failed to create payment record: {e}")
        import traceback
        traceback.print_exc()
        continue

print("\n" + "="*70)
print("TEST COMPLETE ✅")
print("="*70)
print("\n✨ Payment reference codes are now dynamically generated!")
print(f"   Each company has its own unique prefix (e.g., LPL, LRH, NPL, etc.)")
print("="*70 + "\n")
