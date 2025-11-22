"""
Email notification service for SaaS platform.
Handles all email delivery through Celery tasks.
"""
import os
import logging
from typing import Dict, List, Optional
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send emails with HTML templates"""
    
    DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL or 'noreply@realestatesaas.com'
    
    @staticmethod
    def send_email(
        subject: str,
        template_name: str,
        context: Dict,
        recipient_list: List[str],
        reply_to: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Send email with HTML template.
        
        Args:
            subject: Email subject line
            template_name: Path to email template (e.g., 'emails/affiliation_approval.html')
            context: Template context dictionary
            recipient_list: List of recipient email addresses
            reply_to: Optional reply-to addresses
            bcc: Optional BCC addresses
            tags: Optional email tags for analytics
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Add company info to context if available
            if 'company' not in context and hasattr(context.get('user'), 'company_profile'):
                context['company'] = context['user'].company_profile
            
            # Render HTML template
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            
            # Create email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=EmailService.DEFAULT_FROM_EMAIL,
                to=recipient_list,
                reply_to=reply_to,
                bcc=bcc,
            )
            
            # Attach HTML version
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send(fail_silently=False)
            
            logger.info(
                f"Email sent: subject='{subject}' to={recipient_list} template={template_name}"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to send email: subject='{subject}' to={recipient_list} error={str(e)}",
                exc_info=True
            )
            return False
    
    @staticmethod
    def send_affiliation_approval_email(affiliation) -> bool:
        """Send approval notification to marketer"""
        return EmailService.send_email(
            subject=f"✅ Your affiliation with {affiliation.company.company_name} has been approved!",
            template_name='emails/affiliation_approval.html',
            context={
                'marketer': affiliation.marketer,
                'company': affiliation.company,
                'affiliation': affiliation,
                'commission_rate': affiliation.commission_rate,
            },
            recipient_list=[affiliation.marketer.email],
        )
    
    @staticmethod
    def send_affiliation_rejection_email(affiliation, reason: str = "") -> bool:
        """Send rejection notification to marketer"""
        return EmailService.send_email(
            subject=f"❌ Your affiliation request with {affiliation.company.company_name}",
            template_name='emails/affiliation_rejection.html',
            context={
                'marketer': affiliation.marketer,
                'company': affiliation.company,
                'reason': reason,
            },
            recipient_list=[affiliation.marketer.email],
        )
    
    @staticmethod
    def send_commission_approved_email(commission) -> bool:
        """Send commission approval notification to marketer"""
        return EmailService.send_email(
            subject=f"💰 Commission of ₦{commission.commission_amount:,.0f} has been approved",
            template_name='emails/commission_approved.html',
            context={
                'marketer': commission.affiliation.marketer,
                'company': commission.affiliation.company,
                'commission': commission,
                'amount': commission.commission_amount,
            },
            recipient_list=[commission.affiliation.marketer.email],
        )
    
    @staticmethod
    def send_commission_payment_email(commission, payment_reference: str) -> bool:
        """Send payment confirmation to marketer"""
        return EmailService.send_email(
            subject=f"✅ Payment of ₦{commission.commission_amount:,.0f} processed",
            template_name='emails/commission_payment.html',
            context={
                'marketer': commission.affiliation.marketer,
                'company': commission.affiliation.company,
                'commission': commission,
                'amount': commission.commission_amount,
                'payment_reference': payment_reference,
                'bank_name': getattr(commission.affiliation, 'bank_name', 'Your Bank'),
            },
            recipient_list=[commission.affiliation.marketer.email],
        )
    
    @staticmethod
    def send_invoice_email(invoice) -> bool:
        """Send invoice to company admin"""
        return EmailService.send_email(
            subject=f"Invoice {invoice.invoice_number} - {invoice.period_start.strftime('%B %Y')}",
            template_name='emails/invoice_generated.html',
            context={
                'company': invoice.company,
                'invoice': invoice,
                'amount': invoice.amount,
                'tax': invoice.tax_amount,
                'total': invoice.amount + invoice.tax_amount,
                'due_date': invoice.due_date,
            },
            recipient_list=[invoice.company.billing_email or invoice.company.email],
        )
    
    @staticmethod
    def send_subscription_renewal_email(company, days_until_renewal: int = 0) -> bool:
        """Send subscription renewal reminder"""
        template = 'emails/subscription_renewal.html' if days_until_renewal > 0 else 'emails/subscription_renewed.html'
        
        return EmailService.send_email(
            subject=f"Your subscription renews in {days_until_renewal} days" if days_until_renewal > 0 else "✅ Subscription renewed",
            template_name=template,
            context={
                'company': company,
                'tier': company.subscription_tier,
                'days_until_renewal': days_until_renewal,
                'renewal_date': company.subscription_ends_at,
            },
            recipient_list=[company.billing_email or company.email],
        )
    
    @staticmethod
    def send_trial_expiration_warning_email(company, days_remaining: int) -> bool:
        """Send trial expiration warning"""
        return EmailService.send_email(
            subject=f"⏰ Your free trial expires in {days_remaining} days",
            template_name='emails/trial_expiration_warning.html',
            context={
                'company': company,
                'days_remaining': days_remaining,
                'trial_end_date': company.trial_ends_at,
                'upgrade_url': f"{settings.FRONTEND_URL}/billing/upgrade/" if hasattr(settings, 'FRONTEND_URL') else '',
            },
            recipient_list=[company.billing_email or company.email],
        )
    
    @staticmethod
    def send_payment_failed_email(company, error_message: str = "") -> bool:
        """Send payment failure notification"""
        return EmailService.send_email(
            subject="❌ Payment failed - Action required",
            template_name='emails/payment_failed.html',
            context={
                'company': company,
                'error_message': error_message,
                'retry_url': f"{settings.FRONTEND_URL}/billing/retry/" if hasattr(settings, 'FRONTEND_URL') else '',
            },
            recipient_list=[company.billing_email or company.email],
        )
    
    @staticmethod
    def send_api_limit_exceeded_email(company, current_usage: int, limit: int) -> bool:
        """Send API limit exceeded notification"""
        return EmailService.send_email(
            subject="⚠️ API rate limit exceeded",
            template_name='emails/api_limit_exceeded.html',
            context={
                'company': company,
                'current_usage': current_usage,
                'limit': limit,
                'upgrade_url': f"{settings.FRONTEND_URL}/billing/upgrade/" if hasattr(settings, 'FRONTEND_URL') else '',
            },
            recipient_list=[company.billing_email or company.email],
        )
    
    @staticmethod
    def send_weekly_summary_email(company, metrics: Dict) -> bool:
        """Send weekly metrics summary to company admin"""
        return EmailService.send_email(
            subject=f"📊 Weekly Summary - {company.company_name}",
            template_name='emails/weekly_summary.html',
            context={
                'company': company,
                'metrics': metrics,
                'new_properties': metrics.get('new_properties', 0),
                'new_clients': metrics.get('new_clients', 0),
                'commissions_paid': metrics.get('commissions_paid', 0),
                'api_calls': metrics.get('api_calls', 0),
            },
            recipient_list=[company.billing_email or company.email],
        )


# Convenience alias
send_email = EmailService.send_email
