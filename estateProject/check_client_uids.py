import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, Company, MarketerUser

print("=" * 80)
print("COMPANIES IN DATABASE")
print("=" * 80)
for c in Company.objects.all():
    print(f"  ID: {c.id} | Name: {c.company_name} | Slug: {c.slug}")

print("\n" + "=" * 80)
print("CLIENT USERS WITH UIDs")
print("=" * 80)
for cu in ClientUser.objects.select_related('company_profile').all():
    company_name = cu.company_profile.company_name if cu.company_profile else "NONE"
    print(f"  ID: {cu.id} | Name: {cu.full_name:30} | Company: {company_name:30} | UID: {cu.company_client_uid}")

print("\n" + "=" * 80)
print("MARKETER USERS WITH UIDs")
print("=" * 80)
for mu in MarketerUser.objects.select_related('company_profile').all():
    company_name = mu.company_profile.company_name if mu.company_profile else "NONE"
    print(f"  ID: {mu.id} | Name: {mu.full_name:30} | Company: {company_name:30} | UID: {mu.company_marketer_uid}")

print("\n" + "=" * 80)
print("SPECIFIC UID LOOKUPS")
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
