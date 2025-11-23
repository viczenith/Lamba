"""
Email Notification System for Subscription Management
Sends subscription warnings, renewal reminders, and billing notifications
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SubscriptionEmailNotifications:
    """Handle all subscription-related email notifications"""
    
    @staticmethod
    def send_trial_expiring_email(company, days_remaining):
        """Send email when trial is expiring"""
        
        subject = f"Your {company.company_name} trial expires in {days_remaining} days"
        
        context = {
            'company_name': company.company_name,
            'days_remaining': days_remaining,
            'admin_email': company.admin.email if company.admin else 'support@lamba.com',
            'dashboard_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/",
            'upgrade_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/upgrade/",
        }
        
        if days_remaining == 7:
            template_name = 'emails/trial_ending_7days.html'
            context['message'] = f"Your 14-day trial ends in one week. Upgrade now to keep your account active."
            context['urgency'] = 'low'
        elif days_remaining == 2:
            template_name = 'emails/trial_ending_2days.html'
            context['message'] = "Only 2 days left! Upgrade now to avoid service interruption."
            context['urgency'] = 'high'
            context['cta_text'] = 'Upgrade Now'
        else:
            template_name = 'emails/trial_ending_generic.html'
            context['message'] = f"Your trial ends in {days_remaining} days."
            context['urgency'] = 'medium'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_grace_period_email(company, days_remaining):
        """Send email when in grace period"""
        
        subject = f"URGENT: {company.company_name} subscription expired - Limited access active"
        
        context = {
            'company_name': company.company_name,
            'days_remaining': days_remaining,
            'urgency': 'critical',
            'message': f"Your subscription expired. You have {days_remaining} days to renew and restore full access.",
            'dashboard_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/",
            'renew_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/renew/",
            'cta_text': 'Renew Subscription',
        }
        
        template_name = 'emails/grace_period_active.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_subscription_expired_email(company):
        """Send email when subscription fully expires"""
        
        subject = f"Account {company.company_name} - Subscription Expired"
        
        context = {
            'company_name': company.company_name,
            'urgency': 'critical',
            'message': 'Your subscription has expired. All features are now disabled.',
            'dashboard_url': f"{settings.SITE_URL}/admin/company/{company.slug}/",
            'renew_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/renew/",
            'cta_text': 'Renew Now to Restore Access',
        }
        
        template_name = 'emails/subscription_expired.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_subscription_renewed_email(company, new_end_date):
        """Send confirmation email when subscription renewed"""
        
        subject = f"✓ {company.company_name} - Subscription Renewed"
        
        context = {
            'company_name': company.company_name,
            'new_end_date': new_end_date.strftime('%B %d, %Y'),
            'urgency': 'low',
            'message': 'Your subscription has been successfully renewed!',
            'dashboard_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/",
        }
        
        template_name = 'emails/subscription_renewed.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_upgrade_confirmation_email(company, old_tier, new_tier, new_features):
        """Send confirmation email when plan upgraded"""
        
        subject = f"✓ {company.company_name} - Plan Upgraded to {new_tier.title()}"
        
        context = {
            'company_name': company.company_name,
            'old_tier': old_tier.title(),
            'new_tier': new_tier.title(),
            'new_features': new_features,
            'urgency': 'low',
            'message': f'Your plan has been upgraded from {old_tier} to {new_tier}!',
            'dashboard_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/",
        }
        
        template_name = 'emails/upgrade_confirmation.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_invoice_email(company, invoice_data):
        """Send invoice email"""
        
        subject = f"Invoice #{invoice_data['invoice_number']} - {company.company_name}"
        
        context = {
            'company_name': company.company_name,
            'invoice_number': invoice_data['invoice_number'],
            'amount': f"₦{invoice_data['amount']:,.0f}",
            'due_date': invoice_data['due_date'].strftime('%B %d, %Y'),
            'plan': invoice_data['plan'],
            'billing_cycle': invoice_data['billing_cycle'],
            'urgency': 'low',
        }
        
        template_name = 'emails/invoice.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_payment_failed_email(company, error_message):
        """Send payment failure notification"""
        
        subject = f"⚠ {company.company_name} - Payment Failed"
        
        context = {
            'company_name': company.company_name,
            'error_message': error_message,
            'urgency': 'high',
            'message': 'Your payment could not be processed. Please try again.',
            'retry_url': f"{settings.SITE_URL}/admin/company/{company.slug}/subscription/renew/",
            'cta_text': 'Try Payment Again',
        }
        
        template_name = 'emails/payment_failed.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def send_refund_processed_email(company, refund_amount):
        """Send refund confirmation email"""
        
        subject = f"✓ {company.company_name} - Refund Processed"
        
        context = {
            'company_name': company.company_name,
            'refund_amount': f"₦{refund_amount:,.2f}",
            'urgency': 'low',
            'message': 'Your refund has been processed.',
            'dashboard_url': f"{settings.SITE_URL}/admin/company/{company.slug}/billing/history/",
        }
        
        template_name = 'emails/refund_processed.html'
        
        SubscriptionEmailNotifications._send_email(
            subject,
            template_name,
            context,
            company.admin.email if company.admin else 'noreply@lamba.com'
        )
    
    @staticmethod
    def _send_email(subject, template_name, context, recipient_email):
        """Internal method to send email"""
        try:
            # Add default context variables
            context['site_name'] = 'LAMBA'
            context['site_url'] = settings.SITE_URL
            context['support_email'] = getattr(settings, 'SUPPORT_EMAIL', 'support@lamba.com')
            context['current_year'] = timezone.now().year
            
            # Render HTML and plain text versions
            html_content = render_to_string(template_name, context)
            text_content = f"Email from {context['site_name']}: {context.get('message', '')}"
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            
            # Attach HTML version
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send(fail_silently=False)
            
            logger.info(f"Email sent to {recipient_email}: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")


# ============================================================================
# CELERY TASKS FOR AUTOMATED EMAILS
# ============================================================================

from celery import shared_task

@shared_task
def send_subscription_warnings():
    """
    Celery task to check subscriptions and send warning emails
    Schedule: Daily (e.g., 9:00 AM)
    """
    from estateApp.subscription_billing_models import SubscriptionBillingModel
    
    now = timezone.now()
    
    # Check for subscriptions expiring in 7, 4, and 2 days
    for days in [7, 4, 2]:
        target_date = (now + timedelta(days=days)).date()
        
        billings = SubscriptionBillingModel.objects.filter(
            subscription_ends_at__date=target_date,
            status__in=['active', 'trial']
        )
        
        for billing in billings:
            try:
                SubscriptionEmailNotifications.send_trial_expiring_email(
                    billing.company,
                    days
                )
            except Exception as e:
                logger.error(f"Failed to send warning for {billing.company.id}: {str(e)}")

@shared_task
def activate_grace_periods():
    """
    Celery task to activate grace periods for expired subscriptions
    Schedule: Hourly
    """
    from estateApp.subscription_billing_models import SubscriptionBillingModel
    
    now = timezone.now()
    
    # Find just-expired subscriptions
    expired = SubscriptionBillingModel.objects.filter(
        subscription_ends_at__lt=now,
        status='active'
    )
    
    for billing in expired:
        try:
            if not billing.is_grace_period():
                billing.start_grace_period()
                SubscriptionEmailNotifications.send_grace_period_email(
                    billing.company,
                    7
                )
        except Exception as e:
            logger.error(f"Failed to activate grace period for {billing.company.id}: {str(e)}")

@shared_task
def expire_grace_periods():
    """
    Celery task to fully expire subscriptions after grace period
    Schedule: Daily
    """
    from estateApp.subscription_billing_models import SubscriptionBillingModel
    
    now = timezone.now()
    
    # Find grace periods that have ended
    expired_grace = SubscriptionBillingModel.objects.filter(
        grace_period_ends_at__lt=now,
        status='grace'
    )
    
    for billing in expired_grace:
        try:
            billing.status = 'expired'
            billing.save()
            SubscriptionEmailNotifications.send_subscription_expired_email(billing.company)
        except Exception as e:
            logger.error(f"Failed to expire grace period for {billing.company.id}: {str(e)}")

@shared_task
def send_grace_period_reminders():
    """
    Celery task to send daily grace period reminders
    Schedule: Daily (9:00 AM)
    """
    from estateApp.subscription_billing_models import SubscriptionBillingModel
    
    now = timezone.now()
    
    # Find subscriptions in grace period
    in_grace = SubscriptionBillingModel.objects.filter(
        status='grace',
        grace_period_ends_at__gt=now
    )
    
    for billing in in_grace:
        try:
            days_left = (billing.grace_period_ends_at - now).days
            SubscriptionEmailNotifications.send_grace_period_email(
                billing.company,
                days_left
            )
        except Exception as e:
            logger.error(f"Failed to send grace reminder for {billing.company.id}: {str(e)}")


# ============================================================================
# SETTINGS.PY CONFIGURATION
# ============================================================================

"""
Add to settings.py:

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@lamba.com')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@lamba.com')

# Site Configuration
SITE_URL = os.getenv('SITE_URL', 'https://lamba.com')

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

CELERY_BEAT_SCHEDULE = {
    'send_subscription_warnings': {
        'task': 'estateApp.email_notifications.send_subscription_warnings',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'activate_grace_periods': {
        'task': 'estateApp.email_notifications.activate_grace_periods',
        'schedule': crontab(minute=0),  # Every hour
    },
    'expire_grace_periods': {
        'task': 'estateApp.email_notifications.expire_grace_periods',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'send_grace_period_reminders': {
        'task': 'estateApp.email_notifications.send_grace_period_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
"""
