#!/usr/bin/env python
"""
Debug script to print per-company client IDs/UIDs using view logic.
"""
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, ClientUser, CustomUser
from django.utils import timezone

for comp in Company.objects.all():
    company = comp
    clients_qs = ClientUser.objects.filter(company_profile=company)
    parent_ids = list(clients_qs.values_list('pk', flat=True))
    fallback_clients = CustomUser.objects.filter(role='client', company_profile=company).exclude(id__in=parent_ids)
    combined = list(clients_qs) + list(fallback_clients)
    
    if not combined:
        continue
    
    combined.sort(key=lambda u: getattr(u, 'date_registered', None) or timezone.now(), reverse=True)
    ordered_for_ids = sorted(combined, key=lambda u: getattr(u, 'date_registered', None) or timezone.now())
    id_map = {u.pk: idx+1 for idx,u in enumerate(ordered_for_ids)}
    
    print(f'Company: {company.slug} {company.company_name} count: {len(combined)}')
    print(f' ordered_for_ids: {[u.pk for u in ordered_for_ids]}')
    print(f' id_map: {id_map}')
    
    for c in combined:
        company_uid = id_map.get(c.pk, c.pk)
        company_client_id = getattr(c,'company_client_id', None) or company_uid
        try:
            prefix = company._company_prefix()
        except Exception:
            prefix = (company.company_name or 'CMP')[:3].upper()
        company_client_uid = getattr(c,'company_client_uid', None) or f"{prefix}-CLT{int(company_client_id):03d}"
        print(f' - {c.pk} {c.email} client_id= {company_client_id} uid= {company_client_uid}')
    print()
