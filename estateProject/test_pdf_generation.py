"""
Test PDF generation with base64 images
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Transaction, Company
from estateApp.views import image_to_base64

print("=" * 60)
print("TESTING PDF GENERATION WITH BASE64 IMAGES")
print("=" * 60)

# Get a company with logo and signature
companies = Company.objects.all()

for company in companies:
    print(f"\n🏢 Company: {company.company_name}")
    
    # Test logo conversion
    if company.logo:
        print(f"   Logo: {company.logo.name}")
        logo_base64 = image_to_base64(company.logo)
        if logo_base64:
            print(f"   ✅ Logo converted to base64 (length: {len(logo_base64)} chars)")
            print(f"   Preview: {logo_base64[:50]}...")
        else:
            print(f"   ❌ Failed to convert logo")
    else:
        print(f"   ⚠️  No logo set")
    
    # Test signature conversion
    if company.cashier_signature:
        print(f"   Signature: {company.cashier_signature.name}")
        sig_base64 = image_to_base64(company.cashier_signature)
        if sig_base64:
            print(f"   ✅ Signature converted to base64 (length: {len(sig_base64)} chars)")
            print(f"   Preview: {sig_base64[:50]}...")
        else:
            print(f"   ❌ Failed to convert signature")
    else:
        print(f"   ⚠️  No cashier signature set")
    
    # Check receipt counter
    print(f"   Receipt Counter: {company.receipt_counter}")
    
    # Test receipt number generation
    receipt_num = company.get_next_receipt_number()
    print(f"   Next Receipt Number: {receipt_num}")

print("\n" + "=" * 60)

# Get a sample transaction for testing
txn = Transaction.objects.select_related('company', 'client', 'allocation__estate').first()
if txn:
    print(f"\n📄 Sample Transaction for PDF Test:")
    print(f"   Transaction ID: {txn.id}")
    print(f"   Reference: {txn.reference_code}")
    print(f"   Client: {txn.client.full_name}")
    print(f"   Amount: ₦{txn.total_amount:,.2f}")
    print(f"   Company: {txn.company.company_name}")
    
    print(f"\n✅ Ready to test PDF generation!")
    print(f"   URL: /receipt/{txn.reference_code}/?download=true")
else:
    print("\n⚠️  No transactions found for testing")

print("=" * 60)
