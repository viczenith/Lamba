#!/usr/bin/env python
"""
Security Test Script: Verify cross-company data leakage prevention
Tests the client_profile and admin_marketer_profile views for proper company isolation.

Run with: python manage.py shell < test_data_leakage.py
Or: ./test_data_leakage.py (after adding shebang and making executable)
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RealEstateMSApp.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from estateApp.models import (
    Company, ClientUser, MarketerUser, 
    ClientMarketerAssignment, MarketerAffiliation,
    PlotAllocation, Estate, Transaction
)
from django.urls import reverse
from decimal import Decimal

User = get_user_model()


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_client_profile_data_leakage():
    """
    Test 1: Verify client_profile view prevents cross-company data leakage
    """
    print_section("TEST 1: Client Profile Data Leakage Prevention")
    
    # Get two different companies
    companies = list(Company.objects.all()[:2])
    if len(companies) < 2:
        print("❌ SKIP: Need at least 2 companies in database")
        return False
    
    company_a, company_b = companies[0], companies[1]
    print(f"\n📊 Testing with:")
    print(f"   Company A: {company_a.company_name} ({company_a.slug})")
    print(f"   Company B: {company_b.company_name} ({company_b.slug})")
    
    # Get clients from each company
    client_a = ClientUser.objects.filter(company_profile=company_a).first()
    client_b = ClientUser.objects.filter(company_profile=company_b).first()
    
    if not client_a or not client_b:
        print("❌ SKIP: Need clients in both companies")
        return False
    
    print(f"\n👤 Test Clients:")
    print(f"   Client A: {client_a.full_name} (ID: {client_a.id}, Company: {company_a.slug})")
    print(f"   Client B: {client_b.full_name} (ID: {client_b.id}, Company: {company_b.slug})")
    
    # Get an admin user from company A
    admin_a = User.objects.filter(role='admin', company_profile=company_a).first()
    if not admin_a:
        print("❌ SKIP: Need admin user in Company A")
        return False
    
    print(f"\n🔑 Admin User: {admin_a.full_name} (Company: {company_a.slug})")
    
    client = Client()
    client.force_login(admin_a)
    
    # TEST 1a: Access client_a's profile with correct company - SHOULD SUCCEED
    print(f"\n✅ TEST 1a: Access Client A's profile from Company A")
    response = client.get(f'/client_profile/{client_a.id}/?company={company_a.slug}')
    if response.status_code == 200:
        print(f"   ✅ PASS: Status {response.status_code} - Profile accessible")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Expected 200")
        return False
    
    # TEST 1b: Access client_b's profile with company B slug - SHOULD FAIL (user is from company A)
    print(f"\n✅ TEST 1b: Try to access Client B's profile from Company B (cross-company attack)")
    response = client.get(f'/client_profile/{client_b.id}/?company={company_b.slug}')
    if response.status_code in [403, 404]:
        print(f"   ✅ PASS: Status {response.status_code} - Access denied (cross-company)")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Should be 403/404, got {response.status_code}")
        return False
    
    # TEST 1c: Access client_b's profile without company parameter - SHOULD FAIL
    print(f"\n✅ TEST 1c: Try to access Client B without company parameter")
    response = client.get(f'/client_profile/{client_b.id}/')
    if response.status_code in [404, 403]:
        print(f"   ✅ PASS: Status {response.status_code} - Requires company context")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Should require company context")
        return False
    
    # TEST 1d: Using slug-based URL with company parameter
    from estateApp.views import generate_name_slug
    slug_a = generate_name_slug(client_a.full_name)
    slug_b = generate_name_slug(client_b.full_name)
    
    print(f"\n✅ TEST 1d: Access via slug-based URL: /{slug_a}.client-profile?company={company_a.slug}")
    response = client.get(f'/{slug_a}.client-profile/?company={company_a.slug}')
    if response.status_code == 200:
        print(f"   ✅ PASS: Status {response.status_code} - Slug-based URL works")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Slug-based URL failed")
        return False
    
    # TEST 1e: Try cross-company access via slug
    print(f"\n✅ TEST 1e: Try cross-company access via slug: /{slug_b}.client-profile?company={company_b.slug}")
    response = client.get(f'/{slug_b}.client-profile/?company={company_b.slug}')
    if response.status_code in [403, 404]:
        print(f"   ✅ PASS: Status {response.status_code} - Cross-company slug access denied")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Should be 403/404")
        return False
    
    print("\n✅ CLIENT PROFILE SECURITY TESTS: ALL PASSED")
    return True


def test_marketer_profile_data_leakage():
    """
    Test 2: Verify admin_marketer_profile view prevents cross-company data leakage
    """
    print_section("TEST 2: Marketer Profile Data Leakage Prevention")
    
    # Get two different companies
    companies = list(Company.objects.all()[:2])
    if len(companies) < 2:
        print("❌ SKIP: Need at least 2 companies in database")
        return False
    
    company_a, company_b = companies[0], companies[1]
    print(f"\n📊 Testing with:")
    print(f"   Company A: {company_a.company_name} ({company_a.slug})")
    print(f"   Company B: {company_b.company_name} ({company_b.slug})")
    
    # Get marketers from each company
    marketer_a = MarketerUser.objects.filter(company_profile=company_a).first()
    marketer_b = MarketerUser.objects.filter(company_profile=company_b).first()
    
    if not marketer_a or not marketer_b:
        print("❌ SKIP: Need marketers in both companies")
        return False
    
    print(f"\n👤 Test Marketers:")
    print(f"   Marketer A: {marketer_a.full_name} (ID: {marketer_a.id}, Company: {company_a.slug})")
    print(f"   Marketer B: {marketer_b.full_name} (ID: {marketer_b.id}, Company: {company_b.slug})")
    
    # Get an admin user from company A
    admin_a = User.objects.filter(role='admin', company_profile=company_a).first()
    if not admin_a:
        print("❌ SKIP: Need admin user in Company A")
        return False
    
    print(f"\n🔑 Admin User: {admin_a.full_name} (Company: {company_a.slug})")
    
    client = Client()
    client.force_login(admin_a)
    
    # TEST 2a: Access marketer_a's profile with correct company - SHOULD SUCCEED
    print(f"\n✅ TEST 2a: Access Marketer A's profile from Company A")
    response = client.get(f'/admin-marketer/{marketer_a.id}/?company={company_a.slug}')
    if response.status_code == 200:
        print(f"   ✅ PASS: Status {response.status_code} - Profile accessible")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Expected 200")
        return False
    
    # TEST 2b: Access marketer_b's profile with company B slug - SHOULD FAIL
    print(f"\n✅ TEST 2b: Try to access Marketer B's profile from Company B (cross-company attack)")
    response = client.get(f'/admin-marketer/{marketer_b.id}/?company={company_b.slug}')
    if response.status_code in [403, 404]:
        print(f"   ✅ PASS: Status {response.status_code} - Access denied (cross-company)")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Should be 403/404")
        return False
    
    # TEST 2c: Access marketer_b without company parameter - SHOULD FAIL
    print(f"\n✅ TEST 2c: Try to access Marketer B without company parameter")
    response = client.get(f'/admin-marketer/{marketer_b.id}/')
    if response.status_code in [404, 403]:
        print(f"   ✅ PASS: Status {response.status_code} - Requires company context")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Should require company context")
        return False
    
    # TEST 2d: Using slug-based URL with company parameter
    from estateApp.views import generate_name_slug
    slug_a = generate_name_slug(marketer_a.full_name)
    slug_b = generate_name_slug(marketer_b.full_name)
    
    print(f"\n✅ TEST 2d: Access via slug-based URL: /{slug_a}.marketer-profile?company={company_a.slug}")
    response = client.get(f'/{slug_a}.marketer-profile/?company={company_a.slug}')
    if response.status_code == 200:
        print(f"   ✅ PASS: Status {response.status_code} - Slug-based URL works")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Slug-based URL failed")
        return False
    
    # TEST 2e: Try cross-company access via slug
    print(f"\n✅ TEST 2e: Try cross-company access via slug: /{slug_b}.marketer-profile?company={company_b.slug}")
    response = client.get(f'/{slug_b}.marketer-profile/?company={company_b.slug}')
    if response.status_code in [403, 404]:
        print(f"   ✅ PASS: Status {response.status_code} - Cross-company slug access denied")
    else:
        print(f"   ❌ FAIL: Status {response.status_code} - Should be 403/404")
        return False
    
    print("\n✅ MARKETER PROFILE SECURITY TESTS: ALL PASSED")
    return True


def test_transaction_isolation():
    """
    Test 3: Verify that transactions are scoped correctly to prevent data leakage
    """
    print_section("TEST 3: Transaction Data Leakage Prevention")
    
    companies = list(Company.objects.all()[:2])
    if len(companies) < 2:
        print("❌ SKIP: Need at least 2 companies in database")
        return False
    
    company_a, company_b = companies[0], companies[1]
    
    # Check transaction counts
    txn_a = Transaction.objects.filter(company=company_a).count()
    txn_b = Transaction.objects.filter(company=company_b).count()
    
    print(f"\n💼 Company Transaction Counts:")
    print(f"   Company A ({company_a.slug}): {txn_a} transactions")
    print(f"   Company B ({company_b.slug}): {txn_b} transactions")
    
    # Verify transactions are properly scoped
    unscoped_txns = Transaction.objects.filter(company__isnull=True).count()
    if unscoped_txns > 0:
        print(f"⚠️  WARNING: {unscoped_txns} transactions have no company scope (potential data leakage)")
        return False
    else:
        print(f"✅ All transactions are properly scoped to a company")
    
    return True


def run_all_tests():
    """Run all security tests."""
    print_section("🔒 CROSS-COMPANY DATA LEAKAGE SECURITY TESTS")
    
    results = []
    
    # Run all tests
    results.append(("Client Profile Data Leakage", test_client_profile_data_leakage()))
    results.append(("Marketer Profile Data Leakage", test_marketer_profile_data_leakage()))
    results.append(("Transaction Isolation", test_transaction_isolation()))
    
    # Summary
    print_section("📊 TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL SECURITY TESTS PASSED! Data leakage prevention is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Security issues detected!")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
