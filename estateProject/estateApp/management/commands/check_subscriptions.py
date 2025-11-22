"""
Management command: check_subscriptions
Purpose: Check and update subscription statuses for all companies
Handles trial expiry, grace periods, read-only mode, and data deletion
Designed to run every 6 hours via cron or Celery beat
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from estateApp.models import Company, SubscriptionAlert
from estateApp.services.alerts import SubscriptionAlertService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check and update subscription statuses for all companies'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Check specific company by ID',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        company_id = options.get('company_id')
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS(f'Starting subscription checks at {timezone.now()}'))
        
        try:
            if company_id:
                # Check specific company
                company = Company.objects.get(id=company_id)
                self._check_company(company, verbose)
            else:
                # Check all companies with active or trial subscriptions
                companies = Company.objects.filter(
                    Q(subscription_status='trial') | Q(subscription_status='active') | Q(subscription_status='expired')
                )
                
                checked = 0
                updated = 0
                
                for company in companies:
                    if self._check_company(company, verbose):
                        updated += 1
                    checked += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSubscription check complete: {checked} companies checked, {updated} updated'
                    )
                )
        
        except Exception as e:
            logger.error(f"Error checking subscriptions: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
    
    def _check_company(self, company, verbose=False):
        """Check single company and update subscription status"""
        updated = False
        now = timezone.now()
        
        if verbose:
            self.stdout.write(f'\nChecking {company.company_name} (ID: {company.id})')
            self.stdout.write(f'  Status: {company.subscription_status}')
            self.stdout.write(f'  Read-only: {company.is_read_only_mode}')
        
        # 1. Check if trial has expired
        if company.subscription_status == 'trial' and company.trial_ends_at:
            if company.trial_ends_at <= now:
                if verbose:
                    self.stdout.write(self.style.WARNING('  → Trial has expired'))
                
                # Send email before expiry
                SubscriptionAlertService.send_trial_expiry_email(company)
                
                # Update status
                SubscriptionAlertService.check_and_update_trial_status(company)
                updated = True
        
        # 2. Check if grace period has expired
        if company.grace_period_ends_at:
            if company.grace_period_ends_at <= now and not company.is_read_only_mode:
                if verbose:
                    self.stdout.write(self.style.WARNING('  → Grace period expired, activating read-only mode'))
                
                SubscriptionAlertService.check_and_update_grace_period(company)
                updated = True
        
        # 3. Check if data should be deleted (30 days after grace period)
        if company.data_deletion_date:
            if company.data_deletion_date <= now and company.subscription_status == 'expired':
                if verbose:
                    self.stdout.write(self.style.ERROR('  → Executing data deletion'))
                
                SubscriptionAlertService.check_and_delete_expired_data(company)
                updated = True
        
        # 4. Generate alerts for upcoming expirations
        self._generate_upcoming_alerts(company, verbose)
        
        # 5. Refresh company alerts on dashboard
        self._refresh_company_alerts(company, verbose)
        
        return updated
    
    def _generate_upcoming_alerts(self, company, verbose=False):
        """Generate alerts for upcoming trial/subscription expirations"""
        now = timezone.now()
        
        # Check trial expiry alerts
        if company.subscription_status == 'trial' and company.trial_ends_at:
            days_remaining = (company.trial_ends_at - now).days
            
            # Create alerts for specific days
            alert_thresholds = [14, 7, 3, 1]
            
            for threshold in alert_thresholds:
                if days_remaining == threshold:
                    # Check if alert already exists for this day
                    existing = SubscriptionAlert.objects.filter(
                        company=company,
                        alert_type='trial_ending',
                        status='active',
                    ).exists()
                    
                    if not existing:
                        if verbose:
                            self.stdout.write(f'  → Creating trial ending alert ({days_remaining} days remaining)')
                        
                        alert_type = 'trial_ending'
                        severity = 'critical' if days_remaining <= 1 else 'warning'
                        
                        SubscriptionAlertService.create_subscription_alert(
                            company,
                            alert_type,
                            f'Trial Expires in {days_remaining} Day(s)',
                            f'Your trial expires in {days_remaining} day(s). Upgrade now to avoid service interruption.',
                            severity=severity,
                            action_url='/upgrade/',
                            action_label='Upgrade Now',
                            is_dismissible=(days_remaining > 1)
                        )
        
        # Check subscription renewal alerts
        if company.subscription_status == 'active' and company.subscription_ends_at:
            days_remaining = (company.subscription_ends_at - now).days
            
            # Alert 7 days before
            if days_remaining == 7:
                existing = SubscriptionAlert.objects.filter(
                    company=company,
                    alert_type='subscription_renewing',
                    status='active',
                ).exists()
                
                if not existing:
                    if verbose:
                        self.stdout.write(f'  → Creating subscription renewal alert (7 days remaining)')
                    
                    SubscriptionAlertService.create_subscription_alert(
                        company,
                        'subscription_renewing',
                        'Your Subscription Expires in 7 Days',
                        f'Your subscription will expire on {company.subscription_ends_at.strftime("%B %d, %Y")}. Renew now to avoid interruptions.',
                        severity='warning',
                        action_url='/billing/renew/',
                        action_label='Renew Subscription',
                        is_dismissible=True
                    )
    
    def _refresh_company_alerts(self, company, verbose=False):
        """Refresh company alerts (mark old ones as resolved if no longer applicable)"""
        # Mark resolved alerts as resolved if condition no longer applies
        
        if company.subscription_status == 'trial' and not company.trial_ends_at:
            # Remove trial alerts if no trial date
            SubscriptionAlert.objects.filter(
                company=company,
                alert_type='trial_ending',
                status='active',
            ).update(status='resolved')
        
        if not company.is_read_only_mode:
            # Remove read-only alerts if no longer in read-only mode
            SubscriptionAlert.objects.filter(
                company=company,
                alert_type='read_only_mode',
                status='active',
            ).update(status='resolved')
        
        if verbose:
            self.stdout.write('  → Alerts refreshed')


# ============================================================================
# CELERY BEAT TASK CONFIGURATION
# ============================================================================

# Add to estateProject/celery_app.py:
#
# from celery.schedules import crontab
#
# app.conf.beat_schedule = {
#     'check-subscriptions': {
#         'task': 'estateApp.tasks.check_subscriptions_task',
#         'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
#     },
# }

# Add to estateApp/tasks.py:
#
# from celery import shared_task
# from django.core.management import call_command
#
# @shared_task(bind=True)
# def check_subscriptions_task(self):
#     """Celery task to check subscriptions every 6 hours"""
#     call_command('check_subscriptions', verbose=True)
#     return "Subscription check completed"


# ============================================================================
# CRON JOB CONFIGURATION (Alternative to Celery)
# ============================================================================

# Add to crontab:
# 0 */6 * * * cd /path/to/project && python manage.py check_subscriptions --verbose >> /var/log/subscription_checks.log 2>&1
# This runs every 6 hours at 00:00, 06:00, 12:00, 18:00
