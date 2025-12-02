#!/usr/bin/env python
"""
Script to fix transactions missing the company field.
Run this after deploying the code fix.

Usage:
    python manage.py shell
    >>> exec(open('fix_transaction_company_field.py').read())
"""

from estateApp.models import Transaction, PlotAllocation, Company
from django.db.models import Q

print("="*60)
print("FIXING TRANSACTION COMPANY FIELD INCONSISTENCIES")
print("="*60)

# Find all transactions without a company
transactions_without_company = Transaction.objects.filter(company__isnull=True)
print(f"\nFound {transactions_without_company.count()} transactions without company field")

if transactions_without_company.count() == 0:
    print("✅ All transactions have company field set!")
else:
    # Fix each transaction by getting company from allocation
    fixed_count = 0
    error_count = 0
    
    for txn in transactions_without_company:
        try:
            if txn.allocation and txn.allocation.estate and txn.allocation.estate.company:
                txn.company = txn.allocation.estate.company
                txn.save(update_fields=['company'])
                fixed_count += 1
                print(f"  ✓ Fixed transaction {txn.id}: company={txn.company.company_name}")
            else:
                print(f"  ✗ Transaction {txn.id}: Cannot determine company (missing allocation/estate/company)")
                error_count += 1
        except Exception as e:
            print(f"  ✗ Transaction {txn.id}: Error - {str(e)}")
            error_count += 1
    
    print(f"\n✅ Fixed: {fixed_count}")
    print(f"❌ Errors: {error_count}")

# Verify the fix
remaining = Transaction.objects.filter(company__isnull=True).count()
print(f"\nVerification: {remaining} transactions still without company")

if remaining == 0:
    print("✅ SUCCESS! All transactions now have company field set correctly")
else:
    print("⚠️ WARNING: Some transactions still need manual fixes")
    print("\nManual fix required for transactions:")
    for txn in Transaction.objects.filter(company__isnull=True):
        print(f"  - Transaction {txn.id}: client={txn.client.full_name}, allocation={txn.allocation.id}")

print("\n" + "="*60)
print("SCRIPT COMPLETE")
print("="*60)
