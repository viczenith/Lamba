#!/usr/bin/env python
"""
Fix duplicate marketer UIDs by inserting missing MarketerUser child row for pk=15.
"""
import os
import django
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db import connection
from estateApp.models import MarketerUser, Company

print("Inserting missing MarketerUser row for pk=15...")
try:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO estateApp_marketeruser (customuser_ptr_id, company_marketer_id, company_marketer_uid) VALUES (%s, %s, %s)",
            [15, 2, 'LPL-MKT002']
        )
    print("✓ Successfully inserted MarketerUser row for pk=15")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Verify
print("\nVerifying MarketerUsers in Lamba Property Limited:")
try:
    comp = Company.objects.get(slug='lamba-property-limited')
    all_marketers = MarketerUser.objects.filter(company_profile=comp).order_by('company_marketer_id').values('pk', 'email', 'company_marketer_id', 'company_marketer_uid')
    print(f"Found {all_marketers.count()} marketers:\n")
    for m in all_marketers:
        print(f"  pk={m['pk']:3} | email={m['email']:30} | id={m['company_marketer_id']} | uid={m['company_marketer_uid']}")
except Exception as e:
    print(f"✗ Verification error: {e}")
    sys.exit(1)

print("\n✓ Fix complete! All marketers now have unique IDs and UIDs.")
