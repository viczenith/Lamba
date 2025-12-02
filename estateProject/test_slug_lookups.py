import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, MarketerUser, Company

print("=" * 100)
print("COMPREHENSIVE UID AND NAME-SLUG VERIFICATION")
print("=" * 100)

print("\n📋 TESTING CLIENT PROFILES")
print("=" * 100)

test_cases = [
    # (slug, company_slug, expected_result)
    ("LAMCLT001", "lamba-property-limited", "Victor client2"),
    ("LAMCLT010", "lamba-property-limited", "Victor Client 6"),
    ("victor-client-6", "lamba-property-limited", "Victor Client 6"),
    ("victor-client", "lamba-property-limited", "Victor Client"),
    ("TESCLT001", "test-company", "Test Client 0"),
    ("test-client-0", "test-company", "Test Client 0"),
    # Non-existent should fail
    ("NONEXIST001", "lamba-property-limited", None),
    ("fake-name", "lamba-property-limited", None),
]

print("\n▶ CLIENT PROFILE LOOKUPS:")
for slug, company_slug, expected_name in test_cases:
    company = Company.objects.get(slug=company_slug)
    
    # Try UID lookup
    client = ClientUser.objects.filter(
        company_client_uid=slug,
        company_profile=company
    ).first()
    
    # Try name slug
    if not client:
        name_from_slug = slug.replace('-', ' ')
        client = ClientUser.objects.filter(
            full_name__iexact=name_from_slug,
            company_profile=company
        ).first()
    
    # Try exact name
    if not client:
        client = ClientUser.objects.filter(
            full_name=slug,
            company_profile=company
        ).first()
    
    if client:
        result = f"✓ FOUND: {client.full_name}"
        if expected_name and client.full_name != expected_name:
            result += f" (EXPECTED: {expected_name}) ⚠️"
    else:
        result = "✗ NOT FOUND"
        if expected_name:
            result += " (EXPECTED TO EXIST) ⚠️"
    
    print(f"  {slug:25} @ {company_slug:25} → {result}")

print("\n📋 TESTING MARKETER PROFILES")
print("=" * 100)

marketer_test_cases = [
    # (slug, company_slug, expected_result)
    ("LAMMKT001", "lamba-property-limited", "Victor marketer 3"),
    ("LAMMKT002", "lamba-property-limited", "Victor Marketer"),
    ("victor-marketer-3", "lamba-property-limited", "Victor marketer 3"),
    ("victor-marketer", "lamba-property-limited", "Victor Marketer"),
    ("TESMKT001", "test-company", "Demo New Marketer"),
    ("demo-new-marketer", "test-company", "Demo New Marketer"),
    ("LAMMKT011", "lamba-real-homes", "Victor marketer 3"),
    # Non-existent should fail
    ("NONEXIST001", "lamba-property-limited", None),
    ("fake-name", "lamba-property-limited", None),
]

print("\n▶ MARKETER PROFILE LOOKUPS:")
for slug, company_slug, expected_name in marketer_test_cases:
    company = Company.objects.get(slug=company_slug)
    
    # Try UID lookup
    marketer = MarketerUser.objects.filter(
        company_marketer_uid=slug,
        company_profile=company
    ).first()
    
    # Try name slug
    if not marketer:
        name_from_slug = slug.replace('-', ' ')
        marketer = MarketerUser.objects.filter(
            full_name__iexact=name_from_slug,
            company_profile=company
        ).first()
    
    # Try exact name
    if not marketer:
        marketer = MarketerUser.objects.filter(
            full_name=slug,
            company_profile=company
        ).first()
    
    if marketer:
        result = f"✓ FOUND: {marketer.full_name}"
        if expected_name and marketer.full_name != expected_name:
            result += f" (EXPECTED: {expected_name}) ⚠️"
    else:
        result = "✗ NOT FOUND"
        if expected_name:
            result += " (EXPECTED TO EXIST) ⚠️"
    
    print(f"  {slug:25} @ {company_slug:25} → {result}")

print("\n" + "=" * 100)
print("✅ TEST COMPLETE")
print("=" * 100)

print("\n📝 EXAMPLE URLs TO TEST:")
print("\nClient Profiles:")
print("  UID-based:   http://127.0.0.1:8000/LAMCLT010.client-profile/?company=lamba-property-limited")
print("  Name-based:  http://127.0.0.1:8000/victor-client-6.client-profile/?company=lamba-property-limited")
print("  No company:  http://127.0.0.1:8000/LAMCLT001.client-profile/ (uses user's company)")

print("\nMarketer Profiles:")
print("  UID-based:   http://127.0.0.1:8000/LAMMKT001.marketer-profile/?company=lamba-property-limited")
print("  Name-based:  http://127.0.0.1:8000/victor-marketer-3.marketer-profile/?company=lamba-property-limited")
print("  No company:  http://127.0.0.1:8000/LAMMKT001.marketer-profile/ (uses user's company)")

print("\n" + "=" * 100)
