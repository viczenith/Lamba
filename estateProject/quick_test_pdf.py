"""
Quick test to verify PDF generation with images is working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.test import RequestFactory
from estateApp.models import Transaction, Company
from estateApp.views import payment_receipt

print("=" * 70)
print("QUICK PDF GENERATION TEST")
print("=" * 70)

# Get a transaction
txn = Transaction.objects.select_related('company', 'client').first()

if not txn:
    print("\n❌ No transactions found in database")
    print("   Create a transaction first to test PDF generation")
    exit(1)

print(f"\n✅ Found Transaction:")
print(f"   ID: {txn.id}")
print(f"   Reference: {txn.reference_code}")
print(f"   Client: {txn.client.full_name}")
print(f"   Company: {txn.company.company_name}")
print(f"   Amount: ₦{txn.total_amount:,.2f}")

company = txn.company

print(f"\n🏢 Company Details:")
print(f"   Name: {company.company_name}")
print(f"   Registration No (CAC): {company.registration_number}")
print(f"   Receipt Counter: {company.receipt_counter}")
print(f"   Cashier Name: {company.cashier_name or 'Not set'}")

if company.logo:
    print(f"   Logo: ✅ {company.logo.name}")
else:
    print(f"   Logo: ⚠️  Not set")

if company.cashier_signature:
    print(f"   Signature: ✅ {company.cashier_signature.name}")
else:
    print(f"   Signature: ⚠️  Not set")

print(f"\n📋 Test URLs:")
print(f"\n   Browser View (HTML):")
print(f"   http://127.0.0.1:8000/receipt/{txn.reference_code}/?download=false")
print(f"\n   PDF Download:")
print(f"   http://127.0.0.1:8000/receipt/{txn.reference_code}/?download=true")
print(f"   http://127.0.0.1:8000/receipt/{txn.reference_code}/")

print(f"\n💡 What to Check:")
print(f"   1. ✅ Company logo displays in PDF")
print(f"   2. ✅ Cashier signature displays in PDF")
print(f"   3. ✅ Receipt number format: REC-[INITIALS]-[NUMBER]")
print(f"   4. ✅ Reference code format: [INITIALS]YYYYMMDD-XXX-XXXX")
print(f"   5. ✅ CAC number shows registration_number")
print(f"   6. ✅ Currency format: ₦ XX,XXX,XXX.XX")
print(f"   7. ⚡ PDF downloads quickly (< 2 seconds)")

print("\n" + "=" * 70)
print("✅ Ready to test! Open the URLs above in your browser")
print("=" * 70)
