"""
Management command to initialize subscription plans
"""
from django.core.management.base import BaseCommand
from superAdmin.models import SubscriptionPlan, PlatformConfiguration


class Command(BaseCommand):
    help = 'Initialize default subscription plans'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating subscription plans...')
        
        # Get platform config for pricing
        config = PlatformConfiguration.get_config()
        
        # Trial Plan
        trial_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='trial',
            defaults={
                'name': 'Trial Plan',
                'description': '14-day free trial with limited features',
                'monthly_price': 0,
                'annual_price': 0,
                'setup_fee': 0,
                'max_plots': 10,
                'max_agents': 2,
                'max_admins': 1,
                'max_api_calls_daily': 1000,
                'max_storage_gb': 1,
                'features': {
                    'basic_features': True,
                    'advanced_analytics': False,
                    'api_access': True,
                    'custom_domain': False,
                    'white_label': False,
                    'priority_support': False,
                },
                'is_active': True,
                'is_visible': False,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Trial Plan {"created" if created else "exists"}'))
        
        # Starter Plan
        starter_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='starter',
            defaults={
                'name': 'Starter',
                'description': 'Perfect for small real estate agencies getting started',
                'monthly_price': config.starter_price,
                'annual_price': config.starter_price * 10,  # 2 months free
                'setup_fee': 0,
                'max_plots': 50,
                'max_agents': 5,
                'max_admins': 2,
                'max_api_calls_daily': 5000,
                'max_storage_gb': 5,
                'features': {
                    'basic_features': True,
                    'advanced_analytics': False,
                    'api_access': True,
                    'custom_domain': False,
                    'white_label': False,
                    'priority_support': False,
                    'email_support': True,
                },
                'is_active': True,
                'is_visible': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Starter Plan {"created" if created else "exists"}'))
        
        # Professional Plan
        pro_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='professional',
            defaults={
                'name': 'Professional',
                'description': 'For growing agencies with advanced needs',
                'monthly_price': config.professional_price,
                'annual_price': config.professional_price * 10,
                'setup_fee': 0,
                'max_plots': 500,
                'max_agents': 20,
                'max_admins': 5,
                'max_api_calls_daily': 20000,
                'max_storage_gb': 20,
                'features': {
                    'basic_features': True,
                    'advanced_analytics': True,
                    'api_access': True,
                    'custom_domain': True,
                    'white_label': False,
                    'priority_support': True,
                    'email_support': True,
                    'phone_support': True,
                    'webhook_integration': True,
                },
                'is_active': True,
                'is_visible': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Professional Plan {"created" if created else "exists"}'))
        
        # Enterprise Plan
        enterprise_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='enterprise',
            defaults={
                'name': 'Enterprise',
                'description': 'Unlimited everything for large organizations',
                'monthly_price': config.enterprise_price,
                'annual_price': config.enterprise_price * 10,
                'setup_fee': 50000,  # ₦50,000 setup
                'max_plots': 0,  # Unlimited
                'max_agents': 0,  # Unlimited
                'max_admins': 0,  # Unlimited
                'max_api_calls_daily': 0,  # Unlimited
                'max_storage_gb': 0,  # Unlimited
                'features': {
                    'basic_features': True,
                    'advanced_analytics': True,
                    'api_access': True,
                    'custom_domain': True,
                    'white_label': True,
                    'priority_support': True,
                    'email_support': True,
                    'phone_support': True,
                    'dedicated_support': True,
                    'webhook_integration': True,
                    'sso': True,
                    'custom_integrations': True,
                    'sla_guarantee': True,
                },
                'is_active': True,
                'is_visible': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Enterprise Plan {"created" if created else "exists"}'))
        
        # Custom Plan (for special negotiations)
        custom_plan, created = SubscriptionPlan.objects.get_or_create(
            tier='custom',
            defaults={
                'name': 'Custom',
                'description': 'Tailored solution for specific requirements',
                'monthly_price': 0,  # Negotiated
                'annual_price': 0,
                'setup_fee': 0,
                'max_plots': 0,
                'max_agents': 0,
                'max_admins': 0,
                'max_api_calls_daily': 0,
                'max_storage_gb': 0,
                'features': {},  # Customized
                'is_active': True,
                'is_visible': False,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Custom Plan {"created" if created else "exists"}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ All subscription plans initialized!'))
