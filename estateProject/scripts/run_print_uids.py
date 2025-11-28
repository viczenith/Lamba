import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, MarketerUser, CustomUser
from django.utils import timezone

for comp in Company.objects.all():
    company = comp
    marketers_qs = MarketerUser.objects.filter(company_profile=company)
    parent_ids = list(marketers_qs.values_list('pk', flat=True))
    fallback_marketers = CustomUser.objects.filter(role='marketer', company_profile=company).exclude(id__in=parent_ids)
    combined = list(marketers_qs) + list(fallback_marketers)
    combined.sort(key=lambda u: getattr(u, 'date_registered', None) or timezone.now(), reverse=True)
    ordered_for_ids = sorted(combined, key=lambda u: getattr(u, 'date_registered', None) or timezone.now())
    id_map = {u.pk: idx+1 for idx,u in enumerate(ordered_for_ids)}
    print('Company:', company.slug, company.company_name, 'count:', len(combined))
    print(' ordered_for_ids:', [u.pk for u in ordered_for_ids])
    print(' id_map:', id_map)
    for m in combined:
        company_uid = id_map.get(m.pk, m.pk)
        company_marketer_id = getattr(m,'company_marketer_id', None) or company_uid
        try:
            prefix = company._company_prefix()
        except Exception:
            prefix = (company.company_name or 'CMP')[:3].upper()
        company_marketer_uid = getattr(m,'company_marketer_uid', None) or f"{prefix}-MKT{int(company_marketer_id):03d}"
        print(' -', m.pk, m.email, 'marketer_id=', company_marketer_id, 'uid=', company_marketer_uid)
    print()
