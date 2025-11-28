#!/usr/bin/env python
"""
Find and fix duplicate client UIDs by creating missing ClientUser subclass rows and assigning unique IDs.
"""
import os
import django
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.db import connection
from estateApp.models import ClientUser, CustomUser, Company, CompanySequence
from django.db.models import Max

def fix_client_duplicates(company_slug):
    comp = Company.objects.get(slug=company_slug)
    print(f"\n{'='*70}")
    print(f"Fixing client UIDs for: {comp.company_name}")
    print(f"{'='*70}\n")
    
    # Find all existing ClientUser rows
    existing_client_ids = set(ClientUser.objects.filter(company_profile=comp).values_list('pk', flat=True))
    print(f"Existing ClientUser rows: {len(existing_client_ids)}")
    if existing_client_ids:
        cu_qs = ClientUser.objects.filter(company_profile=comp).order_by('company_client_id').values('pk', 'email', 'company_client_id', 'company_client_uid')
        for m in cu_qs:
            print(f"  pk={m['pk']} | email={m['email'][:30]:30} | id={m['company_client_id']} | uid={m['company_client_uid']}")
    
    # Find fallback CustomUser clients (role='client' but no ClientUser row)
    fallback_clients = CustomUser.objects.filter(role='client', company_profile=comp).exclude(id__in=existing_client_ids)
    print(f"\nFallback CustomUser clients: {fallback_clients.count()}")
    if fallback_clients.count() > 0:
        for u in fallback_clients:
            print(f"  pk={u.pk} | email={u.email}")
        
        # Create missing ClientUser rows with unique IDs/UIDs
        print(f"\nCreating ClientUser subclass rows...")
        created = 0
        for u in fallback_clients:
            # Get next client ID
            try:
                new_id = CompanySequence.get_next(comp, 'client')
            except Exception:
                maxv = ClientUser.objects.filter(company_profile=comp).aggregate(maxv=Max('company_client_id'))
                cur = maxv.get('maxv') or 0
                new_id = int(cur) + 1
            
            # Build UID
            prefix = comp._company_prefix() if hasattr(comp, '_company_prefix') else (comp.company_name or 'CMP')[:3].upper()
            base_uid = f"{prefix}-CLT{int(new_id):03d}"
            if ClientUser.objects.filter(company_client_uid=base_uid).exists():
                base_uid = f"{prefix}{comp.id}-CLT{int(new_id):03d}"
            
            # Insert into DB
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO estateApp_clientuser (customuser_ptr_id, company_client_id, company_client_uid) VALUES (%s, %s, %s)",
                        [u.pk, new_id, base_uid]
                    )
                print(f"  ✓ pk={u.pk} -> id={new_id}, uid={base_uid}")
                created += 1
            except Exception as e:
                print(f"  ✗ pk={u.pk} failed: {e}")
        
        print(f"\nCreated {created} new ClientUser rows\n")
    
    # Final verification
    print("Final ClientUser rows:")
    final_qs = ClientUser.objects.filter(company_profile=comp).order_by('company_client_id').values('pk', 'email', 'company_client_id', 'company_client_uid')
    for m in final_qs:
        print(f"  pk={m['pk']} | email={m['email'][:30]:30} | id={m['company_client_id']} | uid={m['company_client_uid']}")
    
    # Check for duplicates
    from django.db.models import Count
    dups = ClientUser.objects.filter(company_profile=comp).values('company_client_uid').annotate(c=Count('id')).filter(c__gt=1)
    if dups.exists():
        print(f"\n✗ WARNING: Duplicate UIDs still found: {list(dups)}")
    else:
        print(f"\n✓ No duplicate UIDs - all clients have unique IDs!")

if __name__ == '__main__':
    try:
        fix_client_duplicates('lamba-property-limited')
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
