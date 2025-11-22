"""
Super Admin Signals - Auto-create related models
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from estateApp.models import Company
from .models import CompanySubscription, CompanyOnboarding, SubscriptionPlan


@receiver(post_save, sender=Company)
def create_company_subscription(sender, instance, created, **kwargs):
    """Auto-create subscription and onboarding when company is created"""
    if created:
        # Get or create trial plan
        trial_plan, _ = SubscriptionPlan.objects.get_or_create(
            tier='trial',
            defaults={
                'name': 'Trial Plan',
                'description': '14-day free trial',
                'monthly_price': 0,
                'annual_price': 0,
                'max_plots': 10,
                'max_agents': 2,
                'max_api_calls_daily': 1000,
                'features': {
                    'basic_features': True,
                    'advanced_analytics': False,
                    'api_access': True,
                }
            }
        )
        
        # Create subscription
        trial_ends = timezone.now() + timedelta(days=14)
        CompanySubscription.objects.get_or_create(
            company=instance,
            defaults={
                'plan': trial_plan,
                'billing_cycle': 'trial',
                'payment_status': 'active',
                'current_period_start': timezone.now(),
                'current_period_end': trial_ends,
                'trial_ends_at': trial_ends,
            }
        )
        
        # Create onboarding tracker
        CompanyOnboarding.objects.get_or_create(
            company=instance,
            defaults={
                'current_step': 'registration',
                'steps_completed': ['registration'],
                'completion_percentage': 12,  # 1 out of 8 steps
            }
        )
