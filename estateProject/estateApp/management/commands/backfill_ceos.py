from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from estateApp.models import Company, CompanyCeo


class Command(BaseCommand):
    help = 'Backfill CompanyCeo records from legacy Company.ceo_name and ceo_dob fields'

    def handle(self, *args, **options):
        companies = Company.objects.all()
        created = 0
        skipped = 0
        for c in companies:
            try:
                # If the company already has any CEO records, skip
                if c.ceos.exists():
                    skipped += 1
                    continue

                name = (c.ceo_name or '').strip()
                dob = c.ceo_dob

                if not name and not dob:
                    skipped += 1
                    continue

                CompanyCeo.objects.create(
                    company=c,
                    name=name or '',
                    dob=dob,
                    is_primary=True
                )
                created += 1
            except Exception as e:
                self.stderr.write(f'Failed for company {c.id} ({c.company_name}): {e}')

        self.stdout.write(self.style.SUCCESS(f'Backfill complete: created={created}, skipped={skipped}'))
