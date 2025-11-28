#!/usr/bin/env python
"""
Final comprehensive verification showing before/after state.
"""
import os, django, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import MarketerUser, ClientUser, Company
from django.db.models import Count

print("\n" + "="*80)
print(" "*20 + "FINAL VERIFICATION REPORT")
print("="*80)

comp = Company.objects.get(slug='lamba-property-limited')

print(f"\nCompany: {comp.company_name}")
print("-" * 80)

print("\n📊 MARKETERS IN LAMBA PROPERTY LIMITED:")
print("-" * 80)
marketers = MarketerUser.objects.filter(company_profile=comp).order_by('company_marketer_id').values('pk', 'email', 'company_marketer_id', 'company_marketer_uid')
if marketers:
    print(f"{'PK':<5} {'Email':<40} {'ID':<5} {'UID':<20}")
    print("-" * 80)
    for m in marketers:
        print(f"{m['pk']:<5} {m['email']:<40} {m['company_marketer_id']:<5} {m['company_marketer_uid']:<20}")
else:
    print("No marketers found.")

# Check for duplicates
dup_m = MarketerUser.objects.filter(company_profile=comp).values('company_marketer_uid').annotate(c=Count('id')).filter(c__gt=1)
if dup_m:
    print(f"\n⚠️  DUPLICATES FOUND: {list(dup_m)}")
else:
    print(f"\n✅ No duplicate UIDs (all {marketers.count()} marketers have unique UIDs)")

print("\n" + "="*80)
print("📊 CLIENTS IN LAMBA PROPERTY LIMITED:")
print("-" * 80)
clients = ClientUser.objects.filter(company_profile=comp).order_by('company_client_id').values('pk', 'email', 'company_client_id', 'company_client_uid')
if clients:
    print(f"{'PK':<5} {'Email':<40} {'ID':<5} {'UID':<20}")
    print("-" * 80)
    for c in clients:
        print(f"{c['pk']:<5} {c['email']:<40} {c['company_client_id']:<5} {c['company_client_uid']:<20}")
else:
    print("No clients found.")

# Check for duplicates
dup_c = ClientUser.objects.filter(company_profile=comp).values('company_client_uid').annotate(c=Count('id')).filter(c__gt=1)
if dup_c:
    print(f"\n⚠️  DUPLICATES FOUND: {list(dup_c)}")
else:
    print(f"\n✅ No duplicate UIDs (all {clients.count()} clients have unique UIDs)")

print("\n" + "="*80)
print("🔍 SYSTEM-WIDE CHECK:")
print("-" * 80)

all_m_dups = MarketerUser.objects.values('company_marketer_uid').annotate(c=Count('id')).filter(c__gt=1)
all_c_dups = ClientUser.objects.values('company_client_uid').annotate(c=Count('id')).filter(c__gt=1)

print(f"Total MarketerUsers: {MarketerUser.objects.count()}")
print(f"  ✅ Duplicate MarketerUser UIDs: {'None' if not all_m_dups else list(all_m_dups)}")

print(f"\nTotal ClientUsers: {ClientUser.objects.count()}")
print(f"  ✅ Duplicate ClientUser UIDs: {'None' if not all_c_dups else list(all_c_dups)}")

print("\n" + "="*80)
if not dup_m and not dup_c and not all_m_dups and not all_c_dups:
    print("✅ ✅ ✅ ALL CHECKS PASSED - DUPLICATE UID ISSUE FULLY RESOLVED ✅ ✅ ✅")
else:
    print("⚠️  ISSUES DETECTED - Please review above")
print("="*80 + "\n")
