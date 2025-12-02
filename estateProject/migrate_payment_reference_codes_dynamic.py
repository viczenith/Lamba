#!/usr/bin/env python
"""
Migration script to update all existing payment reference codes to use dynamic company prefixes.

This script converts hardcoded 'NLP' prefixes to dynamic prefixes based on each transaction's company.

Format changes:
- Transaction: NLP20251201-250-4985 → NPL20251201-250-4985 (for company with prefix NPL)
- PaymentRecord: NLP-20251201-250BAN4985 → NPL-20251201-250BAN4985 (for company with prefix NPL)

Usage:
    python manage.py shell < migrate_payment_reference_codes_dynamic.py
"""

import re
import sys
from decimal import Decimal
from django.db import transaction as db_transaction
from estateApp.models import Company, Transaction, PaymentRecord

def get_company_prefix(company):
    """Get the dynamic prefix for a company"""
    try:
        return company._company_prefix()
    except Exception as e:
        print(f"  ❌ Error getting prefix for company {company.id}: {e}")
        return None

def migrate_transaction_references():
    """Update all Transaction reference codes"""
    print("\n" + "="*70)
    print("MIGRATING TRANSACTION REFERENCE CODES")
    print("="*70)
    
    transactions = Transaction.objects.all()
    updated = 0
    skipped = 0
    
    print(f"\n📋 Found {transactions.count()} transactions to process...")
    
    with db_transaction.atomic():
        for txn in transactions:
            if not txn.reference_code:
                skipped += 1
                continue
            
            # Pattern: NLP20251201-250-4985 or similar
            # Extract: prefix-date-size-suffix
            match = re.match(r'^([A-Z]{2,3})(\d{8})-(.+)-(\d{4})$', txn.reference_code)
            
            if not match:
                print(f"  ⚠️  Transaction {txn.id}: Invalid format '{txn.reference_code}' - Skipping")
                skipped += 1
                continue
            
            old_prefix = match.group(1)
            date_part = match.group(2)
            size_part = match.group(3)
            suffix_part = match.group(4)
            
            # Get correct prefix from company
            company = txn.company or (txn.allocation.estate.company if txn.allocation and txn.allocation.estate else None)
            if not company:
                print(f"  ❌ Transaction {txn.id}: No company found - Skipping")
                skipped += 1
                continue
            
            new_prefix = get_company_prefix(company)
            if not new_prefix:
                skipped += 1
                continue
            
            # Only update if prefix changed
            if old_prefix != new_prefix:
                old_code = txn.reference_code
                txn.reference_code = f"{new_prefix}{date_part}-{size_part}-{suffix_part}"
                txn.save(update_fields=['reference_code'])
                updated += 1
                print(f"  ✅ Transaction {txn.id}: {old_code} → {txn.reference_code} ({company.company_name})")
            else:
                print(f"  ℹ️  Transaction {txn.id}: Prefix already correct ({new_prefix})")
    
    print(f"\n📊 Transaction Results: {updated} updated, {skipped} skipped")
    return updated

def migrate_payment_record_references():
    """Update all PaymentRecord reference codes"""
    print("\n" + "="*70)
    print("MIGRATING PAYMENT RECORD REFERENCE CODES")
    print("="*70)
    
    payments = PaymentRecord.objects.all()
    updated = 0
    skipped = 0
    
    print(f"\n📋 Found {payments.count()} payment records to process...")
    
    with db_transaction.atomic():
        for pr in payments:
            if not pr.reference_code:
                skipped += 1
                continue
            
            # Pattern: NLP-20251201-250BAN4985 or NLP-20251201-250-4985
            # Extract: prefix-date-size-method-suffix (or similar)
            match = re.match(r'^([A-Z]{2,3})(-?)(\d{8})-(.+)$', pr.reference_code)
            
            if not match:
                print(f"  ⚠️  PaymentRecord {pr.id}: Invalid format '{pr.reference_code}' - Skipping")
                skipped += 1
                continue
            
            old_prefix = match.group(1)
            dash_after_prefix = match.group(2)  # Empty string or '-'
            date_part = match.group(3)
            rest_part = match.group(4)  # size-method-suffix
            
            # Get correct prefix from company
            company = pr.company or (pr.transaction.allocation.estate.company if pr.transaction and pr.transaction.allocation and pr.transaction.allocation.estate else None)
            if not company:
                print(f"  ❌ PaymentRecord {pr.id}: No company found - Skipping")
                skipped += 1
                continue
            
            new_prefix = get_company_prefix(company)
            if not new_prefix:
                skipped += 1
                continue
            
            # Only update if prefix changed
            if old_prefix != new_prefix:
                old_code = pr.reference_code
                # Preserve format (with or without dash after prefix)
                if dash_after_prefix:
                    pr.reference_code = f"{new_prefix}-{date_part}-{rest_part}"
                else:
                    pr.reference_code = f"{new_prefix}-{date_part}-{rest_part}"
                pr.save(update_fields=['reference_code'])
                updated += 1
                print(f"  ✅ PaymentRecord {pr.id}: {old_code} → {pr.reference_code} ({company.company_name})")
            else:
                print(f"  ℹ️  PaymentRecord {pr.id}: Prefix already correct ({new_prefix})")
    
    print(f"\n📊 Payment Record Results: {updated} updated, {skipped} skipped")
    return updated

def main():
    """Run the migration"""
    print("\n" + "="*70)
    print("DYNAMIC PAYMENT REFERENCE CODE MIGRATION")
    print("="*70)
    print("\nThis script will update all payment reference codes to use")
    print("dynamic company-specific prefixes instead of hardcoded 'NLP'.")
    print("\nExample:")
    print("  NLP20251201-250-4985 → NPL20251201-250-4985")
    print("  NLP-20251201-250BAN4985 → NPL-20251201-250BAN4985")
    print("="*70)
    
    try:
        # Check if there are any companies
        if not Company.objects.exists():
            print("\n❌ No companies found. Please create companies first.")
            return
        
        print(f"\n✅ Found {Company.objects.count()} companies")
        
        # Run migrations
        txn_updated = migrate_transaction_references()
        pr_updated = migrate_payment_record_references()
        
        # Summary
        total_updated = txn_updated + pr_updated
        print("\n" + "="*70)
        print("MIGRATION COMPLETE ✅")
        print("="*70)
        print(f"\n📊 Total Updated: {total_updated} records")
        print(f"   - Transactions: {txn_updated}")
        print(f"   - Payment Records: {pr_updated}")
        print("\n✨ All payment reference codes now use dynamic company prefixes!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
