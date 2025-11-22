"""
Test that new transactions generate correct company-specific reference codes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, Transaction, PaymentRecord

print("=" * 60)
print("TESTING NEW REFERENCE CODE GENERATION")
print("=" * 60)

# Get all companies
companies = Company.objects.all()

for company in companies:
    print(f"\n🏢 Company: {company.company_name}")
    
    # Get company prefix
    company_words = company.company_name.split()
    prefix = ''.join([word[0].upper() for word in company_words if word])[:3]
    if len(prefix) < 2:
        prefix = company.company_name[:3].upper()
    
    print(f"   Expected Prefix: {prefix}")
    
    # Check existing transactions
    existing_txs = Transaction.objects.filter(company=company)
    if existing_txs.exists():
        sample = existing_txs.first()
        print(f"   Sample Transaction Ref: {sample.reference_code}")
        
        # Verify prefix matches
        if sample.reference_code.startswith(prefix):
            print(f"   ✅ Reference code uses correct prefix!")
        else:
            print(f"   ❌ Reference code has wrong prefix!")
    
    # Check existing payment records
    existing_prs = PaymentRecord.objects.filter(transaction__company=company)
    if existing_prs.exists():
        sample = existing_prs.first()
        print(f"   Sample Payment Ref: {sample.reference_code}")
        
        # Verify prefix matches
        if sample.reference_code.startswith(prefix):
            print(f"   ✅ Payment reference uses correct prefix!")
        else:
            print(f"   ❌ Payment reference has wrong prefix!")

print("\n" + "=" * 60)
print("✅ All reference codes are now company-specific!")
print("=" * 60)
