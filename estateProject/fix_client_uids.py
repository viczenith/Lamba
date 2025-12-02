import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company
from django.db.models import Max

print("=" * 80)
print("REGENERATING ALL CLIENT AND MARKETER UIDs")
print("=" * 80)

# Fix Client UIDs
client_count = 0
for cu in ClientUser.objects.select_related('company_profile').all():
    old_uid = cu.company_client_uid
    
    # If no company, skip
    if not cu.company_profile:
        print(f"⚠️  Skipping {cu.full_name} (ID: {cu.id}) - NO COMPANY ASSIGNED")
        continue
    
    # If no client_id, assign one
    if not cu.company_client_id:
        maxv = ClientUser.objects.filter(company_profile=cu.company_profile).aggregate(maxv=Max('company_client_id'))
        cur = maxv.get('maxv') or 0
        cu.company_client_id = int(cur) + 1
        print(f"  → Assigned client_id {cu.company_client_id} to {cu.full_name}")
    
    # Generate fresh UID
    prefix = cu.company_profile.company_name[:3].upper() if cu.company_profile.company_name else "CMP"
    new_uid = f"{prefix}CLT{int(cu.company_client_id):03d}"
    
    # Make sure it's unique
    existing = ClientUser.objects.filter(company_client_uid=new_uid).exclude(pk=cu.pk).exists()
    if existing:
        new_uid = f"{prefix}{cu.company_profile.id}CLT{int(cu.company_client_id):03d}"
    
    cu.company_client_uid = new_uid
    cu.save()
    client_count += 1
    
    status = "✓ Updated" if old_uid != new_uid else "✓ Verified"
    print(f"{status}: {cu.full_name} @ {cu.company_profile.company_name} | OLD: {old_uid} | NEW: {new_uid}")

print(f"\n✓ Fixed {client_count} client UIDs")

# Fix Marketer UIDs
marketer_count = 0
for mu in MarketerUser.objects.select_related('company_profile').all():
    old_uid = mu.company_marketer_uid
    
    # If no company, skip
    if not mu.company_profile:
        print(f"⚠️  Skipping {mu.full_name} (ID: {mu.id}) - NO COMPANY ASSIGNED")
        continue
    
    # If no marketer_id, assign one
    if not mu.company_marketer_id:
        maxv = MarketerUser.objects.filter(company_profile=mu.company_profile).aggregate(maxv=Max('company_marketer_id'))
        cur = maxv.get('maxv') or 0
        mu.company_marketer_id = int(cur) + 1
        print(f"  → Assigned marketer_id {mu.company_marketer_id} to {mu.full_name}")
    
    # Generate fresh UID
    prefix = mu.company_profile.company_name[:3].upper() if mu.company_profile.company_name else "CMP"
    new_uid = f"{prefix}MKT{int(mu.company_marketer_id):03d}"
    
    # Make sure it's unique
    existing = MarketerUser.objects.filter(company_marketer_uid=new_uid).exclude(pk=mu.pk).exists()
    if existing:
        new_uid = f"{prefix}{mu.company_profile.id}MKT{int(mu.company_marketer_id):03d}"
    
    mu.company_marketer_uid = new_uid
    mu.save()
    marketer_count += 1
    
    status = "✓ Updated" if old_uid != new_uid else "✓ Verified"
    print(f"{status}: {mu.full_name} @ {mu.company_profile.company_name} | OLD: {old_uid} | NEW: {new_uid}")

print(f"\n✓ Fixed {marketer_count} marketer UIDs")

print("\n" + "=" * 80)
print("VERIFICATION - CHECKING SPECIFIC UIDs")
print("=" * 80)
test_uids = ["LPLCLT005", "LPLCLT010", "LRHCLT005", "LPLMKT001"]
for uid in test_uids:
    client = ClientUser.objects.filter(company_client_uid=uid).first()
    marketer = MarketerUser.objects.filter(company_marketer_uid=uid).first()
    
    if client:
        print(f"  ✓ Found Client UID {uid}: {client.full_name} in {client.company_profile.company_name if client.company_profile else 'NONE'}")
    elif marketer:
        print(f"  ✓ Found Marketer UID {uid}: {marketer.full_name} in {marketer.company_profile.company_name if marketer.company_profile else 'NONE'}")
    else:
        print(f"  ✗ UID {uid}: NOT FOUND in database")

print("\n" + "=" * 80)
print("DONE!")
print("=" * 80)
