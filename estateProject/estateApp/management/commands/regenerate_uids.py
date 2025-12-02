from django.core.management.base import BaseCommand
from django.db import transaction
from estateApp.models import (
    ClientUser, MarketerUser, Company, 
    ClientMarketerAssignment, MarketerAffiliation,
    CompanyClientProfile, CompanyMarketerProfile,
    CompanySequence
)


class Command(BaseCommand):
    help = "Regenerate all UIDs using existing logic and CompanySequence"

    def handle(self, *args, **options):
        self.stdout.write("=" * 100)
        self.stdout.write(self.style.SUCCESS("REGENERATING UIDs USING EXISTING LOGIC + CompanySequence"))
        self.stdout.write("=" * 100)

        # Clear company profiles to regenerate
        self.stdout.write("\n▶ Clearing existing CompanyClientProfile and CompanyMarketerProfile...")
        CompanyClientProfile.objects.all().delete()
        CompanyMarketerProfile.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("  ✓ Cleared"))

        # Clear CompanySequence to restart from 1
        self.stdout.write("\n▶ Resetting CompanySequence...")
        CompanySequence.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("  ✓ Reset"))

        companies = Company.objects.all()

        for company in companies:
            self.stdout.write("\n" + "=" * 100)
            self.stdout.write(f"COMPANY: {company.company_name}")
            self.stdout.write("=" * 100)

            prefix = company._company_prefix()
            self.stdout.write(f"  Prefix: {prefix}")

            # ========== CLIENTS ==========
            self.stdout.write(f"\n▶ REGENERATING CLIENT UIDs:")

            # Get all clients: direct + affiliated
            direct_client_ids = list(
                ClientUser.objects.filter(company_profile=company).values_list('id', flat=True)
            )
            affiliated_client_ids = list(
                ClientMarketerAssignment.objects.filter(company=company)
                .values_list('client_id', flat=True)
                .distinct()
            )
            all_client_ids = sorted(set(direct_client_ids + affiliated_client_ids))

            if not all_client_ids:
                self.stdout.write(f"  (no clients)")
            else:
                for client_id in all_client_ids:
                    client = ClientUser.objects.get(id=client_id)

                    # Get next sequential ID using CompanySequence
                    seq_id = CompanySequence.get_next(company, 'client')

                    # Generate UID using the same logic as the model
                    new_uid = f"{prefix}CLT{int(seq_id):03d}"

                    # Check uniqueness (if collision, add company ID)
                    if ClientUser.objects.filter(company_client_uid=new_uid).exclude(id=client.id).exists() or \
                       CompanyClientProfile.objects.filter(company_client_uid=new_uid).exclude(client_id=client.id).exists():
                        new_uid = f"{prefix}{company.id}CLT{int(seq_id):03d}"

                    # Create CompanyClientProfile
                    profile, created = CompanyClientProfile.objects.get_or_create(
                        client=client,
                        company=company,
                        defaults={
                            'company_client_id': seq_id,
                            'company_client_uid': new_uid
                        }
                    )

                    # Update ClientUser field too
                    if not client.company_client_uid or client.company_client_uid != new_uid:
                        client.company_client_uid = new_uid
                        client.company_client_id = seq_id
                        client.save(update_fields=['company_client_uid', 'company_client_id'])

                    self.stdout.write(f"  ✓ {new_uid:20} - {client.full_name}")

            # ========== MARKETERS ==========
            self.stdout.write(f"\n▶ REGENERATING MARKETER UIDs:")

            # Get all marketers: direct + affiliated
            direct_marketer_ids = list(
                MarketerUser.objects.filter(company_profile=company).values_list('id', flat=True)
            )
            affiliated_marketer_ids = list(
                MarketerAffiliation.objects.filter(company=company)
                .values_list('marketer_id', flat=True)
                .distinct()
            )
            all_marketer_ids = sorted(set(direct_marketer_ids + affiliated_marketer_ids))

            if not all_marketer_ids:
                self.stdout.write(f"  (no marketers)")
            else:
                for marketer_id in all_marketer_ids:
                    marketer = MarketerUser.objects.get(id=marketer_id)

                    # Get next sequential ID using CompanySequence
                    seq_id = CompanySequence.get_next(company, 'marketer')

                    # Generate UID using the same logic as the model
                    new_uid = f"{prefix}MKT{int(seq_id):03d}"

                    # Check uniqueness (if collision, add company ID)
                    if MarketerUser.objects.filter(company_marketer_uid=new_uid).exclude(id=marketer.id).exists() or \
                       CompanyMarketerProfile.objects.filter(company_marketer_uid=new_uid).exclude(marketer_id=marketer.id).exists():
                        new_uid = f"{prefix}{company.id}MKT{int(seq_id):03d}"

                    # Create CompanyMarketerProfile
                    profile, created = CompanyMarketerProfile.objects.get_or_create(
                        marketer=marketer,
                        company=company,
                        defaults={
                            'company_marketer_id': seq_id,
                            'company_marketer_uid': new_uid
                        }
                    )

                    # Update MarketerUser field too
                    if not marketer.company_marketer_uid or marketer.company_marketer_uid != new_uid:
                        marketer.company_marketer_uid = new_uid
                        marketer.company_marketer_id = seq_id
                        marketer.save(update_fields=['company_marketer_uid', 'company_marketer_id'])

                    self.stdout.write(f"  ✓ {new_uid:20} - {marketer.full_name}")

        self.stdout.write("\n" + "=" * 100)
        self.stdout.write(self.style.SUCCESS("FINAL VERIFICATION"))
        self.stdout.write("=" * 100)

        for company in companies:
            self.stdout.write(f"\n{company.company_name}:")

            # Client profiles
            client_profiles = CompanyClientProfile.objects.filter(company=company).order_by('company_client_id')
            if client_profiles.exists():
                self.stdout.write(f"  Clients:")
                for p in client_profiles:
                    self.stdout.write(f"    ✓ {p.company_client_uid:20} - {p.client.full_name}")

            # Marketer profiles
            marketer_profiles = CompanyMarketerProfile.objects.filter(company=company).order_by('company_marketer_id')
            if marketer_profiles.exists():
                self.stdout.write(f"  Marketers:")
                for p in marketer_profiles:
                    self.stdout.write(f"    ✓ {p.company_marketer_uid:20} - {p.marketer.full_name}")

        self.stdout.write("\n" + "=" * 100)
        self.stdout.write(self.style.SUCCESS("✅ ALL UIDs PROPERLY REGENERATED!"))
        self.stdout.write("=" * 100)
