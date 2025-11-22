"""
Management command to set up Enterprise trial subscription for a company.
Configures a company with 14-day Enterprise trial with unlimited features.

Usage:
    python manage.py setup_enterprise_trial [company_id]
    python manage.py setup_enterprise_trial --company-name "Company Name"
    python manage.py setup_enterprise_trial --first
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from estateApp.models import Company, SubscriptionPlan
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up 14-day Enterprise trial subscription for a company with unlimited features'

    def add_arguments(self, parser):
        parser.add_argument(
            'company_id',
            type=int,
            nargs='?',
            help='ID of company to set up trial for (optional if --company-name or --first provided)'
        )
        parser.add_argument(
            '--company-name',
            type=str,
            help='Name of company to set up trial for'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of trial days (default: 14)'
        )
        parser.add_argument(
            '--first',
            action='store_true',
            help='Set up trial for the first company in database'
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        company_name = options.get('company_name')
        days = options.get('days', 14)
        use_first = options.get('first', False)

        # Determine which company to use
        company = None
        
        if use_first:
            company = Company.objects.first()
            if not company:
                raise CommandError('No companies found in database')
            self.stdout.write(self.style.SUCCESS(f'✓ Using first company: {company.company_name} (ID: {company.id})'))
        elif company_id:
            try:
                company = Company.objects.get(id=company_id)
                self.stdout.write(self.style.SUCCESS(f'✓ Using company ID: {company_id}'))
            except Company.DoesNotExist:
                raise CommandError(f'Company with ID {company_id} not found')
        elif company_name:
            try:
                company = Company.objects.get(company_name__iexact=company_name)
                self.stdout.write(self.style.SUCCESS(f'✓ Found company: {company.company_name} (ID: {company.id})'))
            except Company.DoesNotExist:
                raise CommandError(f'Company with name "{company_name}" not found')
        else:
            raise CommandError(
                'Please provide: company_id, --company-name, or --first\n'
                'Example: python manage.py setup_enterprise_trial 1\n'
                'Or: python manage.py setup_enterprise_trial --company-name "My Company"\n'
                'Or: python manage.py setup_enterprise_trial --first'
            )

        if not company:
            raise CommandError('Could not determine company')

        # Get or create Enterprise plan
        try:
            enterprise_plan = SubscriptionPlan.objects.get(tier='enterprise')
            self.stdout.write(self.style.SUCCESS(f'✓ Found Enterprise plan: {enterprise_plan.name}'))
        except SubscriptionPlan.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Enterprise plan not found in database'))
            self.stdout.write('Creating Enterprise plan with unlimited features...')
            
            enterprise_plan = SubscriptionPlan.objects.create(
                tier='enterprise',
                name='Enterprise',
                description='Enterprise plan with unlimited features - perfect for large real estate operations',
                monthly_price=100000.00,  # ₦100,000/month
                annual_price=1000000.00,  # ₦1,000,000/year (2 months free)
                max_plots=999999,  # Effectively unlimited
                max_agents=999999,  # Effectively unlimited
                max_api_calls_daily=999999,  # Effectively unlimited
                features={
                    'unlimited_plots': True,
                    'unlimited_agents': True,
                    'unlimited_api_calls': True,
                    'advanced_analytics': True,
                    'priority_support': True,
                    'custom_branding': True,
                    'api_access': True,
                    'white_label': True,
                    'advanced_reports': True,
                    'multi_location': True,
                },
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS('✓ Enterprise plan created successfully'))

        # Configure company for Enterprise trial
        now = timezone.now()
        trial_ends_at = now + timedelta(days=days)

        old_status = company.subscription_status
        old_tier = company.subscription_tier

        company.subscription_tier = 'enterprise'
        company.subscription_status = 'trial'
        company.trial_ends_at = trial_ends_at
        company.subscription_started_at = now
        company.subscription_ends_at = trial_ends_at
        company.subscription_renewed_at = now
        
        # Set unlimited limits (999999 = effectively unlimited)
        company.max_plots = 999999
        company.max_agents = 999999
        company.max_api_calls_daily = 999999

        company.save()

        # Output beautiful summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('  🎉 ENTERPRISE TRIAL SETUP COMPLETE! 🎉'))
        self.stdout.write('='*70 + '\n')
        
        self.stdout.write(self.style.SUCCESS('📊 COMPANY INFORMATION'))
        self.stdout.write(f'   Company Name: {company.company_name}')
        self.stdout.write(f'   Company ID: {company.id}')
        self.stdout.write(f'   Email: {company.email}\n')
        
        self.stdout.write(self.style.SUCCESS('📈 SUBSCRIPTION CHANGES'))
        self.stdout.write(f'   Status: {old_status} → {self.style.SUCCESS(company.subscription_status.upper())}')
        self.stdout.write(f'   Tier: {old_tier} → {self.style.SUCCESS(company.subscription_tier.upper())}\n')
        
        self.stdout.write(self.style.SUCCESS('📅 TRIAL INFORMATION'))
        self.stdout.write(f'   Trial Start: {now.strftime("%B %d, %Y at %H:%M:%S")}')
        self.stdout.write(f'   Trial Ends: {trial_ends_at.strftime("%B %d, %Y at %H:%M:%S")}')
        self.stdout.write(f'   Duration: {days} days\n')
        
        self.stdout.write(self.style.SUCCESS('🚀 UNLIMITED FEATURES'))
        self.stdout.write(f'   ✓ Max Plots: {company.max_plots:,} (UNLIMITED)')
        self.stdout.write(f'   ✓ Max Agents: {company.max_agents:,} (UNLIMITED)')
        self.stdout.write(f'   ✓ Max API Calls/Day: {company.max_api_calls_daily:,} (UNLIMITED)')
        self.stdout.write(f'   ✓ Advanced Analytics: Enabled')
        self.stdout.write(f'   ✓ Priority Support: Enabled')
        self.stdout.write(f'   ✓ Custom Branding: Enabled')
        self.stdout.write(f'   ✓ API Access: Enabled')
        self.stdout.write(f'   ✓ White Label: Enabled\n')
        
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS('  ✓ Company is now ready for Enterprise trial testing!'))
        self.stdout.write('='*70 + '\n')
        
        logger.info(f'Enterprise trial configured for company {company.id} ({company.company_name})')
