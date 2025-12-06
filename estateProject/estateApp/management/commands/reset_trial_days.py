"""
Management command to reset trial days for all companies.
This command sets trial_ends_at to 14 days from today for all companies.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from estateApp.models import Company


class Command(BaseCommand):
    help = 'Reset trial period for all companies to 14 days from today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of trial days to set (default: 14)'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Specific company ID to update (optional, updates all if not provided)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        trial_days = options['days']
        company_id = options.get('company_id')
        dry_run = options['dry_run']
        
        now = timezone.now()
        new_trial_ends_at = now + timedelta(days=trial_days)
        
        # Get companies to update
        if company_id:
            companies = Company.objects.filter(id=company_id)
        else:
            companies = Company.objects.all()
        
        if not companies.exists():
            self.stdout.write(self.style.WARNING('No companies found to update.'))
            return
        
        self.stdout.write(self.style.NOTICE(f'\n{"=" * 60}'))
        self.stdout.write(self.style.NOTICE('TRIAL DAYS RESET COMMAND'))
        self.stdout.write(self.style.NOTICE(f'{"=" * 60}'))
        self.stdout.write(f'Current Date/Time: {now.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Trial Duration: {trial_days} days')
        self.stdout.write(f'New Trial End Date: {new_trial_ends_at.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Companies to update: {companies.count()}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes will be made.\n'))
        
        updated_count = 0
        
        for company in companies:
            old_trial_ends = company.trial_ends_at
            old_status = company.subscription_status
            
            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would update "{company.company_name}": '
                    f'trial_ends_at: {old_trial_ends} → {new_trial_ends_at}, '
                    f'status: {old_status} → trial'
                )
            else:
                # Update trial dates and status
                company.trial_ends_at = new_trial_ends_at
                company.subscription_ends_at = new_trial_ends_at
                company.subscription_started_at = now
                company.subscription_status = 'trial'
                company.is_read_only_mode = False
                company.grace_period_ends_at = None
                company.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated "{company.company_name}": '
                        f'trial_ends_at → {new_trial_ends_at.strftime("%Y-%m-%d")}'
                    )
                )
                updated_count += 1
        
        self.stdout.write(f'\n{"=" * 60}')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] {companies.count()} companies would be updated.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} companies!'))
        self.stdout.write(f'{"=" * 60}\n')
