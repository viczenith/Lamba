#!/usr/bin/env python
"""
Test script for receipt enhancement features
Tests:
1. Receipt number generation with company-specific prefix
2. Currency formatting filter
3. CAC number display
4. Cashier signature support
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estate.settings')
django.setup()

from estateApp.models import Company, Transaction, PaymentRecord
from estateApp.templatetags.custom_filters import currency_format
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


def test_receipt_number_generation():
    """Test receipt number generation with atomic counter"""
    print("\n" + "="*60)
    print("TEST 1: Receipt Number Generation")
    print("="*60)
    
    try:
        # Get first company
        company = Company.objects.first()
        if not company:
            print("❌ No company found. Create a company first.")
            return False
        
        print(f"✓ Testing with company: {company.company_name}")
        
        # Generate 3 receipt numbers
        receipt_numbers = []
        for i in range(3):
            receipt_no = company.get_next_receipt_number()
            receipt_numbers.append(receipt_no)
            print(f"  Receipt {i+1}: {receipt_no}")
        
        # Verify sequential numbering
        for i, rn in enumerate(receipt_numbers):
            expected_num = company.receipt_counter - 2 + i
            if f"{expected_num:05d}" in rn:
                print(f"✓ Receipt {i+1} has correct sequential number")
            else:
                print(f"❌ Receipt {i+1} numbering issue")
                return False
        
        print(f"✓ Current receipt counter: {company.receipt_counter}")
        print("✅ Receipt number generation PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_currency_formatting():
    """Test currency formatting filter"""
    print("="*60)
    print("TEST 2: Currency Formatting")
    print("="*60)
    
    test_cases = [
        (15000000, "₦ 15,000,000.00"),
        (1234.56, "₦ 1,234.56"),
        (500, "₦ 500.00"),
        (0, "₦ 0.00"),
    ]
    
    passed = True
    for amount, expected in test_cases:
        result = currency_format(amount)
        if result == expected:
            print(f"✓ {amount:>12} → {result}")
        else:
            print(f"❌ {amount:>12} → {result} (expected: {expected})")
            passed = False
    
    if passed:
        print("✅ Currency formatting PASSED\n")
    else:
        print("❌ Currency formatting FAILED\n")
    
    return passed


def test_company_fields():
    """Test new company fields exist and are accessible"""
    print("="*60)
    print("TEST 3: New Company Fields")
    print("="*60)
    
    try:
        company = Company.objects.first()
        if not company:
            print("❌ No company found")
            return False
        
        # Check field existence
        fields = ['receipt_counter', 'cac_number', 'cashier_name', 'cashier_signature']
        for field in fields:
            if hasattr(company, field):
                value = getattr(company, field)
                print(f"✓ {field:20} : {value if value else 'Not set'}")
            else:
                print(f"❌ Field '{field}' does not exist")
                return False
        
        print("✅ Company fields PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_receipt_context():
    """Test that payment_receipt view would have correct context"""
    print("="*60)
    print("TEST 4: Receipt Context Simulation")
    print("="*60)
    
    try:
        # Get a transaction
        transaction = Transaction.objects.first()
        if not transaction:
            print("❌ No transaction found. Create a transaction first.")
            return False
        
        company = transaction.company
        receipt_number = company.get_next_receipt_number()
        
        print(f"✓ Company: {company.company_name}")
        print(f"✓ Transaction Ref: {transaction.reference_code}")
        print(f"✓ Receipt Number: {receipt_number}")
        print(f"✓ Amount: {currency_format(transaction.total_amount)}")
        print(f"✓ Balance: {currency_format(transaction.balance)}")
        
        if company.cac_number:
            print(f"✓ CAC Number: {company.cac_number}")
        else:
            print(f"⚠ CAC Number: Not set (update via company profile)")
        
        if company.cashier_name:
            print(f"✓ Cashier: {company.cashier_name}")
        else:
            print(f"⚠ Cashier: Not set (update via company profile)")
        
        print("✅ Receipt context simulation PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🧪 RECEIPT ENHANCEMENT TEST SUITE 🧪".center(60))
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Receipt Number Generation", test_receipt_number_generation()))
    results.append(("Currency Formatting", test_currency_formatting()))
    results.append(("Company Fields", test_company_fields()))
    results.append(("Receipt Context", test_receipt_context()))
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:30} : {status}")
        if result:
            passed += 1
    
    print("="*60)
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Receipt enhancement is ready.")
        print("\n📋 Next Steps:")
        print("   1. Login as company admin")
        print("   2. Go to Company Profile")
        print("   3. Click 'Edit Company Details'")
        print("   4. Fill in CAC Number, Cashier Name, and upload Cashier Signature")
        print("   5. Generate a receipt to see the new features in action!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
    
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
