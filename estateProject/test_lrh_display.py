"""
Test that Lamba Real Homes displays correct LRH IDs (not LPL)
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, CompanyMarketerProfile, CompanyClientProfile


def test_lrh_display_ids():
    """Test that all LRH profiles have correct LRH UIDs"""
    print("\n" + "="*80)
    print("TESTING LRH DISPLAY IDs")
    print("="*80)
    
    try:
        lrh = Company.objects.get(company_name__icontains='Lamba Real Homes')
        lpl = Company.objects.get(company_name__icontains='Lamba Property Limited')
        
        print(f"\n🏢 Lamba Real Homes (prefix: {lrh._company_prefix()})")
        print(f"🏢 Lamba Property Limited (prefix: {lpl._company_prefix()})")
        
        # Check marketer profiles
        print(f"\n📊 Lamba Real Homes Marketer Profiles:")
        lrh_marketer_profiles = CompanyMarketerProfile.objects.filter(company=lrh)
        
        wrong_count = 0
        for profile in lrh_marketer_profiles:
            prefix = profile.company_marketer_uid[:3]
            status = "✓" if prefix == "LRH" else "❌"
            print(f"   {status} {profile.marketer.full_name}: {profile.company_marketer_uid}")
            if prefix != "LRH":
                wrong_count += 1
        
        # Check client profiles
        print(f"\n📊 Lamba Real Homes Client Profiles:")
        lrh_client_profiles = CompanyClientProfile.objects.filter(company=lrh)
        
        for profile in lrh_client_profiles:
            prefix = profile.company_client_uid[:3]
            status = "✓" if prefix == "LRH" else "❌"
            print(f"   {status} {profile.client.full_name}: {profile.company_client_uid}")
            if prefix != "LRH":
                wrong_count += 1
        
        # Comparison: Check LPL profiles to confirm they use LPL prefix
        print(f"\n📊 Lamba Property Limited Marketer Profiles (for comparison):")
        lpl_marketer_profiles = CompanyMarketerProfile.objects.filter(company=lpl)
        
        for profile in lpl_marketer_profiles[:3]:  # Show first 3 only
            prefix = profile.company_marketer_uid[:3]
            print(f"   ✓ {profile.marketer.full_name}: {profile.company_marketer_uid}")
        
        if wrong_count == 0:
            print(f"\n✅ All LRH profiles are correctly showing LRH prefix!")
            return True
        else:
            print(f"\n⚠️ Found {wrong_count} profiles with wrong prefix in LRH")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_lrh_display_ids()
    exit(0 if success else 1)
