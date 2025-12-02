import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    ClientUser, MarketerUser, Company, 
    ClientMarketerAssignment, MarketerAffiliation,
    CompanyClientProfile, CompanyMarketerProfile
)

print("=" * 100)
print("FIXING ALL COMPANY PROFILE UIDs (ENSURING GLOBAL UNIQUENESS)")
print("=" * 100)

companies = Company.objects.all()

# First, clear everything to start fresh
print("\n▶ Clearing all CompanyClientProfile and CompanyMarketerProfile...")
CompanyClientProfile.objects.all().delete()
CompanyMarketerProfile.objects.all().delete()
print("  ✓ Cleared")

for company in companies:
    print(f"\n{'='*100}")
    print(f"COMPANY: {company.company_name} (ID: {company.id})")
    print(f"{'='*100}")
    
    prefix = company.company_name[:3].upper()
    company_id_suffix = f"C{company.id}"  # Add company ID for uniqueness
    
    # ========== CLIENTS ==========
    print(f"\n▶ CREATING CLIENT UIDs:")
    
    # Get all clients: direct + affiliated
    direct_client_ids = list(ClientUser.objects.filter(company_profile=company).values_list('id', flat=True))
    affiliated_client_ids = list(ClientMarketerAssignment.objects.filter(company=company).values_list('client_id', flat=True).distinct())
    all_client_ids = sorted(set(direct_client_ids + affiliated_client_ids))
    
    # Create new profiles with sequential IDs
    for idx, client_id in enumerate(all_client_ids, start=1):
        client = ClientUser.objects.get(id=client_id)
        # Format: PREFIXCLTIDX (e.g., LAMCLT005) - works if no collisions
        # If collisions, add company ID: LAMC1CLT005
        new_uid = f"{prefix}CLT{idx:03d}"
        
        try:
            profile = CompanyClientProfile.objects.create(
                client=client,
                company=company,
                company_client_id=idx,
                company_client_uid=new_uid
            )
            print(f"  ✓ {new_uid:20} - {client.full_name}")
        except Exception as e:
            # If collision, add company ID
            new_uid = f"{prefix}{company_id_suffix}CLT{idx:03d}"
            profile = CompanyClientProfile.objects.create(
                client=client,
                company=company,
                company_client_id=idx,
                company_client_uid=new_uid
            )
            print(f"  ✓ {new_uid:20} - {client.full_name} (with company ID)")
    
    # ========== MARKETERS ==========
    print(f"\n▶ CREATING MARKETER UIDs:")
    
    # Get all marketers: direct + affiliated
    direct_marketer_ids = list(MarketerUser.objects.filter(company_profile=company).values_list('id', flat=True))
    affiliated_marketer_ids = list(MarketerAffiliation.objects.filter(company=company).values_list('marketer_id', flat=True).distinct())
    all_marketer_ids = sorted(set(direct_marketer_ids + affiliated_marketer_ids))
    
    # Create new profiles with sequential IDs
    for idx, marketer_id in enumerate(all_marketer_ids, start=1):
        marketer = MarketerUser.objects.get(id=marketer_id)
        new_uid = f"{prefix}MKT{idx:03d}"
        
        try:
            profile = CompanyMarketerProfile.objects.create(
                marketer=marketer,
                company=company,
                company_marketer_id=idx,
                company_marketer_uid=new_uid
            )
            print(f"  ✓ {new_uid:20} - {marketer.full_name}")
        except Exception as e:
            # If collision, add company ID
            new_uid = f"{prefix}{company_id_suffix}MKT{idx:03d}"
            profile = CompanyMarketerProfile.objects.create(
                marketer=marketer,
                company=company,
                company_marketer_id=idx,
                company_marketer_uid=new_uid
            )
            print(f"  ✓ {new_uid:20} - {marketer.full_name} (with company ID)")

print("\n" + "=" * 100)
print("FINAL VERIFICATION - ALL COMPANY PROFILE UIDs")
print("=" * 100)

for company in companies:
    print(f"\n{company.company_name}:")
    
    # Client profiles
    client_profiles = CompanyClientProfile.objects.filter(company=company).order_by('company_client_id')
    if client_profiles.exists():
        print(f"  Clients:")
        for p in client_profiles:
            print(f"    ✓ {p.company_client_uid:20} - {p.client.full_name}")
    else:
        print(f"  (no clients)")
    
    # Marketer profiles
    marketer_profiles = CompanyMarketerProfile.objects.filter(company=company).order_by('company_marketer_id')
    if marketer_profiles.exists():
        print(f"  Marketers:")
        for p in marketer_profiles:
            print(f"    ✓ {p.company_marketer_uid:20} - {p.marketer.full_name}")
    else:
        print(f"  (no marketers)")

print("\n" + "=" * 100)
print("✅ ALL UIDs FIXED!")
print("=" * 100)

print("\n📝 SAMPLE URLS TO TEST:")
print("\nLamba Real Homes:")
lrh_profiles = CompanyClientProfile.objects.filter(company__slug='lamba-real-homes')
for p in lrh_profiles:
    print(f"  http://127.0.0.1:8000/{p.company_client_uid}.client-profile/?company=lamba-real-homes")
