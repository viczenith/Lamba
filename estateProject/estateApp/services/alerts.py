"""
SubscriptionAlertService - Manages subscription-related alerts and notifications
Handles trial expiry alerts, usage warnings, and subscription lifecycle events
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from estateApp.models import Company, SubscriptionAlert, CompanyUsage

logger = logging.getLogger(__name__)


class SubscriptionAlertService:
    """Service for generating and managing subscription alerts"""
    
    # Alert type mapping: days_before -> (alert_type, severity, is_dismissible)
    TRIAL_ALERT_SCHEDULE = {
        14: ('trial_ending', 'info', True),        # 14 days before (day 1 of trial)
        7: ('trial_ending', 'warning', True),      # 7 days before (day 8 of trial)
        3: ('trial_ending', 'warning', True),      # 3 days before
        1: ('trial_ending', 'critical', False),    # 1 day before (urgent)
        0: ('trial_expired', 'urgent', False),     # Expired (non-dismissible)
    }
    
    @staticmethod
    def get_required_alerts(company):
        """
        Generate all required alerts for a company based on subscription status
        
        Args:
            company: Company instance or ID
            
        Returns:
            dict with 'critical_alerts', 'warnings', 'info_alerts'
        """
        # Handle case where company is passed as string ID instead of object
        if isinstance(company, str):
            try:
                company = Company.objects.get(id=company)
            except (Company.DoesNotExist, ValueError):
                logger.error(f"Company not found: {company}")
                return {
                    'critical_alerts': [],
                    'warnings': [],
                    'info_alerts': [],
                    'usage_warnings': [],
                }
        
        # Verify company is actually a Company instance
        if not isinstance(company, Company):
            logger.error(f"Invalid company object: {type(company)}")
            return {
                'critical_alerts': [],
                'warnings': [],
                'info_alerts': [],
                'usage_warnings': [],
            }
        
        alerts = {
            'critical_alerts': [],
            'warnings': [],
            'info_alerts': [],
            'usage_warnings': [],
        }
        
        # Check trial status
        trial_alerts = SubscriptionAlertService._check_trial_status(company)
        if trial_alerts['critical']:
            alerts['critical_alerts'].extend(trial_alerts['critical'])
        if trial_alerts['warning']:
            alerts['warnings'].extend(trial_alerts['warning'])
        if trial_alerts['info']:
            alerts['info_alerts'].extend(trial_alerts['info'])
        
        # Check subscription status
        subscription_alerts = SubscriptionAlertService._check_subscription_status(company)
        if subscription_alerts['critical']:
            alerts['critical_alerts'].extend(subscription_alerts['critical'])
        if subscription_alerts['warning']:
            alerts['warnings'].extend(subscription_alerts['warning'])
        
        # Check usage limits
        usage_alerts = SubscriptionAlertService._check_usage_limits(company)
        alerts['usage_warnings'].extend(usage_alerts)
        
        # Check read-only mode
        if company.is_read_only_mode:
            alerts['critical_alerts'].append({
                'type': 'read_only_mode',
                'severity': 'critical',
                'title': 'Read-Only Mode Active',
                'message': 'Your account is in read-only mode. Please upgrade or renew your subscription.',
                'action_url': '/upgrade/',
                'action_label': 'Upgrade Now',
                'dismissible': False,
            })
        
        return alerts
    
    @staticmethod
    def _check_trial_status(company):
        """Check trial status and generate alerts"""
        alerts = {'critical': [], 'warning': [], 'info': []}
        
        # Safety check for None or invalid company
        if not company or not isinstance(company, Company):
            return alerts
        
        # Check if company has required attributes
        if not hasattr(company, 'subscription_status') or not hasattr(company, 'trial_ends_at'):
            return alerts
        
        if company.subscription_status != 'trial' or not company.trial_ends_at:
            return alerts
        
        now = timezone.now()
        days_remaining = (company.trial_ends_at - now).days
        
        # Trial expired
        if days_remaining < 0:
            alert = SubscriptionAlertService._create_alert_dict(
                'trial_expired',
                'urgent',
                'Trial Expired',
                f'Your 14-day trial has expired. Your account access is being limited. Please upgrade to continue.',
                '/upgrade/',
                'Upgrade Now',
                dismissible=False
            )
            alerts['critical'].append(alert)
        
        # Critical alert (1 day or less)
        elif days_remaining <= 1:
            alert = SubscriptionAlertService._create_alert_dict(
                'trial_ending',
                'critical',
                'Trial Expires Tomorrow',
                f'Your trial expires in {days_remaining} day(s). Upgrade now to avoid service interruption.',
                '/upgrade/',
                'Upgrade Now',
                dismissible=False
            )
            alerts['critical'].append(alert)
        
        # Warning alert (2-3 days)
        elif days_remaining <= 3:
            alert = SubscriptionAlertService._create_alert_dict(
                'trial_ending',
                'warning',
                f'Trial Expires in {days_remaining} Days',
                f'Your trial expires on {company.trial_ends_at.strftime("%B %d, %Y")}. Upgrade today to continue.',
                '/upgrade/',
                'View Plans',
                dismissible=True
            )
            alerts['warning'].append(alert)
        
        # Info alert (4-7 days)
        elif days_remaining <= 7:
            alert = SubscriptionAlertService._create_alert_dict(
                'trial_ending',
                'warning',
                f'Trial Expires in {days_remaining} Days',
                f'Your trial expires soon. Check out our plans to find the right fit for your needs.',
                '/pricing/',
                'See Plans',
                dismissible=True
            )
            alerts['warning'].append(alert)
        
        # General info (8+ days)
        else:
            alert = SubscriptionAlertService._create_alert_dict(
                'trial_info',
                'info',
                f'Trial Active - {days_remaining} Days Remaining',
                'You\'re currently on a free 14-day trial. Upgrade to a paid plan to continue after trial ends.',
                '/pricing/',
                'View Plans',
                dismissible=True
            )
            alerts['info'].append(alert)
        
        return alerts
    
    @staticmethod
    def _check_subscription_status(company):
        """Check subscription status and generate alerts"""
        alerts = {'critical': [], 'warning': []}
        
        # Safety check for None or invalid company
        if not company or not isinstance(company, Company):
            return alerts
        
        # Check if company has required attributes
        if not hasattr(company, 'subscription_status') or not hasattr(company, 'grace_period_ends_at'):
            return alerts
        
        if company.subscription_status not in ['active', 'expired']:
            return alerts
        
        now = timezone.now()
        
        # Grace period active (expired but within 3 days)
        if company.grace_period_ends_at and company.grace_period_ends_at > now:
            days_remaining = (company.grace_period_ends_at - now).days
            alert = SubscriptionAlertService._create_alert_dict(
                'grace_period',
                'critical',
                'Grace Period - Limited Access',
                f'Your subscription has expired but you have {days_remaining} days of access left. Please renew to restore full access.',
                '/billing/renew/',
                'Renew Now',
                dismissible=False
            )
            alerts['critical'].append(alert)
        
        # Subscription ending soon (within 7 days)
        elif company.subscription_ends_at and company.subscription_ends_at > now:
            days_remaining = (company.subscription_ends_at - now).days
            if days_remaining <= 7:
                alert = SubscriptionAlertService._create_alert_dict(
                    'subscription_renewing',
                    'warning',
                    f'Subscription Expires in {days_remaining} Days',
                    f'Your subscription will expire on {company.subscription_ends_at.strftime("%B %d, %Y")}. Renew now to avoid interruptions.',
                    '/billing/renew/',
                    'Renew Subscription',
                    dismissible=True
                )
                alerts['warning'].append(alert)
        
        return alerts
    
    @staticmethod
    def _check_usage_limits(company):
        """Check usage limits and generate alerts"""
        alerts = []
        
        # Safety check for None or invalid company
        if not company or not isinstance(company, Company):
            return alerts
        
        try:
            usage_metrics = CompanyUsage.objects.filter(company=company)
            
            for usage in usage_metrics:
                percentage = usage.get_usage_percentage()
                
                # Critical alert: at or exceeding limit
                if usage.is_limit_exceeded():
                    alert = SubscriptionAlertService._create_alert_dict(
                        'usage_exceeded',
                        'critical',
                        f'{usage.get_feature_display()} Limit Exceeded',
                        f'You have reached your {usage.get_feature_display()} limit. Please upgrade to increase your limit.',
                        '/upgrade/',
                        'Upgrade Now',
                        dismissible=False
                    )
                    alerts.append(alert)
                
                # Warning alert: approaching limit (80%+)
                elif percentage >= 80:
                    remaining = usage.usage_limit - usage.usage_count
                    alert = SubscriptionAlertService._create_alert_dict(
                        'usage_warning',
                        'warning',
                        f'{usage.get_feature_display()} Usage High ({int(percentage)}%)',
                        f'You have {remaining} {usage.get_feature_display()} remaining. Consider upgrading your plan.',
                        '/upgrade/',
                        'View Plans',
                        dismissible=True
                    )
                    alerts.append(alert)

            # ALSO check SubscriptionPlan.features-based limits (live counts)
            try:
                from estateApp.services.plan_limits import (
                    FEATURE_ESTATE_PROPERTIES,
                    FEATURE_ALLOCATIONS,
                    FEATURE_CLIENTS,
                    FEATURE_AFFILIATES,
                    get_limit_status,
                )

                feature_labels = {
                    FEATURE_ESTATE_PROPERTIES: 'Estate Properties',
                    FEATURE_ALLOCATIONS: 'Allocations',
                    FEATURE_CLIENTS: 'Clients',
                    FEATURE_AFFILIATES: 'Affiliates',
                }

                dashboard_url = reverse('subscription_dashboard')

                for feature in (FEATURE_ESTATE_PROPERTIES, FEATURE_ALLOCATIONS, FEATURE_CLIENTS, FEATURE_AFFILIATES):
                    res = get_limit_status(company, feature)
                    if res.limit is None:
                        continue

                    label = feature_labels.get(feature, feature)

                    if res.is_exhausted:
                        alerts.append(
                            SubscriptionAlertService._create_alert_dict(
                                'usage_exceeded',
                                'critical',
                                f'{label} Limit Reached',
                                f'You have reached your {label.lower()} limit ({res.used}/{res.limit}). Upgrade to add more.',
                                dashboard_url,
                                'Manage Subscription',
                                dismissible=False,
                            )
                        )
                    elif res.is_near_limit:
                        alerts.append(
                            SubscriptionAlertService._create_alert_dict(
                                'usage_warning',
                                'warning',
                                f'{label} Nearly Full',
                                f'You are approaching your {label.lower()} limit ({res.used}/{res.limit}). Consider upgrading soon.',
                                dashboard_url,
                                'View Plans',
                                dismissible=True,
                            )
                        )
            except Exception:
                pass
        
        except Exception as e:
            logger.error(f"Error checking usage limits for company {company.id}: {str(e)}")
        
        return alerts
    
    @staticmethod
    def _create_alert_dict(alert_type, severity, title, message, action_url=None, action_label=None, dismissible=True):
        """Helper to create alert dictionary"""
        return {
            'type': alert_type,
            'severity': severity,
            'title': title,
            'message': message,
            'action_url': action_url,
            'action_label': action_label,
            'dismissible': dismissible,
        }
    
    @staticmethod
    def create_subscription_alert(company, alert_type, title, message, severity='warning', 
                                 action_url=None, action_label=None, is_dismissible=True):
        """
        Create and save a subscription alert in database
        
        Args:
            company: Company instance
            alert_type: Type of alert (from ALERT_TYPES choices)
            title: Alert title
            message: Alert message
            severity: Alert severity level
            action_url: URL for CTA (Call To Action)
            action_label: Label for CTA button
            is_dismissible: Whether alert can be dismissed
            
        Returns:
            SubscriptionAlert instance
        """
        try:
            alert = SubscriptionAlert.objects.create(
                company=company,
                alert_type=alert_type,
                title=title,
                message=message,
                severity=severity,
                action_url=action_url,
                action_label=action_label,
                is_dismissible=is_dismissible,
                status='active',
            )
            logger.info(f"Created alert: {alert_type} for company {company.id}")
            return alert
        except Exception as e:
            logger.error(f"Error creating subscription alert: {str(e)}")
            return None
    
    @staticmethod
    def send_trial_expiry_email(company):
        """Send trial expiry notification email"""
        if not company.trial_ends_at:
            return False
        
        try:
            days_remaining = (company.trial_ends_at - timezone.now()).days
            
            subject = f"Your Trial Expires in {days_remaining} Days"
            message = f"""
            Hello {company.company_name},
            
            Your 14-day free trial expires in {days_remaining} days on {company.trial_ends_at.strftime("%B %d, %Y")}.
            
            To continue using our service after your trial ends, please upgrade to one of our paid plans:
            - Starter: $99/month
            - Professional: $299/month
            - Enterprise: Custom pricing
            
            Visit {company.custom_domain or 'https://app.realestate.com'}/upgrade to view all plans.
            
            Best regards,
            Real Estate Management Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [company.billing_email or company.email],
                fail_silently=False,
            )
            logger.info(f"Trial expiry email sent to {company.company_name}")
            return True
        except Exception as e:
            logger.error(f"Error sending trial expiry email: {str(e)}")
            return False
    
    @staticmethod
    def check_and_update_trial_status(company):
        """
        Check trial status and update company subscription status accordingly
        Called by scheduled task every 6 hours
        """
        if company.subscription_status != 'trial' or not company.trial_ends_at:
            return False
        
        now = timezone.now()
        
        # Trial has expired
        if company.trial_ends_at <= now:
            company.subscription_status = 'expired'
            company.grace_period_ends_at = now + timedelta(days=3)  # 3-day grace period
            company.save(update_fields=['subscription_status', 'grace_period_ends_at'])
            
            # Create alert
            SubscriptionAlertService.create_subscription_alert(
                company,
                'trial_expired',
                'Trial Period Ended',
                'Your 14-day trial has ended. Your account is in grace period for 3 days.',
                severity='urgent',
                is_dismissible=False
            )
            
            logger.info(f"Trial expired for company {company.id}. Grace period started.")
            return True
        
        return False
    
    @staticmethod
    def check_and_update_grace_period(company):
        """
        Check grace period and update status when it expires
        Transitions company to read-only mode
        """
        if not company.grace_period_ends_at:
            return False
        
        now = timezone.now()
        
        # Grace period has expired
        if company.grace_period_ends_at <= now and not company.is_read_only_mode:
            company.is_read_only_mode = True
            company.data_deletion_date = now + timedelta(days=30)  # Schedule deletion for 30 days
            company.save(update_fields=['is_read_only_mode', 'data_deletion_date'])
            
            # Create alert
            SubscriptionAlertService.create_subscription_alert(
                company,
                'read_only_mode',
                'Account Now Read-Only',
                'Your grace period has ended. Your account is now in read-only mode. Upgrade to restore full access.',
                severity='critical',
                action_url='/upgrade/',
                action_label='Upgrade Now',
                is_dismissible=False
            )
            
            logger.info(f"Read-only mode activated for company {company.id}")
            return True
        
        return False
    
    @staticmethod
    def check_and_delete_expired_data(company):
        """
        Check if data deletion date has been reached and schedule/execute deletion
        Only deletes data, keeps company record for potential recovery
        """
        if not company.data_deletion_date:
            return False
        
        now = timezone.now()
        
        # Deletion date reached
        if company.data_deletion_date <= now and company.subscription_status == 'expired':
            try:
                from estateApp.models import EstatePlot, Client, MarketerAffiliation, Transaction
                
                # Delete company data
                EstatePlot.objects.filter(estate__company=company).delete()
                Client.objects.filter(company=company).delete()
                MarketerAffiliation.objects.filter(company=company).delete()
                Transaction.objects.filter(company=company).delete()
                
                # Create final alert
                SubscriptionAlertService.create_subscription_alert(
                    company,
                    'data_deletion',
                    'Data Permanently Deleted',
                    'Your account data has been permanently deleted due to non-renewal after grace period.',
                    severity='critical',
                    is_dismissible=False
                )
                
                logger.warning(f"Company {company.id} data permanently deleted due to expired subscription.")
                return True
            except Exception as e:
                logger.error(f"Error deleting company {company.id} data: {str(e)}")
                return False
        
        return False


# Import settings for email configuration
from django.conf import settings
