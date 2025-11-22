"""
Audit logging for tracking all significant actions.
Records administrative actions, data changes, and security events.
"""
import logging
import json
from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

logger = logging.getLogger(__name__)

# Import AuditLog from models to avoid duplicate
from .models import AuditLog


class AuditLogger:
    """
    Main audit logging service.
    """
    
    @staticmethod
    def log_action(action, user, company, content_type=None, object_id=None,
                   object_repr=None, old_values=None, new_values=None,
                   status='SUCCESS', error_message=None, request=None, metadata=None):
        """
        Log an action to the audit log.
        """
        try:
            ip_address = None
            user_agent = None
            request_path = None
            request_method = None
            
            if request:
                ip_address = AuditLogger.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                request_path = request.path
                request_method = request.method
            
            # Create audit log entry
            audit_log = AuditLog.objects.create(
                user=user,
                company=company,
                action=action,
                content_type=content_type,
                object_id=object_id,
                object_repr=object_repr or '',
                old_values=old_values or {},
                new_values=new_values or {},
                status=status,
                error_message=error_message or '',
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request_path,
                request_method=request_method,
                metadata=metadata or {},
            )
            
            logger.info(
                f"Audit log created: {action} by {user} on {company}",
                extra={'audit_log_id': audit_log.id}
            )
            
            return audit_log
        
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def log_create(user, company, instance, request=None, extra_fields=None):
        """Log object creation"""
        
        content_type = ContentType.objects.get_for_model(instance)
        
        new_values = {}
        if extra_fields:
            for field in extra_fields:
                if hasattr(instance, field):
                    new_values[field] = str(getattr(instance, field))
        
        return AuditLogger.log_action(
            action='CREATE',
            user=user,
            company=company,
            content_type=content_type,
            object_id=instance.id,
            object_repr=str(instance),
            new_values=new_values,
            request=request,
        )
    
    @staticmethod
    def log_update(user, company, instance, old_values, new_values, request=None):
        """Log object update"""
        
        content_type = ContentType.objects.get_for_model(instance)
        
        return AuditLogger.log_action(
            action='UPDATE',
            user=user,
            company=company,
            content_type=content_type,
            object_id=instance.id,
            object_repr=str(instance),
            old_values=old_values,
            new_values=new_values,
            request=request,
        )
    
    @staticmethod
    def log_delete(user, company, instance, request=None):
        """Log object deletion"""
        
        content_type = ContentType.objects.get_for_model(instance)
        
        return AuditLogger.log_action(
            action='DELETE',
            user=user,
            company=company,
            content_type=content_type,
            object_id=instance.id,
            object_repr=str(instance),
            request=request,
        )
    
    @staticmethod
    def log_login(user, company=None, request=None):
        """Log user login"""
        return AuditLogger.log_action(
            action='LOGIN',
            user=user,
            company=company,
            request=request,
        )
    
    @staticmethod
    def log_logout(user, company=None, request=None):
        """Log user logout"""
        # Handle company properly - it could be a string or Company instance
        if company and isinstance(company, str):
            from estateApp.models import Company
            try:
                company = Company.objects.get(company_name=company)
            except Company.DoesNotExist:
                company = None
        elif not company and hasattr(user, 'company_profile'):
            company = user.company_profile
        
        return AuditLogger.log_action(
            action='LOGOUT',
            user=user,
            company=company,
            request=request,
        )
    
    @staticmethod
    def log_permission_change(user, company, target_user, old_perms, new_perms, request=None):
        """Log permission changes"""
        
        return AuditLogger.log_action(
            action='PERMISSION_CHANGE',
            user=user,
            company=company,
            object_repr=f"User: {target_user}",
            old_values={'permissions': old_perms},
            new_values={'permissions': new_perms},
            request=request,
        )
    
    @staticmethod
    def log_subscription_change(user, company, old_tier, new_tier, request=None):
        """Log subscription changes"""
        
        return AuditLogger.log_action(
            action='SUBSCRIPTION_CHANGE',
            user=user,
            company=company,
            old_values={'tier': old_tier},
            new_values={'tier': new_tier},
            request=request,
        )
    
    @staticmethod
    def log_api_key_action(user, company, api_key, action, request=None):
        """Log API key creation or revocation"""
        
        return AuditLogger.log_action(
            action=action,
            user=user,
            company=company,
            object_repr=f"API Key: {api_key.name}",
            metadata={
                'api_key_id': api_key.id,
                'api_key_prefix': api_key.key[:8],  # Log only prefix
            },
            request=request,
        )
    
    @staticmethod
    def log_export(user, company, export_type, record_count, request=None):
        """Log data export"""
        
        return AuditLogger.log_action(
            action='EXPORT',
            user=user,
            company=company,
            object_repr=f"{export_type} export",
            metadata={'record_count': record_count, 'export_type': export_type},
            request=request,
        )
    
    @staticmethod
    def log_bulk_operation(user, company, operation_type, records_affected, request=None):
        """Log bulk operations"""
        
        return AuditLogger.log_action(
            action='BULK_OPERATION',
            user=user,
            company=company,
            object_repr=f"Bulk {operation_type}",
            metadata={
                'operation_type': operation_type,
                'records_affected': records_affected,
            },
            request=request,
        )
    
    @staticmethod
    def log_payment(user, company, amount, status, transaction_id=None, request=None):
        """Log payment transactions"""
        
        return AuditLogger.log_action(
            action='PAYMENT',
            user=user,
            company=company,
            status=status,
            object_repr=f"Payment: ${amount}",
            metadata={
                'amount': amount,
                'transaction_id': transaction_id,
            },
            request=request,
        )
    
    @staticmethod
    def log_security_event(user, company, event_type, description, severity='LOW', request=None):
        """Log security events"""
        
        return AuditLogger.log_action(
            action='SECURITY_EVENT',
            user=user,
            company=company,
            object_repr=event_type,
            metadata={
                'event_type': event_type,
                'description': description,
                'severity': severity,
            },
            request=request,
        )


class AuditLogQuery:
    """
    Query and analyze audit logs.
    """
    
    @staticmethod
    def get_user_actions(user, company=None, days=7):
        """Get recent actions by a user"""
        
        since = timezone.now() - timedelta(days=days)
        
        query = AuditLog.objects.filter(
            user=user,
            created_at__gte=since
        )
        
        if company:
            query = query.filter(company=company)
        
        return query.order_by('-created_at')
    
    @staticmethod
    def get_company_activity(company, days=7, action=None):
        """Get all activity in a company"""
        
        since = timezone.now() - timedelta(days=days)
        
        query = AuditLog.objects.filter(
            company=company,
            created_at__gte=since
        )
        
        if action:
            query = query.filter(action=action)
        
        return query.order_by('-created_at')
    
    @staticmethod
    def get_failed_actions(company=None, days=7):
        """Get all failed actions"""
        
        since = timezone.now() - timedelta(days=days)
        
        query = AuditLog.objects.filter(
            status='FAILED',
            created_at__gte=since
        )
        
        if company:
            query = query.filter(company=company)
        
        return query.order_by('-created_at')
    
    @staticmethod
    def get_object_history(obj):
        """Get all audit logs for a specific object"""
        
        content_type = ContentType.objects.get_for_model(obj)
        
        return AuditLog.objects.filter(
            content_type=content_type,
            object_id=obj.id
        ).order_by('-created_at')
    
    @staticmethod
    def get_security_events(company, severity='HIGH', days=30):
        """Get security events"""
        
        since = timezone.now() - timedelta(days=days)
        
        return AuditLog.objects.filter(
            company=company,
            action='SECURITY_EVENT',
            created_at__gte=since
        ).order_by('-created_at')
    
    @staticmethod
    def get_statistics(company, days=7):
        """Get audit log statistics"""
        
        since = timezone.now() - timedelta(days=days)
        
        logs = AuditLog.objects.filter(
            company=company,
            created_at__gte=since
        )
        
        return {
            'total_actions': logs.count(),
            'by_action': dict(logs.values_list('action').annotate(
                models.Count('id')
            )),
            'by_user': dict(logs.values_list('user__username').annotate(
                models.Count('id')
            )),
            'successful': logs.filter(status='SUCCESS').count(),
            'failed': logs.filter(status='FAILED').count(),
        }


def log_audit_action(action, **kwargs):
    """
    Convenience function to log an audit action.
    Usage: log_audit_action('CREATE', user=user, company=company, instance=obj)
    """
    return AuditLogger.log_action(action, **kwargs)
