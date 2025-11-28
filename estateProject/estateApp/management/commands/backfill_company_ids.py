from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from estateApp.models import Company, ClientUser, MarketerUser


class Command(BaseCommand):
    help = 'Backfill per-company client and marketer IDs (company_client_id, company_marketer_id) for existing records.'

    def handle(self, *args, **options):
        companies = Company.objects.all()
        total_clients = 0
        total_marketers = 0

        for comp in companies:
            self.stdout.write(f"Processing company: {comp.company_name} (id={comp.id})")
            # Clients
            with transaction.atomic():
                max_client = (
                    ClientUser.objects.filter(company_profile=comp, company_client_id__isnull=False)
                    .aggregate(maxv=Max('company_client_id'))
                )
                next_client_id = (max_client.get('maxv') or 0) + 1

                missing_clients = ClientUser.objects.filter(company_profile=comp, company_client_id__isnull=True).order_by('date_registered', 'id')
                for c in missing_clients:
                    c.company_client_id = next_client_id
                    c.save(update_fields=['company_client_id'])
                    next_client_id += 1
                    total_clients += 1

            # Marketers
            with transaction.atomic():
                max_marketer = (
                    MarketerUser.objects.filter(company_profile=comp, company_marketer_id__isnull=False)
                    .aggregate(maxv=Max('company_marketer_id'))
                )
                next_marketer_id = (max_marketer.get('maxv') or 0) + 1

                missing_marketers = MarketerUser.objects.filter(company_profile=comp, company_marketer_id__isnull=True).order_by('date_registered', 'id')
                for m in missing_marketers:
                    m.company_marketer_id = next_marketer_id
                    m.save(update_fields=['company_marketer_id'])
                    next_marketer_id += 1
                    total_marketers += 1

        self.stdout.write(self.style.SUCCESS(f'Backfilled {total_clients} client IDs and {total_marketers} marketer IDs across {companies.count()} companies.'))
