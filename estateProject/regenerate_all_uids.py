import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company, CompanyClientProfile, CompanyMarketerProfile
from django.db.models import Max

print("=" * 100)
print("COMPREHENSIVE UID REGENERATION FOR ALL COMPANIES")
print("=" * 100)

# Get all companies
companies = Company.objects.all()
print(f"\nFound {companies.count()} companies to process")

# ============================================================================
# PHASE 1: REGENERATE CLIENT UIDs
# ============================================================================
print("\n" + "=" * 100)
print("PHASE 1: REGENERATING CLIENT UIDs")
print("=" * 100)

client_total = 0
client_fixed = 0
client_skipped = 0

for company in companies:
    print(f"\n▶ Company: {company.company_name} (ID: {company.id})")
    
    clients = ClientUser.objects.filter(company_profile=company).all()
    if not clients.exists():
        print(f"  ℹ️  No clients for this company")
        continue
    
    # Get company prefix
    prefix = company.company_name[:3].upper() if company.company_name else "CMP"
    print(f"  Prefix: {prefix}")
    
    for idx, client in enumerate(clients, 1):
        client_total += 1
        
        # If no client_id, assign one based on company max
        if not client.company_client_id:
            maxv = ClientUser.objects.filter(company_profile=company).aggregate(maxv=Max('company_client_id'))
            cur = maxv.get('maxv') or 0
            client.company_client_id = int(cur) + 1
            print(f"    → Assigned client_id {client.company_client_id} to {client.full_name}")
        
        # Generate fresh UID
        new_uid = f"{prefix}CLT{int(client.company_client_id):03d}"
        
        # Check for uniqueness across ALL clients
        existing = ClientUser.objects.filter(company_client_uid=new_uid).exclude(pk=client.pk).exists()
        if existing:
            new_uid = f"{prefix}{company.id}CLT{int(client.company_client_id):03d}"
        
        old_uid = client.company_client_uid
        client.company_client_uid = new_uid
        client.save(update_fields=['company_client_uid'])
        
        status = "✓ REGENERATED" if old_uid != new_uid else "✓ VERIFIED"
        print(f"    {status}: {client.full_name:40} | {old_uid or 'None':20} → {new_uid}")
        
        if old_uid != new_uid:
            client_fixed += 1
        
        # Also update CompanyClientProfile if it exists
        try:
            profile = CompanyClientProfile.objects.get(client=client, company=company)
            profile.company_client_id = client.company_client_id
            profile.company_client_uid = client.company_client_uid
            profile.save(update_fields=['company_client_id', 'company_client_uid'])
        except CompanyClientProfile.DoesNotExist:
            # Create if doesn't exist
            try:
                CompanyClientProfile.objects.create(
                    client=client,
                    company=company,
                    company_client_id=client.company_client_id,
                    company_client_uid=client.company_client_uid
                )
                print(f"      → Created CompanyClientProfile")
            except Exception as e:
                print(f"      ⚠️  Could not create profile: {e}")

print(f"\n✓ CLIENT UIDs: {client_fixed}/{client_total} regenerated")

# ============================================================================
# PHASE 2: REGENERATE MARKETER UIDs
# ============================================================================
print("\n" + "=" * 100)
print("PHASE 2: REGENERATING MARKETER UIDs")
print("=" * 100)

marketer_total = 0
marketer_fixed = 0
marketer_skipped = 0

for company in companies:
    print(f"\n▶ Company: {company.company_name} (ID: {company.id})")
    
    marketers = MarketerUser.objects.filter(company_profile=company).all()
    if not marketers.exists():
        print(f"  ℹ️  No marketers for this company")
        continue
    
    # Get company prefix
    prefix = company.company_name[:3].upper() if company.company_name else "CMP"
    print(f"  Prefix: {prefix}")
    
    for idx, marketer in enumerate(marketers, 1):
        marketer_total += 1
        
        # If no marketer_id, assign one based on company max
        if not marketer.company_marketer_id:
            maxv = MarketerUser.objects.filter(company_profile=company).aggregate(maxv=Max('company_marketer_id'))
            cur = maxv.get('maxv') or 0
            marketer.company_marketer_id = int(cur) + 1
            print(f"    → Assigned marketer_id {marketer.company_marketer_id} to {marketer.full_name}")
        
        # Generate fresh UID
        new_uid = f"{prefix}MKT{int(marketer.company_marketer_id):03d}"
        
        # Check for uniqueness across ALL marketers
        existing = MarketerUser.objects.filter(company_marketer_uid=new_uid).exclude(pk=marketer.pk).exists()
        if existing:
            new_uid = f"{prefix}{company.id}MKT{int(marketer.company_marketer_id):03d}"
        
        old_uid = marketer.company_marketer_uid
        marketer.company_marketer_uid = new_uid
        marketer.save(update_fields=['company_marketer_uid'])
        
        status = "✓ REGENERATED" if old_uid != new_uid else "✓ VERIFIED"
        print(f"    {status}: {marketer.full_name:40} | {old_uid or 'None':20} → {new_uid}")
        
        if old_uid != new_uid:
            marketer_fixed += 1
        
        # Also update CompanyMarketerProfile if it exists
        try:
            profile = CompanyMarketerProfile.objects.get(marketer=marketer, company=company)
            profile.company_marketer_id = marketer.company_marketer_id
            profile.company_marketer_uid = marketer.company_marketer_uid
            profile.save(update_fields=['company_marketer_id', 'company_marketer_uid'])
        except CompanyMarketerProfile.DoesNotExist:
            # Create if doesn't exist
            try:
                CompanyMarketerProfile.objects.create(
                    marketer=marketer,
                    company=company,
                    company_marketer_id=marketer.company_marketer_id,
                    company_marketer_uid=marketer.company_marketer_uid
                )
                print(f"      → Created CompanyMarketerProfile")
            except Exception as e:
                print(f"      ⚠️  Could not create profile: {e}")

print(f"\n✓ MARKETER UIDs: {marketer_fixed}/{marketer_total} regenerated")

# ============================================================================
# PHASE 3: VERIFICATION
# ============================================================================
print("\n" + "=" * 100)
print("PHASE 3: FINAL VERIFICATION")
print("=" * 100)

print("\n📊 CLIENT UIDs BY COMPANY:")
for company in companies:
    clients = ClientUser.objects.filter(company_profile=company)
    if clients.exists():
        print(f"\n  {company.company_name}:")
        for client in clients:
            print(f"    ✓ {client.company_client_uid:20} - {client.full_name}")

print("\n📊 MARKETER UIDs BY COMPANY:")
for company in companies:
    marketers = MarketerUser.objects.filter(company_profile=company)
    if marketers.exists():
        print(f"\n  {company.company_name}:")
        for marketer in marketers:
            print(f"    ✓ {marketer.company_marketer_uid:20} - {marketer.full_name}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"✓ Client UIDs: {client_fixed} regenerated, {client_total} total processed")
print(f"✓ Marketer UIDs: {marketer_fixed} regenerated, {marketer_total} total processed")
print("\n✅ ALL UIDs REGENERATED SUCCESSFULLY!")
print("=" * 100)
