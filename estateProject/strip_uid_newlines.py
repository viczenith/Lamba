import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser

print("=" * 80)
print("REMOVING NEWLINES FROM ALL UIDs")
print("=" * 80)

# Fix Client UIDs
client_count = 0
for cu in ClientUser.objects.all():
    if cu.company_client_uid and '\n' in cu.company_client_uid:
        old_uid = repr(cu.company_client_uid)  # Show with escape chars
        cu.company_client_uid = cu.company_client_uid.replace('\n', '').replace('\r', '').strip()
        cu.save()
        client_count += 1
        print(f"✓ Fixed {cu.full_name}: {old_uid} → {cu.company_client_uid}")

print(f"\n✓ Fixed {client_count} client UIDs with newlines")

# Fix Marketer UIDs
marketer_count = 0
for mu in MarketerUser.objects.all():
    if mu.company_marketer_uid and '\n' in mu.company_marketer_uid:
        old_uid = repr(mu.company_marketer_uid)  # Show with escape chars
        mu.company_marketer_uid = mu.company_marketer_uid.replace('\n', '').replace('\r', '').strip()
        mu.save()
        marketer_count += 1
        print(f"✓ Fixed {mu.full_name}: {old_uid} → {mu.company_marketer_uid}")

print(f"\n✓ Fixed {marketer_count} marketer UIDs with newlines")

print("\n" + "=" * 80)
print("ALL UIDs IN DATABASE (CLEANED)")
print("=" * 80)
print("\nCLIENT UIDs:")
for cu in ClientUser.objects.select_related('company_profile').filter(company_profile__isnull=False):
    print(f"  {cu.company_client_uid:20} - {cu.full_name:30} @ {cu.company_profile.company_name}")

print("\nMARKETER UIDs:")
for mu in MarketerUser.objects.select_related('company_profile').filter(company_profile__isnull=False):
    print(f"  {mu.company_marketer_uid:20} - {mu.full_name:30} @ {mu.company_profile.company_name}")

print("\n" + "=" * 80)
print("DONE!")
print("=" * 80)
