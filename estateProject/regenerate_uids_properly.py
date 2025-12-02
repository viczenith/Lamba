import os
import django
import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    ClientUser, MarketerUser, Company, 
    ClientMarketerAssignment, MarketerAffiliation,
    CompanyClientProfile, CompanyMarketerProfile,
    CompanySequence
)

print("=" * 100)
print("REGENERATING UIDs USING EXISTING LOGIC + CompanySequence")
print("=" * 100)

# Clear company profiles to regenerate
print("\n▶ Clearing existing CompanyClientProfile and CompanyMarketerProfile...")
CompanyClientProfile.objects.all().delete()
CompanyMarketerProfile.objects.all().delete()
print("  ✓ Cleared")

# Clear CompanySequence to restart from 1
print("\n▶ Resetting CompanySequence...")
CompanySequence.objects.all().delete()
print("  ✓ Reset")

companies = Company.objects.all()

for company in companies:
    print(f"\n{'='*100}")
    print(f"COMPANY: {company.company_name}")
    print(f"{'='*100}")
    
    prefix = company._company_prefix()
    print(f"  Prefix: {prefix}")
    
    # ========== CLIENTS ==========
    print(f"\n▶ REGENERATING CLIENT UIDs:")
    
    # Get all clients: direct + affiliated
    direct_client_ids = list(ClientUser.objects.filter(company_profile=company).values_list('id', flat=True))
    affiliated_client_ids = list(ClientMarketerAssignment.objects.filter(company=company).values_list('client_id', flat=True).distinct())
    all_client_ids = sorted(set(direct_client_ids + affiliated_client_ids))
    
    if not all_client_ids:
        print(f"  (no clients)")
    else:
        for client_id in all_client_ids:
            client = ClientUser.objects.get(id=client_id)
            
            # Get next sequential ID using CompanySequence
            seq_id = CompanySequence.get_next(company, 'client')
            
            # Generate UID using the same logic as the model
            new_uid = f"{prefix}CLT{int(seq_id):03d}"
            
            # Check uniqueness (if collision, add company ID)
            if ClientUser.objects.filter(company_client_uid=new_uid).exists() or \
               CompanyClientProfile.objects.filter(company_client_uid=new_uid).exists():
                new_uid = f"{prefix}{company.id}CLT{int(seq_id):03d}"
            
            # Create CompanyClientProfile
            profile, created = CompanyClientProfile.objects.get_or_create(
                client=client,
                company=company,
                defaults={
                    'company_client_id': seq_id,
                    'company_client_uid': new_uid
                }
            )
            
            # Update ClientUser field too
            if not client.company_client_uid or client.company_client_uid != new_uid:
                client.company_client_uid = new_uid
                client.company_client_id = seq_id
                client.save(update_fields=['company_client_uid', 'company_client_id'])
            
            print(f"  ✓ {new_uid:20} - {client.full_name}")
    
    # ========== MARKETERS ==========
    print(f"\n▶ REGENERATING MARKETER UIDs:")
    
    # Get all marketers: direct + affiliated
    direct_marketer_ids = list(MarketerUser.objects.filter(company_profile=company).values_list('id', flat=True))
    affiliated_marketer_ids = list(MarketerAffiliation.objects.filter(company=company).values_list('marketer_id', flat=True).distinct())
    all_marketer_ids = sorted(set(direct_marketer_ids + affiliated_marketer_ids))
    
    if not all_marketer_ids:
        print(f"  (no marketers)")
    else:
        for marketer_id in all_marketer_ids:
            marketer = MarketerUser.objects.get(id=marketer_id)
            
            # Get next sequential ID using CompanySequence
            seq_id = CompanySequence.get_next(company, 'marketer')
            
            # Generate UID using the same logic as the model
            new_uid = f"{prefix}MKT{int(seq_id):03d}"
            
            # Check uniqueness (if collision, add company ID)
            if MarketerUser.objects.filter(company_marketer_uid=new_uid).exists() or \
               CompanyMarketerProfile.objects.filter(company_marketer_uid=new_uid).exists():
                new_uid = f"{prefix}{company.id}MKT{int(seq_id):03d}"
            
            # Create CompanyMarketerProfile
            profile, created = CompanyMarketerProfile.objects.get_or_create(
                marketer=marketer,
                company=company,
                defaults={
                    'company_marketer_id': seq_id,
                    'company_marketer_uid': new_uid
                }
            )
            
            # Update MarketerUser field too
            if not marketer.company_marketer_uid or marketer.company_marketer_uid != new_uid:
                marketer.company_marketer_uid = new_uid
                marketer.company_marketer_id = seq_id
                marketer.save(update_fields=['company_marketer_uid', 'company_marketer_id'])
            
            print(f"  ✓ {new_uid:20} - {marketer.full_name}")

print("\n" + "=" * 100)
print("FINAL VERIFICATION")
print("=" * 100)

for company in companies:
    print(f"\n{company.company_name}:")
    
    # Client profiles
    client_profiles = CompanyClientProfile.objects.filter(company=company).order_by('company_client_id')
    if client_profiles.exists():
        print(f"  Clients:")
        for p in client_profiles:
            print(f"    ✓ {p.company_client_uid:20} - {p.client.full_name}")
    
    # Marketer profiles
    marketer_profiles = CompanyMarketerProfile.objects.filter(company=company).order_by('company_marketer_id')
    if marketer_profiles.exists():
        print(f"  Marketers:")
        for p in marketer_profiles:
            print(f"    ✓ {p.company_marketer_uid:20} - {p.marketer.full_name}")

print("\n" + "=" * 100)
print("✅ ALL UIDs PROPERLY REGENERATED!")
print("=" * 100)
