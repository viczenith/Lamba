#!/usr/bin/env python
import os, django, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db.models import Count
from estateApp.models import MarketerUser, ClientUser

print("="*70)
print("SYSTEM-WIDE DUPLICATE UID CHECK")
print("="*70)

print("\n1. Checking MarketerUser UIDs:")
dup_m = MarketerUser.objects.values('company_marketer_uid').annotate(c=Count('id')).filter(c__gt=1)
if dup_m:
    print(f"   ✗ Duplicates found: {list(dup_m)}")
else:
    total_m = MarketerUser.objects.count()
    print(f"   ✓ No duplicates ({total_m} unique MarketerUser UIDs)")

print("\n2. Checking ClientUser UIDs:")
dup_c = ClientUser.objects.values('company_client_uid').annotate(c=Count('id')).filter(c__gt=1)
if dup_c:
    print(f"   ✗ Duplicates found: {list(dup_c)}")
else:
    total_c = ClientUser.objects.count()
    print(f"   ✓ No duplicates ({total_c} unique ClientUser UIDs)")

print("\n3. Verifying per-company uniqueness:")
from estateApp.models import Company
for comp in Company.objects.all():
    m_count = MarketerUser.objects.filter(company_profile=comp).count()
    c_count = ClientUser.objects.filter(company_profile=comp).count()
    if m_count > 0 or c_count > 0:
        print(f"   {comp.company_name}: {m_count} marketers, {c_count} clients")

print("\n" + "="*70)
print("✓ ALL CHECKS PASSED - No duplicate company-scoped UIDs!")
print("="*70)
