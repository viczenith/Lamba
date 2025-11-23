"""
Management Command: Ensure all companies have subscription plans
Automatically creates 14-day free trial subscriptions for companies without plans
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from estateApp.models import Company, SubscriptionPlan
from estateApp.subscription_billing_models import SubscriptionBillingModel
from decimal import Decimal


class Command(BaseCommand):
    help = 'Ensure all companies have subscription plans with 14-day free trial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--plan',
            type=str,
            default='professional',
            help='Subscription plan tier to assign (starter, professional, enterprise)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Override existing subscriptions (use with caution)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        plan_tier = options['plan']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SUBSCRIPTION PLAN ENFORCEMENT'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN MODE - No changes will be made\n'))
        
        # Get or create the default plan
        try:
            default_plan = SubscriptionPlan.objects.get(tier=plan_tier)
            self.stdout.write(self.style.SUCCESS(f'✓ Using plan: {default_plan.name} ({plan_tier})'))
        except SubscriptionPlan.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Plan "{plan_tier}" not found'))
            self.stdout.write(self.style.WARNING('Available plans:'))
            for plan in SubscriptionPlan.objects.all():
                self.stdout.write(f'  - {plan.name} ({plan.tier})')
            return
        
        # Get all companies
        all_companies = Company.objects.all()
        self.stdout.write(f'📊 Total companies: {all_companies.count()}\n')
        
        # Separate companies into categories
        companies_without_subscription = []
        companies_with_trial = []
        companies_with_active = []
        
        for company in all_companies:
            try:
                billing = SubscriptionBillingModel.objects.get(company=company)
                if billing.status == 'trial':
                    companies_with_trial.append((company, billing))
                else:
                    companies_with_active.append((company, billing))
            except SubscriptionBillingModel.DoesNotExist:
                companies_without_subscription.append(company)
        
        # Display status
        self.stdout.write(self.style.SUCCESS(f'✅ With active subscriptions: {len(companies_with_active)}'))
        self.stdout.write(self.style.WARNING(f'⏳ With trial subscriptions: {len(companies_with_trial)}'))
        self.stdout.write(self.style.ERROR(f'❌ WITHOUT subscriptions: {len(companies_without_subscription)}\n'))
        
        # Process companies without subscriptions
        if companies_without_subscription:
            self.stdout.write(self.style.WARNING(f'Processing {len(companies_without_subscription)} companies...\n'))
            
            created_count = 0
            for company in companies_without_subscription:
                # Calculate trial period
                trial_ends = timezone.now() + timedelta(days=14)
                
                if not dry_run:
                    # Create subscription billing record
                    billing, created = SubscriptionBillingModel.objects.get_or_create(
                        company=company,
                        defaults={
                            'current_plan': default_plan,
                            'status': 'trial',
                            'payment_method': 'free_trial',
                            'trial_started_at': timezone.now(),
                            'trial_ends_at': trial_ends,
                            'billing_cycle': 'monthly',
                            'auto_renew': False,
                            'monthly_amount': Decimal('0.00'),
                            'annual_amount': Decimal('0.00'),
                        }
                    )
                    
                    # Update company trial dates if not already set
                    if not company.trial_ends_at:
                        company.trial_ends_at = trial_ends
                        company.subscription_status = 'trial'
                        company.subscription_tier = plan_tier
                        company.save()
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {company.company_name}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'ℹ️  {company.company_name} (already had record)')
                        )
                else:
                    self.stdout.write(f'[DRY RUN] Would create subscription for: {company.company_name}')
                    created_count += 1
            
            self.stdout.write('')
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ Successfully created {created_count} subscriptions')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'\n[DRY RUN] Would create {created_count} subscriptions')
                )
        else:
            self.stdout.write(self.style.SUCCESS('✅ All companies already have subscriptions!\n'))
        
        # Final summary
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS('ENFORCEMENT COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
