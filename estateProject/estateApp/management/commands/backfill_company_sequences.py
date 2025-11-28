from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from estateApp.models import Company, CompanySequence, ClientUser, MarketerUser


class Command(BaseCommand):
    help = 'Initialize per-company CompanySequence rows from existing numeric client/marketer IDs.'

    def handle(self, *args, **options):
        companies = Company.objects.all()
        created = 0
        updated = 0
        for comp in companies:
            self.stdout.write(f"Processing company: {comp.company_name} (id={comp.id})")
            # client
            with transaction.atomic():
                max_client = ClientUser.objects.filter(company_profile=comp, company_client_id__isnull=False).aggregate(maxv=Max('company_client_id'))
                max_client_val = max_client.get('maxv') or 0
                obj, created_flag = CompanySequence.objects.get_or_create(company=comp, key='client', defaults={'last_value': max_client_val})
                if not created_flag and obj.last_value != max_client_val:
                    obj.last_value = max_client_val
                    obj.save(update_fields=['last_value'])
                    updated += 1
                elif created_flag:
                    created += 1
            # marketer
            with transaction.atomic():
                max_mark = MarketerUser.objects.filter(company_profile=comp, company_marketer_id__isnull=False).aggregate(maxv=Max('company_marketer_id'))
                max_mark_val = max_mark.get('maxv') or 0
                obj2, created_flag2 = CompanySequence.objects.get_or_create(company=comp, key='marketer', defaults={'last_value': max_mark_val})
                if not created_flag2 and obj2.last_value != max_mark_val:
                    obj2.last_value = max_mark_val
                    obj2.save(update_fields=['last_value'])
                    updated += 1
                elif created_flag2:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'CompanySequence initialization complete. Created: {created}, Updated: {updated}'))