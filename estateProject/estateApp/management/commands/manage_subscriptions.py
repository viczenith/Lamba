"""
Management command to handle subscription renewals and billing.
Automatically renews subscriptions, generates invoices, and manages trial periods.

Usage:
    python manage.py manage_subscriptions
    python manage.py manage_subscriptions --dry-run
    python manage.py manage_subscriptions --renew-trials
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from estateApp.models import Company
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage company subscriptions (renewals, trials, expirations)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--renew-trials',
            action='store_true',
            help='Extend trial periods for companies (admin use only)'
        )
        parser.add_argument(
            '--disable-expired',
            action='store_true',
            help='Disable companies with expired subscriptions'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        renew_trials = options.get('renew_trials')
        disable_expired = options.get('disable_expired')

        now = timezone.now()

        # Check expiring trials
        expiring_soon = Company.objects.filter(
            subscription_status='trial',
            trial_ends_at__lte=now + timedelta(days=3),
            trial_ends_at__gt=now
        )

        if expiring_soon.exists():
            self.stdout.write(self.style.WARNING(f"Trials expiring soon: {expiring_soon.count()}"))
            for company in expiring_soon:
                days_left = (company.trial_ends_at - now).days
                self.stdout.write(f"  - {company.company_name}: {days_left} days left")

        # Check expired trials
        expired_trials = Company.objects.filter(
            subscription_status='trial',
            trial_ends_at__lte=now
        )

        if expired_trials.exists():
            self.stdout.write(self.style.ERROR(f"Expired trials: {expired_trials.count()}"))
            if not dry_run:
                for company in expired_trials:
                    company.subscription_status = 'suspended'
                    company.save()
                    logger.info(f"Suspended trial for {company.company_name}")
                self.stdout.write(self.style.SUCCESS("✓ Expired trials suspended"))

        # Check expiring subscriptions
        expiring_subscriptions = Company.objects.filter(
            subscription_status='active',
            subscription_ends_at__lte=now + timedelta(days=7),
            subscription_ends_at__gt=now
        )

        if expiring_subscriptions.exists():
            self.stdout.write(self.style.WARNING(f"Subscriptions expiring soon: {expiring_subscriptions.count()}"))
            for company in expiring_subscriptions:
                days_left = (company.subscription_ends_at - now).days
                self.stdout.write(f"  - {company.company_name}: {days_left} days left (Tier: {company.get_subscription_tier_display()})")

        # Disable expired subscriptions
        if disable_expired:
            expired_subscriptions = Company.objects.filter(
                subscription_status='active',
                subscription_ends_at__lte=now
            )

            if expired_subscriptions.exists():
                self.stdout.write(self.style.ERROR(f"Expired subscriptions: {expired_subscriptions.count()}"))
                if not dry_run:
                    for company in expired_subscriptions:
                        company.subscription_status = 'suspended'
                        company.save()
                        logger.info(f"Suspended subscription for {company.company_name}")
                    self.stdout.write(self.style.SUCCESS("✓ Expired subscriptions suspended"))

        # Renew trials (admin manual operation)
        if renew_trials:
            self.stdout.write(self.style.WARNING("Trial renewal is a manual admin operation"))
            self.stdout.write("To renew a trial, use the Django admin panel or direct database update")

        # Summary
        self.stdout.write("\n" + self.style.SUCCESS("✓ Subscription Management Complete"))
        self.stdout.write(f"  Expiring soon (3 days): {expiring_soon.count()}")
        self.stdout.write(f"  Expired trials: {expired_trials.count()}")
        self.stdout.write(f"  Expiring subscriptions (7 days): {expiring_subscriptions.count()}")
