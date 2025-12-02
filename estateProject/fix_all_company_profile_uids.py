import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    ClientUser, MarketerUser, Company, 
    ClientMarketerAssignment, MarketerAffiliation,
    CompanyClientProfile, CompanyMarketerProfile
)
from django.db.models import Max

print("=" * 100)
print("REGENERATING ALL COMPANY PROFILE UIDs (INCLUDING AFFILIATIONS)")
print("=" * 100)

# For each company, regenerate UIDs for ALL associated clients/marketers
companies = Company.objects.all()

for company in companies:
    print(f"\n{'='*100}")
    print(f"COMPANY: {company.company_name}")
    print(f"{'='*100}")
    
    # Get prefix
    prefix = company.company_name[:3].upper()
    
    # ========== CLIENTS ==========
    print(f"\n▶ REGENERATING CLIENT UIDs:")
    
    # Get all clients: direct + affiliated
    direct_client_ids = set(ClientUser.objects.filter(company_profile=company).values_list('id', flat=True))
    affiliated_client_ids = set(ClientMarketerAssignment.objects.filter(company=company).values_list('client_id', flat=True))
    all_client_ids = direct_client_ids | affiliated_client_ids
    
    # Get max existing ID from CompanyClientProfile
    max_existing = CompanyClientProfile.objects.filter(company=company).aggregate(Max('company_client_id'))['company_client_id__max'] or 0
    
    next_id = max_existing + 1
    
    for client_id in sorted(all_client_ids):
        client = ClientUser.objects.get(id=client_id)
        
        # Create or update CompanyClientProfile
        profile, created = CompanyClientProfile.objects.get_or_create(
            client=client,
            company=company,
            defaults={
                'company_client_id': next_id,
                'company_client_uid': f"{prefix}CLT{next_id:03d}"
            }
        )
        
        if created:
            print(f"  ✓ CREATED: {client.full_name:30} | ID: {profile.company_client_id} | UID: {profile.company_client_uid}")
            next_id += 1
        else:
            old_uid = profile.company_client_uid
            # Update if ID changed
            if profile.company_client_id != next_id:
                profile.company_client_id = next_id
                profile.company_client_uid = f"{prefix}CLT{next_id:03d}"
                profile.save()
                print(f"  ✓ UPDATED: {client.full_name:30} | OLD UID: {old_uid} | NEW UID: {profile.company_client_uid}")
                next_id += 1
            else:
                print(f"  ✓ VERIFIED: {client.full_name:30} | UID: {profile.company_client_uid}")
    
    # ========== MARKETERS ==========
    print(f"\n▶ REGENERATING MARKETER UIDs:")
    
    # Get all marketers: direct + affiliated
    direct_marketer_ids = set(MarketerUser.objects.filter(company_profile=company).values_list('id', flat=True))
    affiliated_marketer_ids = set(MarketerAffiliation.objects.filter(company=company).values_list('marketer_id', flat=True))
    all_marketer_ids = direct_marketer_ids | affiliated_marketer_ids
    
    # Get max existing ID from CompanyMarketerProfile
    max_existing_m = CompanyMarketerProfile.objects.filter(company=company).aggregate(Max('company_marketer_id'))['company_marketer_id__max'] or 0
    
    next_id_m = max_existing_m + 1
    
    for marketer_id in sorted(all_marketer_ids):
        marketer = MarketerUser.objects.get(id=marketer_id)
        
        # Create or update CompanyMarketerProfile
        profile, created = CompanyMarketerProfile.objects.get_or_create(
            marketer=marketer,
            company=company,
            defaults={
                'company_marketer_id': next_id_m,
                'company_marketer_uid': f"{prefix}MKT{next_id_m:03d}"
            }
        )
        
        if created:
            print(f"  ✓ CREATED: {marketer.full_name:30} | ID: {profile.company_marketer_id} | UID: {profile.company_marketer_uid}")
            next_id_m += 1
        else:
            old_uid = profile.company_marketer_uid
            # Update if ID changed
            if profile.company_marketer_id != next_id_m:
                profile.company_marketer_id = next_id_m
                profile.company_marketer_uid = f"{prefix}MKT{next_id_m:03d}"
                profile.save()
                print(f"  ✓ UPDATED: {marketer.full_name:30} | OLD UID: {old_uid} | NEW UID: {profile.company_marketer_uid}")
                next_id_m += 1
            else:
                print(f"  ✓ VERIFIED: {marketer.full_name:30} | UID: {profile.company_marketer_uid}")

print("\n" + "=" * 100)
print("VERIFICATION - ALL COMPANY PROFILE UIDs")
print("=" * 100)

for company in companies:
    print(f"\n{company.company_name}:")
    
    # Client profiles
    client_profiles = CompanyClientProfile.objects.filter(company=company).order_by('company_client_id')
    if client_profiles.exists():
        print(f"  Clients:")
        for p in client_profiles:
            print(f"    ✓ {p.company_client_uid:15} - {p.client.full_name}")
    
    # Marketer profiles
    marketer_profiles = CompanyMarketerProfile.objects.filter(company=company).order_by('company_marketer_id')
    if marketer_profiles.exists():
        print(f"  Marketers:")
        for p in marketer_profiles:
            print(f"    ✓ {p.company_marketer_uid:15} - {p.marketer.full_name}")

print("\n" + "=" * 100)
print("✅ DONE - ALL UIDs REGENERATED!")
print("=" * 100)
