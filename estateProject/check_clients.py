#!/usr/bin/env python
import os, django, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import ClientUser, Company

comp = Company.objects.get(slug='lamba-property-limited')
print("All ClientUsers for Lamba Property Limited:")
all_clients = ClientUser.objects.filter(company_profile=comp).order_by('company_client_id').values('pk','email','company_client_id','company_client_uid')
for c in all_clients:
    print(f"  pk={c['pk']} id={c['company_client_id']} uid={c['company_client_uid']} email={c['email']}")

print("\nCheck for duplicates:")
from django.db.models import Count
dups = ClientUser.objects.filter(company_profile=comp).values('company_client_uid').annotate(c=Count('id')).filter(c__gt=1)
if dups:
    print(f"  ✗ Duplicates found: {list(dups)}")
else:
    print(f"  ✓ No duplicate UIDs")
