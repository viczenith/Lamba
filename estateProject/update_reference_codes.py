"""
Update all Transaction and PaymentRecord reference codes to use correct company prefix
"""
import os
import django
import re
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Transaction, PaymentRecord, Company

def get_company_prefix(company_name):
    """Generate prefix from company name initials"""
    company_words = company_name.split()
    prefix = ''.join([word[0].upper() for word in company_words if word])[:3]
    if len(prefix) < 2:  # Fallback if company name is too short
        prefix = company_name[:3].upper()
    return prefix

def update_transaction_reference_codes():
    """Update all Transaction reference codes"""
    transactions = Transaction.objects.all()
    updated = 0
    
    for tx in transactions:
        if tx.reference_code:
            # Extract the old prefix (first 3 letters before the date)
            match = re.match(r'^([A-Z]{2,3})(\d{8}-.+)$', tx.reference_code)
            if match:
                old_prefix = match.group(1)
                rest_of_code = match.group(2)
                
                # Get correct prefix from company
                new_prefix = get_company_prefix(tx.company.company_name)
                
                if old_prefix != new_prefix:
                    tx.reference_code = f"{new_prefix}{rest_of_code}"
                    tx.save(update_fields=['reference_code'])
                    updated += 1
                    print(f"✓ Updated Transaction {tx.id}: {old_prefix}{rest_of_code} → {tx.reference_code}")
    
    return updated

def update_payment_record_reference_codes():
    """Update all PaymentRecord reference codes"""
    payments = PaymentRecord.objects.all()
    updated = 0
    
    for pr in payments:
        if pr.reference_code:
            # PaymentRecord format can be either:
            # NLP-20251121-950BAN6446 or NLP20251121-950-6446
            # Extract the old prefix (first 3 letters)
            match = re.match(r'^([A-Z]{2,3})[-]?(\d{8}-.+)$', pr.reference_code)
            if match:
                old_prefix = match.group(1)
                rest_of_code = match.group(2)
                
                # Get correct prefix from company
                new_prefix = get_company_prefix(pr.transaction.company.company_name)
                
                if old_prefix != new_prefix:
                    # Keep the same format (with or without dash after prefix)
                    if '-' in pr.reference_code[:4]:  # Has dash after prefix
                        pr.reference_code = f"{new_prefix}-{rest_of_code}"
                    else:  # No dash after prefix
                        pr.reference_code = f"{new_prefix}{rest_of_code}"
                    pr.save(update_fields=['reference_code'])
                    updated += 1
                    print(f"✓ Updated PaymentRecord {pr.id}: Old prefix {old_prefix} → {pr.reference_code}")
    
    return updated

if __name__ == "__main__":
    print("=" * 60)
    print("UPDATING REFERENCE CODES WITH CORRECT COMPANY PREFIX")
    print("=" * 60)
    
    # Show current company info
    companies = Company.objects.all()
    print("\nCompanies and their prefixes:")
    for company in companies:
        prefix = get_company_prefix(company.company_name)
        print(f"  • {company.company_name} → {prefix}")
    
    print("\n" + "=" * 60)
    print("Updating Transactions...")
    print("=" * 60)
    tx_updated = update_transaction_reference_codes()
    
    print("\n" + "=" * 60)
    print("Updating Payment Records...")
    print("=" * 60)
    pr_updated = update_payment_record_reference_codes()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Transactions updated: {tx_updated}")
    print(f"✓ PaymentRecords updated: {pr_updated}")
    print(f"✓ Total records updated: {tx_updated + pr_updated}")
    print("\n✅ Reference codes now use correct company prefixes!")
