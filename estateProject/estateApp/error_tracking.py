"""
Error tracking and monitoring using Sentry.
Integrates Sentry for exception tracking, performance monitoring, and error alerts.
"""
import logging
import traceback
from functools import wraps
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SentryErrorTracker:
    """
    Wrapper around Sentry for centralized error tracking.
    """
    
    @staticmethod
    def init_sentry():
        """Initialize Sentry integration"""
        try:
            import sentry_sdk
            from sentry_sdk.integrations.django import DjangoIntegration
            from sentry_sdk.integrations.celery import CeleryIntegration
            from sentry_sdk.integrations.redis import RedisIntegration
            
            sentry_sdk.init(
                dsn=getattr(settings, 'SENTRY_DSN', None),
                integrations=[
                    DjangoIntegration(),
                    CeleryIntegration(),
                    RedisIntegration(),
                ],
                traces_sample_rate=getattr(settings, 'SENTRY_TRACES_SAMPLE_RATE', 0.1),
                profiles_sample_rate=getattr(settings, 'SENTRY_PROFILES_SAMPLE_RATE', 0.1),
                environment=getattr(settings, 'ENVIRONMENT', 'production'),
                send_default_pii=getattr(settings, 'SENTRY_SEND_PII', False),
            )
            
            logger.info("Sentry initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    @staticmethod
    def capture_exception(exception, context=None, tags=None):
        """Capture exception in Sentry"""
        try:
            import sentry_sdk
            
            with sentry_sdk.push_scope() as scope:
                # Add context
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                
                # Add tags
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                
                sentry_sdk.capture_exception(exception)
                
                logger.error(f"Exception captured in Sentry: {exception}")
        
        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")
    
    @staticmethod
    def capture_message(message, level='info', context=None, tags=None):
        """Capture message in Sentry"""
        try:
            import sentry_sdk
            
            with sentry_sdk.push_scope() as scope:
                # Add context
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                
                # Add tags
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                
                sentry_sdk.capture_message(message, level=level)
                
                logger.info(f"Message captured in Sentry: {message}")
        
        except Exception as e:
            logger.error(f"Failed to capture message in Sentry: {e}")
    
    @staticmethod
    def set_user_context(user):
        """Set user context for error tracking"""
        try:
            import sentry_sdk
            
            if user and user.is_authenticated:
                sentry_sdk.set_user({
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                })
            else:
                sentry_sdk.set_user(None)
        
        except Exception as e:
            logger.error(f"Failed to set user context: {e}")
    
    @staticmethod
    def set_request_context(request):
        """Set request context for error tracking"""
        try:
            import sentry_sdk
            
            with sentry_sdk.push_scope() as scope:
                scope.set_context("request", {
                    'method': request.method,
                    'path': request.path,
                    'query_string': request.META.get('QUERY_STRING', ''),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                })
                
                # Set company context
                company = getattr(request, 'company', None)
                if company:
                    scope.set_context("company", {
                        'id': company.id,
                        'name': company.company_name if hasattr(company, 'company_name') else str(company),
                    })
        
        except Exception as e:
            logger.error(f"Failed to set request context: {e}")


class ErrorHandler:
    """
    Centralized error handling with logging, Sentry, and notifications.
    """
    
    @staticmethod
    def handle_api_error(exception, request=None, view=None):
        """Handle API error with context"""
        
        # Capture in Sentry
        context = {}
        tags = {'error_type': 'api_error'}
        
        if request:
            context['request'] = {
                'method': request.method,
                'path': request.path,
                'user': str(request.user),
            }
            tags['user_id'] = str(request.user.id) if request.user.is_authenticated else 'anonymous'
            
            company = getattr(request, 'company', None)
            if company:
                tags['company_id'] = str(company.id)
        
        if view:
            context['view'] = {
                'name': view.__class__.__name__,
                'action': getattr(view, 'action', 'unknown'),
            }
        
        SentryErrorTracker.capture_exception(exception, context=context, tags=tags)
        
        # Log error
        logger.error(
            f"API Error: {exception}",
            extra={
                'exception': str(exception),
                'traceback': traceback.format_exc(),
            },
            exc_info=True
        )
    
    @staticmethod
    def handle_celery_error(task_name, exception, args=None, kwargs=None):
        """Handle Celery task error"""
        
        context = {
            'task': {
                'name': task_name,
                'args': str(args),
                'kwargs': str(kwargs),
            }
        }
        
        tags = {
            'error_type': 'celery_error',
            'task_name': task_name,
        }
        
        SentryErrorTracker.capture_exception(exception, context=context, tags=tags)
        
        logger.error(
            f"Celery Task Error [{task_name}]: {exception}",
            extra={
                'task': task_name,
                'args': args,
                'kwargs': kwargs,
            },
            exc_info=True
        )
    
    @staticmethod
    def handle_database_error(exception, query=None):
        """Handle database error"""
        
        context = {}
        if query:
            context['query'] = str(query)[:500]  # Truncate long queries
        
        tags = {'error_type': 'database_error'}
        
        SentryErrorTracker.capture_exception(exception, context=context, tags=tags)
        
        logger.error(
            f"Database Error: {exception}",
            extra={'query': str(query)[:500]},
            exc_info=True
        )
    
    @staticmethod
    def handle_external_api_error(api_name, exception, endpoint=None):
        """Handle external API error"""
        
        context = {'api': {'name': api_name}}
        if endpoint:
            context['api']['endpoint'] = endpoint
        
        tags = {
            'error_type': 'external_api_error',
            'api_name': api_name,
        }
        
        SentryErrorTracker.capture_exception(exception, context=context, tags=tags)
        
        logger.error(
            f"External API Error [{api_name}]: {exception}",
            extra={'api': api_name, 'endpoint': endpoint},
            exc_info=True
        )


def track_errors(func=None, error_type='general'):
    """
    Decorator to automatically track errors in function execution.
    Usage: @track_errors or @track_errors(error_type='celery')
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                # Extract context from arguments
                context = {
                    'function': f.__name__,
                    'module': f.__module__,
                }
                
                tags = {'error_type': error_type}
                
                # Try to extract request/company context
                for arg in args:
                    if hasattr(arg, 'user'):  # Django request
                        context['user'] = str(arg.user)
                        company = getattr(arg, 'company', None)
                        if company:
                            tags['company_id'] = str(company.id)
                        break
                
                SentryErrorTracker.capture_exception(e, context=context, tags=tags)
                raise
        
        return wrapper
    
    # Handle both @track_errors and @track_errors(...) syntax
    if func is not None:
        return decorator(func)
    else:
        return decorator


class ErrorNotificationService:
    """
    Send notifications when critical errors occur.
    """
    
    @staticmethod
    def notify_critical_error(exception, user=None, company=None):
        """Send notification for critical errors"""
        
        try:
            from estateApp.notifications.email_service import EmailService
            
            # Determine recipients
            recipients = []
            
            if company and hasattr(company, 'created_by'):
                recipients.append(company.created_by.email)
            
            if user and hasattr(user, 'email'):
                recipients.append(user.email)
            
            # Add admin emails
            admin_emails = getattr(settings, 'ADMIN_EMAILS', [])
            recipients.extend(admin_emails)
            
            if recipients:
                EmailService.send_critical_error_notification(
                    recipients=list(set(recipients)),
                    error_message=str(exception),
                    error_type=exception.__class__.__name__,
                    timestamp=timezone.now(),
                )
        
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    @staticmethod
    def notify_quota_exceeded(company, resource_type, current_usage, limit):
        """Send notification when resource quota exceeded"""
        
        try:
            from estateApp.notifications.email_service import EmailService
            
            EmailService.send_quota_exceeded_notification(
                company=company,
                resource_type=resource_type,
                current_usage=current_usage,
                limit=limit,
            )
        
        except Exception as e:
            logger.error(f"Failed to send quota notification: {e}")


class PerformanceMonitor:
    """
    Monitor performance and track slow operations.
    """
    
    SLOW_THRESHOLD = {
        'database': 0.5,  # 500ms
        'api_call': 1.0,  # 1 second
        'task': 5.0,  # 5 seconds
    }
    
    @staticmethod
    def track_operation(operation_type='general', threshold=None):
        """Decorator to track operation performance"""
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                
                finally:
                    duration = time.time() - start_time
                    
                    # Check if slow
                    slow_threshold = threshold or PerformanceMonitor.SLOW_THRESHOLD.get(
                        operation_type, 1.0
                    )
                    
                    if duration > slow_threshold:
                        logger.warning(
                            f"Slow {operation_type} operation: {func.__name__} took {duration:.2f}s"
                        )
                        
                        # Capture in Sentry
                        SentryErrorTracker.capture_message(
                            f"Slow operation detected: {func.__name__}",
                            level='warning',
                            context={
                                'operation': func.__name__,
                                'duration': duration,
                                'threshold': slow_threshold,
                            },
                            tags={
                                'operation_type': operation_type,
                                'slow_operation': 'true',
                            }
                        )
            
            return wrapper
        
        return decorator


# ============================================================================
# Phase 4: Custom REST Framework Exception Handler
# ============================================================================

def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler with Sentry integration and detailed error response.
    Provides consistent error formatting and automatic error tracking.
    """
    from rest_framework.views import exception_handler
    from rest_framework import status
    from rest_framework.response import Response
    
    # Call DRF's default exception handler
    response = exception_handler(exc, context)
    
    # Extract context information
    request = context.get('request')
    view = context.get('view')
    
    error_id = None
    status_code = response.status_code if response else 500
    
    try:
        # Track error in Sentry
        import sentry_sdk
        
        error_id = sentry_sdk.last_event_id()
        
        SentryErrorTracker.capture_exception(
            exception=exc,
            context={
                'request': {
                    'method': request.method if request else None,
                    'path': request.path if request else None,
                    'user': str(request.user) if request else None,
                    'ip': get_client_ip(request) if request else None,
                    'company': str(getattr(request, 'company', None)) if request else None,
                },
                'view': str(view) if view else None,
            },
            tags={
                'error_type': type(exc).__name__,
                'status_code': str(status_code),
            }
        )
        
        # Notify on critical errors
        if status_code >= 500:
            ErrorNotificationService.send_critical_error_notification(
                error=exc,
                error_id=error_id,
                request=request,
            )
    
    except Exception as e:
        logger.error(f"Error in exception handler: {e}")
    
    # Format response
    if response is None:
        # Internal server error
        response = Response(
            {
                'error': 'Internal server error',
                'error_id': error_id,
                'detail': str(exc) if settings.DEBUG else 'An unexpected error occurred',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        # Format the error response
        response.data = {
            'success': False,
            'error': response.data,
            'error_id': error_id,
            'timestamp': timezone.now().isoformat(),
        }
    
    return response


def get_client_ip(request):
    """Get client IP address from request"""
    if not request:
        return None
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    
    return request.META.get('REMOTE_ADDR', None)


# Initialize Sentry on module load
SentryErrorTracker.init_sentry()
