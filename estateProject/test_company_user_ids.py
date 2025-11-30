"""
Test script to verify the company-specific user ID system.
This tests that:
1. New users get company-specific IDs
2. Existing users get new IDs when added to new companies
3. No ID conflicts occur across companies
"""
import os
import sys
import django

# Find the correct settings module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    Company, MarketerUser, ClientUser, MarketerAffiliation,
    CompanyMarketerProfile, CompanyClientProfile, CustomUser
)
from django.db import transaction


def test_marketer_ids_across_companies():
    """Test that a marketer gets different IDs in different companies."""
    print("\n" + "="*80)
    print("TEST 1: Marketer IDs Across Companies")
    print("="*80)
    
    try:
        # Get or create test marketer
        marketer_email = "test_marketer_ids@example.com"
        marketer, created = MarketerUser.objects.get_or_create(
            email=marketer_email,
            defaults={
                'full_name': 'Test Marketer For IDs',
                'phone': '08012345678',
            }
        )
        
        # Get test companies
        companies = Company.objects.all()[:2]
        if len(companies) < 2:
            print("❌ Need at least 2 companies for this test")
            return False
        
        company1, company2 = companies
        
        print(f"\n👤 Marketer: {marketer.full_name} ({marketer_email})")
        print(f"\n🏢 Company 1: {company1.company_name}")
        print(f"🏢 Company 2: {company2.company_name}")
        
        # Assign marketer to company 1 via affiliation
        print(f"\n📌 Creating affiliation with {company1.company_name}...")
        aff1, created1 = MarketerAffiliation.objects.get_or_create(
            marketer=marketer,
            company=company1
        )
        print(f"   {'✓ Created' if created1 else '✓ Already exists'}")
        
        # Check profile for company 1
        profile1 = company1.get_marketer_profile(marketer)
        if profile1:
            print(f"   ✓ Profile ID: {profile1.company_marketer_id}")
            print(f"   ✓ Profile UID: {profile1.company_marketer_uid}")
        else:
            print(f"   ❌ No profile found for company 1")
            return False
        
        # Assign marketer to company 2 via affiliation
        print(f"\n📌 Creating affiliation with {company2.company_name}...")
        aff2, created2 = MarketerAffiliation.objects.get_or_create(
            marketer=marketer,
            company=company2
        )
        print(f"   {'✓ Created' if created2 else '✓ Already exists'}")
        
        # Check profile for company 2
        profile2 = company2.get_marketer_profile(marketer)
        if profile2:
            print(f"   ✓ Profile ID: {profile2.company_marketer_id}")
            print(f"   ✓ Profile UID: {profile2.company_marketer_uid}")
        else:
            print(f"   ❌ No profile found for company 2")
            return False
        
        # Verify IDs are different
        if profile1.company_marketer_uid != profile2.company_marketer_uid:
            print(f"\n✅ SUCCESS: Marketer has different UIDs in different companies")
            print(f"   {company1.company_name}: {profile1.company_marketer_uid}")
            print(f"   {company2.company_name}: {profile2.company_marketer_uid}")
            return True
        else:
            print(f"\n❌ FAILED: UIDs are the same in different companies")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_client_ids_in_company():
    """Test that clients get company-specific IDs."""
    print("\n" + "="*80)
    print("TEST 2: Client IDs in Company")
    print("="*80)
    
    try:
        # Get test company
        company = Company.objects.first()
        if not company:
            print("❌ No companies found")
            return False
        
        print(f"\n🏢 Company: {company.company_name}")
        
        # Create multiple test clients
        test_clients = []
        for i in range(3):
            client_email = f"test_client_{i}_{company.id}@example.com"
            client, created = ClientUser.objects.get_or_create(
                email=client_email,
                company_profile=company,
                defaults={
                    'full_name': f'Test Client {i}',
                    'phone': f'0801234567{i}',
                }
            )
            test_clients.append((client, created))
        
        print(f"\n👥 Created/Retrieved {len(test_clients)} test clients")
        
        # Check each client's profile
        all_have_profiles = True
        profiles_data = []
        
        for idx, (client, created) in enumerate(test_clients):
            profile = company.get_client_profile(client)
            if profile:
                print(f"\n   Client {idx+1}: {client.full_name}")
                print(f"     ✓ ID: {profile.company_client_id}")
                print(f"     ✓ UID: {profile.company_client_uid}")
                profiles_data.append(profile)
            else:
                print(f"\n   Client {idx+1}: {client.full_name}")
                print(f"     ❌ No profile found")
                all_have_profiles = False
        
        if not all_have_profiles:
            return False
        
        # Verify all IDs are unique
        uids = [p.company_client_uid for p in profiles_data]
        ids = [p.company_client_id for p in profiles_data]
        
        if len(uids) == len(set(uids)) and len(ids) == len(set(ids)):
            print(f"\n✅ SUCCESS: All clients have unique IDs in the company")
            return True
        else:
            print(f"\n❌ FAILED: Duplicate IDs detected")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_lookup_functions():
    """Test the lookup functions on Company model."""
    print("\n" + "="*80)
    print("TEST 3: Lookup Functions")
    print("="*80)
    
    try:
        company = Company.objects.first()
        if not company:
            print("❌ No companies found")
            return False
        
        print(f"\n🏢 Company: {company.company_name}")
        
        # Get first marketer profile
        marketer_profile = company.marketer_profiles.first()
        if not marketer_profile:
            print("❌ No marketer profiles found in this company")
            return False
        
        print(f"\n🔍 Testing lookups for marketer: {marketer_profile.marketer.full_name}")
        
        # Test get_marketer_by_company_id
        print(f"\n   Testing get_marketer_by_company_id({marketer_profile.company_marketer_id})")
        found_by_id = company.get_marketer_by_company_id(marketer_profile.company_marketer_id)
        if found_by_id and found_by_id.id == marketer_profile.marketer.id:
            print(f"   ✓ Found: {found_by_id.full_name}")
        else:
            print(f"   ❌ Not found by ID")
            return False
        
        # Test get_marketer_by_company_uid
        print(f"\n   Testing get_marketer_by_company_uid('{marketer_profile.company_marketer_uid}')")
        found_by_uid = company.get_marketer_by_company_uid(marketer_profile.company_marketer_uid)
        if found_by_uid and found_by_uid.id == marketer_profile.marketer.id:
            print(f"   ✓ Found: {found_by_uid.full_name}")
        else:
            print(f"   ❌ Not found by UID")
            return False
        
        # Get first client profile
        client_profile = company.client_profiles.first()
        if not client_profile:
            print("\n❌ No client profiles found in this company")
            return False
        
        print(f"\n🔍 Testing lookups for client: {client_profile.client.full_name}")
        
        # Test get_client_by_company_id
        print(f"\n   Testing get_client_by_company_id({client_profile.company_client_id})")
        found_client_by_id = company.get_client_by_company_id(client_profile.company_client_id)
        if found_client_by_id and found_client_by_id.id == client_profile.client.id:
            print(f"   ✓ Found: {found_client_by_id.full_name}")
        else:
            print(f"   ❌ Not found by ID")
            return False
        
        # Test get_client_by_company_uid
        print(f"\n   Testing get_client_by_company_uid('{client_profile.company_client_uid}')")
        found_client_by_uid = company.get_client_by_company_uid(client_profile.company_client_uid)
        if found_client_by_uid and found_client_by_uid.id == client_profile.client.id:
            print(f"   ✓ Found: {found_client_by_uid.full_name}")
        else:
            print(f"   ❌ Not found by UID")
            return False
        
        print(f"\n✅ SUCCESS: All lookup functions work correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "█"*80)
    print("█ COMPANY-SPECIFIC USER ID SYSTEM - TEST SUITE")
    print("█"*80)
    
    results = []
    
    # Run tests
    results.append(("Test 1: Marketer IDs Across Companies", test_marketer_ids_across_companies()))
    results.append(("Test 2: Client IDs in Company", test_client_ids_in_company()))
    results.append(("Test 3: Lookup Functions", test_lookup_functions()))
    
    # Print summary
    print("\n" + "█"*80)
    print("█ TEST SUMMARY")
    print("█"*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
