"""
Management command to update subscription plans with correct pricing and limits.
"""
from django.core.management.base import BaseCommand
from estateApp.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Update subscription plans with correct pricing and limits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Define the correct subscription plans
        plans_data = [
            {
                'tier': 'starter',
                'name': 'Starter',
                'description': 'For Small Companies - Perfect for getting started',
                'monthly_price': 70000,
                'annual_price': 700000,  # Save 2 months
                'max_plots': 2,  # 2 Estate Properties
                'max_agents': 50,  # 30 Clients & 20 Affiliates = 50 total
                'max_api_calls_daily': 500,
                'features': {
                    'estate_properties': 2,
                    'allocations': 30,
                    'clients': 30,
                    'affiliates': 20,
                    'basic_support': True,
                    'email_notifications': True,
                    'basic_reports': True,
                    'api_access': False,
                    'advanced_analytics': False,
                    'priority_support': False,
                    'custom_branding': False,
                },
                'is_active': True,
            },
            {
                'tier': 'professional',
                'name': 'Professional',
                'description': 'For Growing Companies - Scale your business',
                'monthly_price': 100000,
                'annual_price': 1000000,  # Save 2 months
                'max_plots': 5,  # 5 Estate Properties
                'max_agents': 110,  # 80 Clients & 30 Affiliates = 110 total
                'max_api_calls_daily': 2000,
                'features': {
                    'estate_properties': 5,
                    'allocations': 80,
                    'clients': 80,
                    'affiliates': 30,
                    'basic_support': True,
                    'email_notifications': True,
                    'basic_reports': True,
                    'advanced_reports': True,
                    'api_access': True,
                    'advanced_analytics': True,
                    'priority_support': False,
                    'custom_branding': False,
                },
                'is_active': True,
            },
            {
                'tier': 'enterprise',
                'name': 'Enterprise',
                'description': 'Preferred Package Plan - Unlimited everything for large organizations',
                'monthly_price': 150000,
                'annual_price': 1500000,  # Save 2 months
                'max_plots': 999999,  # Unlimited Estate Properties
                'max_agents': 999999,  # Unlimited Clients & Affiliates
                'max_api_calls_daily': 999999,  # Unlimited API calls
                'features': {
                    'estate_properties': 'unlimited',
                    'allocations': 'unlimited',
                    'clients': 'unlimited',
                    'affiliates': 'unlimited',
                    'basic_support': True,
                    'email_notifications': True,
                    'basic_reports': True,
                    'advanced_reports': True,
                    'api_access': True,
                    'advanced_analytics': True,
                    'priority_support': True,
                    'custom_branding': True,
                    'dedicated_account_manager': True,
                    'white_label': True,
                    'sla_guarantee': True,
                },
                'is_active': True,
            },
        ]
        
        self.stdout.write(self.style.NOTICE('\n' + '=' * 60))
        self.stdout.write(self.style.NOTICE('SUBSCRIPTION PLANS UPDATE'))
        self.stdout.write(self.style.NOTICE('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] No changes will be made.\n'))
        
        for plan_data in plans_data:
            tier = plan_data['tier']
            
            try:
                plan, created = SubscriptionPlan.objects.get_or_create(
                    tier=tier,
                    defaults=plan_data
                )
                
                if created:
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] Would CREATE: {plan_data["name"]}')
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ CREATED: {plan.name} - ₦{plan.monthly_price:,.0f}/mo'))
                else:
                    # Update existing plan
                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] Would UPDATE: {plan.name}')
                        self.stdout.write(f'    - Price: ₦{plan.monthly_price:,.0f} → ₦{plan_data["monthly_price"]:,.0f}')
                        self.stdout.write(f'    - Max Estates: {plan.max_plots} → {plan_data["max_plots"]}')
                    else:
                        plan.name = plan_data['name']
                        plan.description = plan_data['description']
                        plan.monthly_price = plan_data['monthly_price']
                        plan.annual_price = plan_data['annual_price']
                        plan.max_plots = plan_data['max_plots']
                        plan.max_agents = plan_data['max_agents']
                        plan.max_api_calls_daily = plan_data['max_api_calls_daily']
                        plan.features = plan_data['features']
                        plan.is_active = plan_data['is_active']
                        plan.save()
                        
                        self.stdout.write(self.style.SUCCESS(f'  ✓ UPDATED: {plan.name}'))
                        self.stdout.write(f'    - Monthly: ₦{plan.monthly_price:,.0f}')
                        self.stdout.write(f'    - Annual: ₦{plan.annual_price:,.0f} (Save 2 months!)')
                        self.stdout.write(f'    - Estates: {plan.max_plots if plan.max_plots < 999999 else "Unlimited"}')
                        self.stdout.write(f'    - Clients & Affiliates: {plan.max_agents if plan.max_agents < 999999 else "Unlimited"}')
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ ERROR with {tier}: {str(e)}'))
        
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] No changes were made.'))
        else:
            self.stdout.write(self.style.SUCCESS('Subscription plans updated successfully!'))
        self.stdout.write('=' * 60 + '\n')
