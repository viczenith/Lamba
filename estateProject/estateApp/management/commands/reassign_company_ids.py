from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from estateApp.models import Company, ClientUser, MarketerUser, CompanySequence


class Command(BaseCommand):
    help = 'Reassign per-company numeric IDs and UIDs for all users in a given company. Use --force to overwrite existing IDs.'

    def add_arguments(self, parser):
        parser.add_argument('company', help='Company slug, id, or name (case-insensitive)')
        parser.add_argument('--force', action='store_true', help='Overwrite existing numeric IDs and UIDs')

    def handle(self, *args, **options):
        identifier = options['company']
        force = options['force']

        # Find company by slug, id, or name
        comp = None
        try:
            # try id
            if identifier.isdigit():
                comp = Company.objects.filter(id=int(identifier)).first()
            if not comp:
                comp = Company.objects.filter(slug=identifier).first()
            if not comp:
                comp = Company.objects.filter(company_name__iexact=identifier).first()
        except Exception:
            comp = None

        if not comp:
            self.stderr.write(self.style.ERROR(f'Company not found for identifier: {identifier}'))
            return

        self.stdout.write(f"Reassigning IDs for company: {comp.company_name} (id={comp.id}), force={force}")

        clients_qs = ClientUser.objects.filter(company_profile=comp).order_by('date_registered', 'id')
        marketers_qs = MarketerUser.objects.filter(company_profile=comp).order_by('date_registered', 'id')

        total_clients = 0
        total_marketers = 0

        with transaction.atomic():
            if force:
                # reset sequence counters for this company
                CompanySequence.objects.filter(company=comp, key__in=['client', 'marketer']).delete()

            # Ensure sequences exist and are initialized to 0 (get_next will create)
            # Assign marketer IDs first
            for m in marketers_qs:
                try:
                    new_id = CompanySequence.get_next(comp, 'marketer')
                except Exception:
                    # fallback to max+1
                    maxv = MarketerUser.objects.filter(company_profile=comp).aggregate(maxv=Max('company_marketer_id'))
                    cur = maxv.get('maxv') or 0
                    new_id = int(cur) + 1
                    CompanySequence.objects.get_or_create(company=comp, key='marketer', defaults={'last_value': new_id})
                m.company_marketer_id = new_id
                # build uid
                prefix = comp._company_prefix() if hasattr(comp, '_company_prefix') else ''.join([w[0] for w in comp.company_name.upper().split()[:3]])
                base_uid = f"{prefix}MKT{int(new_id):03d}"
                if MarketerUser.objects.filter(company_marketer_uid=base_uid).exclude(pk=m.pk).exists():
                    base_uid = f"{prefix}{comp.id}MKT{int(new_id):03d}"
                m.company_marketer_uid = base_uid
                m.save(update_fields=['company_marketer_id', 'company_marketer_uid'])
                total_marketers += 1

            # Then clients
            for c in clients_qs:
                try:
                    new_id = CompanySequence.get_next(comp, 'client')
                except Exception:
                    maxv = ClientUser.objects.filter(company_profile=comp).aggregate(maxv=Max('company_client_id'))
                    cur = maxv.get('maxv') or 0
                    new_id = int(cur) + 1
                    CompanySequence.objects.get_or_create(company=comp, key='client', defaults={'last_value': new_id})
                c.company_client_id = new_id
                prefix = comp._company_prefix() if hasattr(comp, '_company_prefix') else ''.join([w[0] for w in comp.company_name.upper().split()[:3]])
                base_uid = f"{prefix}CLT{int(new_id):03d}"
                if ClientUser.objects.filter(company_client_uid=base_uid).exclude(pk=c.pk).exists():
                    base_uid = f"{prefix}{comp.id}CLT{int(new_id):03d}"
                c.company_client_uid = base_uid
                c.save(update_fields=['company_client_id', 'company_client_uid'])
                total_clients += 1

        self.stdout.write(self.style.SUCCESS(f'Reassigned {total_clients} clients and {total_marketers} marketers for {comp.company_name}'))