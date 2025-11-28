from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from estateApp.models import Company, ClientUser, MarketerUser, CustomUser, CompanySequence


class Command(BaseCommand):
    help = 'Create missing subclass rows for CustomUser marketers/clients and assign company IDs/UIDs.'

    def add_arguments(self, parser):
        parser.add_argument('company', help='Company slug, id, or name (case-insensitive)')

    def handle(self, *args, **options):
        identifier = options['company']

        # Find company
        comp = None
        try:
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

        self.stdout.write(f"Creating missing subclass rows for company: {comp.company_name} (id={comp.id})")

        created_marketers = 0
        created_clients = 0


        with transaction.atomic():
            # Marketers
            parent_marketers = CustomUser.objects.filter(role='marketer', company_profile=comp).exclude(
                id__in=MarketerUser.objects.values('id')
            )
            for u in parent_marketers:
                # Skip if required fields are missing
                if not (u.email and u.full_name and u.phone):
                    self.stderr.write(f"Skipping pk={u.pk} (missing required fields)")
                    continue
                try:
                    new_id = CompanySequence.get_next(comp, 'marketer')
                except Exception:
                    maxv = MarketerUser.objects.filter(company_profile=comp).aggregate(maxv=Max('company_marketer_id'))
                    cur = maxv.get('maxv') or 0
                    new_id = int(cur) + 1
                prefix = comp._company_prefix()
                base_uid = f"{prefix}-MKT{int(new_id):03d}"
                if MarketerUser.objects.filter(company_marketer_uid=base_uid).exists():
                    base_uid = f"{prefix}{comp.id}-MKT{int(new_id):03d}"
                MarketerUser.objects.create(
                    pk=u.pk,
                    customuser_ptr=u,
                    company_profile=comp,
                    email=u.email,
                    full_name=u.full_name,
                    phone=u.phone,
                    date_registered=u.date_registered,
                    company_marketer_id=new_id,
                    company_marketer_uid=base_uid,
                    is_active=u.is_active,
                    is_deleted=u.is_deleted,
                    deleted_at=u.deleted_at,
                    deletion_reason=u.deletion_reason,
                )
                created_marketers += 1

            # Clients
            parent_clients = CustomUser.objects.filter(role='client', company_profile=comp).exclude(
                id__in=ClientUser.objects.values('id')
            )
            for u in parent_clients:
                if not (u.email and u.full_name and u.phone):
                    self.stderr.write(f"Skipping pk={u.pk} (missing required fields)")
                    continue
                try:
                    new_id = CompanySequence.get_next(comp, 'client')
                except Exception:
                    maxv = ClientUser.objects.filter(company_profile=comp).aggregate(maxv=Max('company_client_id'))
                    cur = maxv.get('maxv') or 0
                    new_id = int(cur) + 1
                prefix = comp._company_prefix()
                base_uid = f"{prefix}-CLT{int(new_id):03d}"
                if ClientUser.objects.filter(company_client_uid=base_uid).exists():
                    base_uid = f"{prefix}{comp.id}-CLT{int(new_id):03d}"
                ClientUser.objects.create(
                    pk=u.pk,
                    customuser_ptr=u,
                    company_profile=comp,
                    email=u.email,
                    full_name=u.full_name,
                    phone=u.phone,
                    date_registered=u.date_registered,
                    company_client_id=new_id,
                    company_client_uid=base_uid,
                    is_active=u.is_active,
                    is_deleted=u.is_deleted,
                    deleted_at=u.deleted_at,
                    deletion_reason=u.deletion_reason,
                )
                created_clients += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created_marketers} marketer rows and {created_clients} client rows for {comp.company_name}'))