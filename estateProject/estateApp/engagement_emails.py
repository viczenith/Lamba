"""
User Engagement Email System
Handles re-engagement and onboarding emails for multi-tenant companies
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EngagementEmailConfig:
    """Configuration for engagement emails per company"""
    
    TEMPLATES = {
        'reengagement': {
            'subject': 'We miss you! Get back to {company_name}',
            'template': 'emails/reengagement_reminder.html',
            'plain_template': 'emails/reengagement_reminder.txt',
            'from_name': 'Engagement Team',
        },
        'onboarding': {
            'subject': 'Welcome to {company_name}! Let\'s get started',
            'template': 'emails/onboarding_reminder.html',
            'plain_template': 'emails/onboarding_reminder.txt',
            'from_name': 'Onboarding Team',
        }
    }


def send_reengagement_email(user, company):
    """
    Send re-engagement email to users who haven't logged in for 30+ days
    
    Args:
        user: CustomUser object
        company: Company object
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        config = EngagementEmailConfig.TEMPLATES['reengagement']
        
        context = {
            'user': user,
            'company': company,
            'company_name': company.company_name,
            'user_name': user.full_name or user.email,
            'login_url': f"{settings.SITE_URL}/login/",
            'dashboard_url': f"{settings.SITE_URL}/{company.slug}/dashboard/",
            'support_email': settings.DEFAULT_FROM_EMAIL,
        }
        
        # Render HTML and plain text versions
        html_content = render_to_string(config['template'], context)
        text_content = render_to_string(config['plain_template'], context)
        
        # Create email
        subject = config['subject'].format(company_name=company.company_name)
        from_email = f"{config['from_name']} <{settings.DEFAULT_FROM_EMAIL}>"
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[user.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send
        email.send()
        logger.info(f"Re-engagement email sent to {user.email} for {company.company_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send re-engagement email to {user.email}: {str(e)}")
        return False


def send_onboarding_email(user, company):
    """
    Send onboarding reminder email to users who have never logged in
    
    Args:
        user: CustomUser object
        company: Company object
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        config = EngagementEmailConfig.TEMPLATES['onboarding']
        
        context = {
            'user': user,
            'company': company,
            'company_name': company.company_name,
            'user_name': user.full_name or user.email,
            'user_role': user.get_role_display() if hasattr(user, 'get_role_display') else user.role,
            'login_url': f"{settings.SITE_URL}/login/",
            'dashboard_url': f"{settings.SITE_URL}/{company.slug}/dashboard/",
            'support_email': settings.DEFAULT_FROM_EMAIL,
            'help_center': f"{settings.SITE_URL}/help/",
        }
        
        # Render HTML and plain text versions
        html_content = render_to_string(config['template'], context)
        text_content = render_to_string(config['plain_template'], context)
        
        # Create email
        subject = config['subject'].format(company_name=company.company_name)
        from_email = f"{config['from_name']} <{settings.DEFAULT_FROM_EMAIL}>"
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[user.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send
        email.send()
        logger.info(f"Onboarding email sent to {user.email} for {company.company_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send onboarding email to {user.email}: {str(e)}")
        return False


def send_bulk_reengagement_emails(users, company):
    """
    Send re-engagement emails to multiple users
    
    Args:
        users: QuerySet or list of CustomUser objects
        company: Company object
        
    Returns:
        dict: Statistics about sent emails
    """
    stats = {
        'total': len(users) if isinstance(users, list) else users.count(),
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    for user in users:
        if send_reengagement_email(user, company):
            stats['sent'] += 1
        else:
            stats['failed'] += 1
            stats['errors'].append(f"Failed to send to {user.email}")
    
    logger.info(f"Re-engagement email batch completed for {company.company_name}: "
                f"{stats['sent']} sent, {stats['failed']} failed")
    return stats


def send_bulk_onboarding_emails(users, company):
    """
    Send onboarding emails to multiple users
    
    Args:
        users: QuerySet or list of CustomUser objects
        company: Company object
        
    Returns:
        dict: Statistics about sent emails
    """
    stats = {
        'total': len(users) if isinstance(users, list) else users.count(),
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    for user in users:
        if send_onboarding_email(user, company):
            stats['sent'] += 1
        else:
            stats['failed'] += 1
            stats['errors'].append(f"Failed to send to {user.email}")
    
    logger.info(f"Onboarding email batch completed for {company.company_name}: "
                f"{stats['sent']} sent, {stats['failed']} failed")
    return stats


def get_email_engagement_summary(company):
    """
    Get engagement email summary for a company
    
    Args:
        company: Company object
        
    Returns:
        dict: Summary statistics
    """
    from django.utils import timezone
    from datetime import timedelta
    from estateApp.models import CustomUser, MarketerAffiliation, ClientMarketerAssignment
    from itertools import chain
    
    now = timezone.now()
    last_30_days_cutoff = now - timedelta(days=30)
    
    # Get all users (same logic as company_profile_view)
    company_users = CustomUser.objects.filter(company_profile=company)
    
    affiliated_marketer_ids = set(
        MarketerAffiliation.objects.filter(
            company=company
        ).values_list('marketer_id', flat=True)
    )
    affiliated_client_ids = set(
        ClientMarketerAssignment.objects.filter(
            company=company
        ).values_list('client_id', flat=True)
    )
    
    included_ids = set(company_users.values_list('id', flat=True))
    additional_user_ids = (affiliated_marketer_ids | affiliated_client_ids) - included_ids
    additional_users = CustomUser.objects.filter(id__in=additional_user_ids) if additional_user_ids else CustomUser.objects.none()
    
    all_users = list(chain(company_users, additional_users))
    
    # Categorize users
    reengagement_users = [u for u in all_users if u.last_login and u.last_login < last_30_days_cutoff and u.is_active]
    onboarding_users = [u for u in all_users if not u.last_login and u.is_active]
    
    return {
        'company': company,
        'total_users': len(all_users),
        'reengagement_count': len(reengagement_users),
        'onboarding_count': len(onboarding_users),
        'reengagement_users': reengagement_users,
        'onboarding_users': onboarding_users,
        'can_send_emails': len(reengagement_users) > 0 or len(onboarding_users) > 0,
    }
