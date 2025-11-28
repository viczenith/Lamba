from django.core.management.base import BaseCommand
from django.db import transaction
from estateApp.models import Company, ClientUser, MarketerUser


class Command(BaseCommand):
    help = 'Backfill company-prefixed UIDs (company_client_uid, company_marketer_uid) using existing numeric IDs and company prefix.'

    def handle(self, *args, **options):
        companies = Company.objects.all()
        total_clients = 0
        total_marketers = 0

        for comp in companies:
            self.stdout.write(f"Processing company: {comp.company_name} (id={comp.id})")
            # Clients
            with transaction.atomic():
                clients = ClientUser.objects.filter(company_profile=comp, company_client_id__isnull=False, company_client_uid__isnull=True).order_by('company_client_id')
                for c in clients:
                    try:
                        prefix = self._company_prefix(comp)
                        base_uid = f"{prefix}-CLT{int(c.company_client_id):03d}"
                        if ClientUser.objects.filter(company_client_uid=base_uid).exclude(pk=c.pk).exists():
                            base_uid = f"{prefix}{comp.id}-CLT{int(c.company_client_id):03d}"
                        c.company_client_uid = base_uid
                        c.save(update_fields=['company_client_uid'])
                        total_clients += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to set UID for client {c.pk}: {e}"))

            # Marketers
            with transaction.atomic():
                marketers = MarketerUser.objects.filter(company_profile=comp, company_marketer_id__isnull=False, company_marketer_uid__isnull=True).order_by('company_marketer_id')
                for m in marketers:
                    try:
                        prefix = self._company_prefix(comp)
                        base_uid = f"{prefix}-MKT{int(m.company_marketer_id):03d}"
                        if MarketerUser.objects.filter(company_marketer_uid=base_uid).exclude(pk=m.pk).exists():
                            base_uid = f"{prefix}{comp.id}-MKT{int(m.company_marketer_id):03d}"
                        m.company_marketer_uid = base_uid
                        m.save(update_fields=['company_marketer_uid'])
                        total_marketers += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to set UID for marketer {m.pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Backfilled {total_clients} client UIDs and {total_marketers} marketer UIDs across {companies.count()} companies.'))

    def _company_prefix(self, comp):
        try:
            name = (comp.company_name or '').upper()
            import re
            words = re.findall(r"[A-Z0-9]+", name)
            if not words:
                return 'CMP'
            prefix = ''.join(w[0] for w in words[:3])
            if len(prefix) < 2:
                prefix = f"CMP{comp.id}"
            return prefix
        except Exception:
            return 'CMP'
