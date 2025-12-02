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
print("COMPREHENSIVE DATABASE AUDIT")
print("=" * 100)

# Get all companies
companies = Company.objects.all()

for company in companies:
    print(f"\n{'='*100}")
    print(f"COMPANY: {company.company_name} (ID: {company.id}, Slug: {company.slug})")
    print(f"{'='*100}")
    
    # Direct clients (company_profile)
    print(f"\n▶ DIRECT CLIENTS (company_profile={company.id}):")
    direct_clients = ClientUser.objects.filter(company_profile=company)
    if direct_clients.exists():
        for client in direct_clients:
            print(f"  ✓ {client.id:4} | {client.full_name:30} | UID: {client.company_client_uid}")
    else:
        print(f"  (none)")
    
    # Affiliated clients via ClientMarketerAssignment
    print(f"\n▶ AFFILIATED CLIENTS (via ClientMarketerAssignment):")
    affiliated_client_ids = ClientMarketerAssignment.objects.filter(company=company).values_list('client_id', flat=True).distinct()
    if affiliated_client_ids.exists():
        for client_id in affiliated_client_ids:
            client = ClientUser.objects.get(id=client_id)
            assignment = ClientMarketerAssignment.objects.get(client_id=client_id, company=company)
            print(f"  ✓ {client.id:4} | {client.full_name:30} | via {assignment.marketer.full_name if assignment.marketer else 'N/A'}")
    else:
        print(f"  (none)")
    
    # CompanyClientProfile records
    print(f"\n▶ COMPANY CLIENT PROFILES (company={company.id}):")
    profiles = CompanyClientProfile.objects.filter(company=company)
    if profiles.exists():
        for profile in profiles:
            print(f"  ✓ Client: {profile.client.full_name:30} | ID: {profile.company_client_id} | UID: {profile.company_client_uid}")
    else:
        print(f"  (none)")
    
    # Direct marketers (company_profile)
    print(f"\n▶ DIRECT MARKETERS (company_profile={company.id}):")
    direct_marketers = MarketerUser.objects.filter(company_profile=company)
    if direct_marketers.exists():
        for marketer in direct_marketers:
            print(f"  ✓ {marketer.id:4} | {marketer.full_name:30} | UID: {marketer.company_marketer_uid}")
    else:
        print(f"  (none)")
    
    # Affiliated marketers via MarketerAffiliation
    print(f"\n▶ AFFILIATED MARKETERS (via MarketerAffiliation):")
    affiliations = MarketerAffiliation.objects.filter(company=company)
    if affiliations.exists():
        for aff in affiliations:
            print(f"  ✓ {aff.marketer.id:4} | {aff.marketer.full_name:30} | Status: {aff.status} | Tier: {aff.commission_tier}")
    else:
        print(f"  (none)")
    
    # CompanyMarketerProfile records
    print(f"\n▶ COMPANY MARKETER PROFILES (company={company.id}):")
    mprofiles = CompanyMarketerProfile.objects.filter(company=company)
    if mprofiles.exists():
        for profile in mprofiles:
            print(f"  ✓ Marketer: {profile.marketer.full_name:30} | ID: {profile.company_marketer_id} | UID: {profile.company_marketer_uid}")
    else:
        print(f"  (none)")

print("\n" + "=" * 100)
print("SEARCHING FOR LRHCLT005 AND LRHCLT005 PATTERNS")
print("=" * 100)

# Search for any UID with LRH pattern
print("\nUIDs with 'LRH' pattern:")
lrh_clients = ClientUser.objects.filter(company_client_uid__icontains='LRH')
lrh_marketers = MarketerUser.objects.filter(company_marketer_uid__icontains='LRH')

if lrh_clients.exists():
    for c in lrh_clients:
        print(f"  Client UID: {c.company_client_uid} - {c.full_name}")
else:
    print(f"  (no client UIDs with LRH)")

if lrh_marketers.exists():
    for m in lrh_marketers:
        print(f"  Marketer UID: {m.company_marketer_uid} - {m.full_name}")
else:
    print(f"  (no marketer UIDs with LRH)")

# Search in profiles
lrh_client_profiles = CompanyClientProfile.objects.filter(company_client_uid__icontains='LRH')
lrh_marketer_profiles = CompanyMarketerProfile.objects.filter(company_marketer_uid__icontains='LRH')

if lrh_client_profiles.exists():
    print(f"\n  CompanyClientProfile UIDs with LRH:")
    for p in lrh_client_profiles:
        print(f"    {p.company_client_uid} - {p.client.full_name} @ {p.company.company_name}")
else:
    print(f"\n  (no CompanyClientProfile UIDs with LRH)")

if lrh_marketer_profiles.exists():
    print(f"\n  CompanyMarketerProfile UIDs with LRH:")
    for p in lrh_marketer_profiles:
        print(f"    {p.company_marketer_uid} - {p.marketer.full_name} @ {p.company.company_name}")
else:
    print(f"\n  (no CompanyMarketerProfile UIDs with LRH)")

print("\n" + "=" * 100)
