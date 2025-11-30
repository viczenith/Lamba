"""
Find and fix users in Lamba Real Homes with wrong LPL IDs
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, MarketerUser, ClientUser, CompanyMarketerProfile, CompanyClientProfile
from django.db.models import Q


def find_and_fix_lrh_users():
    """Find users in Lamba Real Homes with wrong LPL IDs"""
    print("\n" + "="*80)
    print("FINDING USERS IN LAMBA REAL HOMES WITH WRONG IDs")
    print("="*80)
    
    try:
        # Get Lamba Real Homes company
        lrh = Company.objects.get(company_name__icontains='Lamba Real Homes')
        lpl = Company.objects.get(company_name__icontains='Lamba Property Limited')
        
        print(f"\n🏢 Target Company: {lrh.company_name} (prefix: {lrh._company_prefix()})")
        print(f"🔍 Looking for marketers with LPL UIDs in {lrh.company_name}...")
        
        # Find marketer profiles in LRH with LPL UIDs
        wrong_marketer_profiles = CompanyMarketerProfile.objects.filter(
            company=lrh,
            company_marketer_uid__startswith='LPL'
        )
        
        print(f"\n📊 Found {wrong_marketer_profiles.count()} marketer profiles with wrong UIDs in {lrh.company_name}")
        
        fixed_count = 0
        
        for profile in wrong_marketer_profiles:
            print(f"\n   Current: {profile.marketer.full_name}")
            print(f"     ❌ Wrong UID: {profile.company_marketer_uid}")
            print(f"     ❌ Wrong ID: {profile.company_marketer_id}")
            
            # Get next available ID for LRH
            from django.db.models import Max
            max_id_result = CompanyMarketerProfile.objects.filter(
                company=lrh,
                company_marketer_uid__startswith='LRH'
            ).aggregate(max_val=Max('company_marketer_id'))
            
            next_id = (max_id_result['max_val'] or 0) + 1
            new_uid = f"LRHMKT{next_id:03d}"
            
            # Update profile
            profile.company_marketer_id = next_id
            profile.company_marketer_uid = new_uid
            profile.save()
            
            print(f"     ✓ New UID: {new_uid}")
            print(f"     ✓ New ID: {next_id}")
            fixed_count += 1
        
        # Find client profiles in LRH with LPL UIDs
        wrong_client_profiles = CompanyClientProfile.objects.filter(
            company=lrh,
            company_client_uid__startswith='LPL'
        )
        
        print(f"\n📊 Found {wrong_client_profiles.count()} client profiles with wrong UIDs in {lrh.company_name}")
        
        for profile in wrong_client_profiles:
            print(f"\n   Current: {profile.client.full_name}")
            print(f"     ❌ Wrong UID: {profile.company_client_uid}")
            print(f"     ❌ Wrong ID: {profile.company_client_id}")
            
            # Get next available ID for LRH
            from django.db.models import Max
            max_id_result = CompanyClientProfile.objects.filter(
                company=lrh,
                company_client_uid__startswith='LRH'
            ).aggregate(max_val=Max('company_client_id'))
            
            next_id = (max_id_result['max_val'] or 0) + 1
            new_uid = f"LRHCLT{next_id:03d}"
            
            # Update profile
            profile.company_client_id = next_id
            profile.company_client_uid = new_uid
            profile.save()
            
            print(f"     ✓ New UID: {new_uid}")
            print(f"     ✓ New ID: {next_id}")
            fixed_count += 1
        
        print(f"\n✅ Fixed {fixed_count} profiles with correct LRH prefix!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_fix():
    """Verify all profiles in LRH have correct prefix"""
    print("\n" + "="*80)
    print("VERIFYING ALL LRH PROFILES HAVE CORRECT PREFIX")
    print("="*80)
    
    try:
        lrh = Company.objects.get(company_name__icontains='Lamba Real Homes')
        
        print(f"\n🏢 {lrh.company_name}:")
        
        # Check marketers
        marketer_profiles = CompanyMarketerProfile.objects.filter(company=lrh)
        print(f"\n📊 Marketer Profiles ({marketer_profiles.count()}):")
        
        wrong_count = 0
        for profile in marketer_profiles:
            if profile.company_marketer_uid.startswith('LRH'):
                print(f"   ✓ {profile.marketer.full_name}: {profile.company_marketer_uid}")
            else:
                print(f"   ❌ {profile.marketer.full_name}: {profile.company_marketer_uid} (WRONG PREFIX!)")
                wrong_count += 1
        
        # Check clients
        client_profiles = CompanyClientProfile.objects.filter(company=lrh)
        print(f"\n📊 Client Profiles ({client_profiles.count()}):")
        
        for profile in client_profiles:
            if profile.company_client_uid.startswith('LRH'):
                print(f"   ✓ {profile.client.full_name}: {profile.company_client_uid}")
            else:
                print(f"   ❌ {profile.client.full_name}: {profile.company_client_uid} (WRONG PREFIX!)")
                wrong_count += 1
        
        if wrong_count == 0:
            print(f"\n✅ All profiles in {lrh.company_name} have correct LRH prefix!")
            return True
        else:
            print(f"\n⚠️  Found {wrong_count} profiles with wrong prefix")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "█"*80)
    print("█ FIXING LAMBA REAL HOMES IDs")
    print("█ Converting all LPL IDs to LRH IDs in Lamba Real Homes")
    print("█"*80)
    
    success = find_and_fix_lrh_users()
    if success:
        verify_fix()
    
    return success


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
