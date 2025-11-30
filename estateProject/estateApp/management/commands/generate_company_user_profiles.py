"""
Management command to generate CompanyMarketerProfile and CompanyClientProfile
for existing marketers and clients that are associated with companies.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from estateApp.models import (
    MarketerUser, ClientUser, Company,
    CompanyMarketerProfile, CompanyClientProfile,
    MarketerAffiliation
)


class Command(BaseCommand):
    help = 'Generate company-specific user profiles for existing marketers and clients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=int,
            help='Generate profiles only for a specific company ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        company_id = options.get('company')

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('COMPANY USER PROFILES GENERATION'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))

        # Generate for marketers
        self.stdout.write(self.style.SUCCESS('\n📊 GENERATING MARKETER PROFILES\n'))
        self.generate_marketer_profiles(dry_run, company_id)

        # Generate for clients
        self.stdout.write(self.style.SUCCESS('\n📊 GENERATING CLIENT PROFILES\n'))
        self.generate_client_profiles(dry_run, company_id)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('GENERATION COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

    def generate_marketer_profiles(self, dry_run, company_id):
        """Generate CompanyMarketerProfile for all marketers."""
        query = MarketerUser.objects.filter(company_profile__isnull=False)
        
        if company_id:
            query = query.filter(company_profile_id=company_id)
        
        total_marketers = query.count()
        created_count = 0
        skipped_count = 0

        self.stdout.write(f"Processing {total_marketers} marketers...")

        for marketer in query:
            company = marketer.company_profile
            
            # Check if profile already exists
            if CompanyMarketerProfile.objects.filter(marketer=marketer, company=company).exists():
                self.stdout.write(
                    f"  ⊘ SKIP: {marketer.full_name} ({marketer.email}) - Profile already exists in {company.company_name}"
                )
                skipped_count += 1
                continue

            # Also check MarketerAffiliation for additional companies
            affiliations = MarketerAffiliation.objects.filter(marketer=marketer).exclude(company=company)
            
            try:
                with transaction.atomic():
                    # Create profile for primary company
                    if not dry_run:
                        profile = self._create_profile(marketer, company)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ CREATE: {marketer.full_name} in {company.company_name} → {profile.company_marketer_uid}"
                            )
                        )
                    else:
                        prefix = self._get_prefix(company)
                        next_id = self._get_next_marketer_id(company)
                        uid = f"{prefix}MKT{next_id:03d}"
                        self.stdout.write(
                            f"  [DRY] CREATE: {marketer.full_name} in {company.company_name} → {uid}"
                        )
                    
                    created_count += 1
                    
                    # Create profiles for affiliated companies
                    for affiliation in affiliations:
                        aff_company = affiliation.company
                        if not CompanyMarketerProfile.objects.filter(marketer=marketer, company=aff_company).exists():
                            if not dry_run:
                                profile = self._create_profile(marketer, aff_company)
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"  ✓ CREATE: {marketer.full_name} in {aff_company.company_name} → {profile.company_marketer_uid}"
                                    )
                                )
                            else:
                                prefix = self._get_prefix(aff_company)
                                next_id = self._get_next_marketer_id(aff_company)
                                uid = f"{prefix}MKT{next_id:03d}"
                                self.stdout.write(
                                    f"  [DRY] CREATE: {marketer.full_name} in {aff_company.company_name} → {uid}"
                                )
                            created_count += 1
                            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ ERROR: {marketer.full_name} - {str(e)}")
                )

        self.stdout.write(f"\nMarketer Summary:")
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")

    def generate_client_profiles(self, dry_run, company_id):
        """Generate CompanyClientProfile for all clients."""
        query = ClientUser.objects.filter(company_profile__isnull=False)
        
        if company_id:
            query = query.filter(company_profile_id=company_id)
        
        total_clients = query.count()
        created_count = 0
        skipped_count = 0

        self.stdout.write(f"Processing {total_clients} clients...")

        for client in query:
            company = client.company_profile
            
            # Check if profile already exists
            if CompanyClientProfile.objects.filter(client=client, company=company).exists():
                self.stdout.write(
                    f"  ⊘ SKIP: {client.full_name} ({client.email}) - Profile already exists in {company.company_name}"
                )
                skipped_count += 1
                continue

            try:
                with transaction.atomic():
                    if not dry_run:
                        profile = self._create_client_profile(client, company)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ CREATE: {client.full_name} in {company.company_name} → {profile.company_client_uid}"
                            )
                        )
                    else:
                        prefix = self._get_prefix(company)
                        next_id = self._get_next_client_id(company)
                        uid = f"{prefix}CLT{next_id:03d}"
                        self.stdout.write(
                            f"  [DRY] CREATE: {client.full_name} in {company.company_name} → {uid}"
                        )
                    created_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ ERROR: {client.full_name} - {str(e)}")
                )

        self.stdout.write(f"\nClient Summary:")
        self.stdout.write(f"  Created: {created_count}")
        self.stdout.write(f"  Skipped: {skipped_count}")

    def _create_profile(self, marketer, company):
        """Create a CompanyMarketerProfile for a marketer in a company."""
        next_id = self._get_next_marketer_id(company)
        prefix = self._get_prefix(company)
        base_uid = f"{prefix}MKT{next_id:03d}"
        
        # Ensure uniqueness
        if CompanyMarketerProfile.objects.filter(company_marketer_uid=base_uid).exists():
            base_uid = f"{prefix}{company.id}MKT{next_id:03d}"
        
        profile, _ = CompanyMarketerProfile.objects.get_or_create(
            marketer=marketer,
            company=company,
            defaults={
                'company_marketer_id': next_id,
                'company_marketer_uid': base_uid
            }
        )
        return profile

    def _create_client_profile(self, client, company):
        """Create a CompanyClientProfile for a client in a company."""
        next_id = self._get_next_client_id(company)
        prefix = self._get_prefix(company)
        base_uid = f"{prefix}CLT{next_id:03d}"
        
        # Ensure uniqueness
        if CompanyClientProfile.objects.filter(company_client_uid=base_uid).exists():
            base_uid = f"{prefix}{company.id}CLT{next_id:03d}"
        
        profile, _ = CompanyClientProfile.objects.get_or_create(
            client=client,
            company=company,
            defaults={
                'company_client_id': next_id,
                'company_client_uid': base_uid
            }
        )
        return profile

    def _get_next_marketer_id(self, company):
        """Get the next marketer ID for a company."""
        maxv = CompanyMarketerProfile.objects.filter(
            company=company
        ).aggregate(maxv=Max('company_marketer_id'))
        return (maxv.get('maxv') or 0) + 1

    def _get_next_client_id(self, company):
        """Get the next client ID for a company."""
        maxv = CompanyClientProfile.objects.filter(
            company=company
        ).aggregate(maxv=Max('company_client_id'))
        return (maxv.get('maxv') or 0) + 1

    def _get_prefix(self, company):
        """Get company prefix for IDs."""
        try:
            return company._company_prefix()
        except Exception:
            return (company.company_name or 'CMP')[:3].upper()
