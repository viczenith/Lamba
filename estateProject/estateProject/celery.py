"""
Celery Configuration for Background Tasks
==========================================
Handles asynchronous task processing for:
- Email sending
- PDF generation
- Bulk imports
- Notifications
- Heavy computations
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')

# Create Celery app
app = Celery('estateProject')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# ==============================================================================
# CELERY BEAT SCHEDULE (Periodic Tasks)
# ==============================================================================
app.conf.beat_schedule = {
    # Check subscription expirations daily at midnight
    'check-subscription-expirations': {
        'task': 'estateApp.tasks.check_subscription_expirations',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # Send reminder emails for expiring trials (3 days before)
    'send-trial-expiry-reminders': {
        'task': 'estateApp.tasks.send_trial_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
    },
    
    # Clean up old sessions weekly
    'cleanup-expired-sessions': {
        'task': 'estateApp.tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
    },
    
    # Generate daily reports
    'generate-daily-reports': {
        'task': 'estateApp.tasks.generate_daily_reports',
        'schedule': crontab(hour=6, minute=0),  # 6 AM daily
    },
    
    # Cleanup old audit logs (keep 90 days)
    'cleanup-audit-logs': {
        'task': 'estateApp.tasks.cleanup_old_audit_logs',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2 AM
    },
    
    # Send birthday greetings
    'send-birthday-greetings': {
        'task': 'estateApp.tasks.send_birthday_greetings',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
    },
    
    # Cache warmup (pre-populate cache)
    'cache-warmup': {
        'task': 'estateApp.tasks.warmup_cache',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

# ==============================================================================
# TASK ROUTES (Priority Queues)
# ==============================================================================
app.conf.task_routes = {
    # High priority - user-facing, needs immediate processing
    'estateApp.tasks.send_notification_email': {'queue': 'high_priority'},
    'estateApp.tasks.send_sms_notification': {'queue': 'high_priority'},
    'estateApp.tasks.process_payment_webhook': {'queue': 'high_priority'},
    
    # Default priority - normal background tasks
    'estateApp.tasks.generate_receipt_pdf': {'queue': 'default'},
    'estateApp.tasks.update_search_index': {'queue': 'default'},
    
    # Low priority - can wait
    'estateApp.tasks.generate_report_pdf': {'queue': 'low_priority'},
    'estateApp.tasks.send_marketing_email': {'queue': 'low_priority'},
    
    # Bulk queue - long running tasks
    'estateApp.tasks.process_bulk_import': {'queue': 'bulk'},
    'estateApp.tasks.generate_monthly_statements': {'queue': 'bulk'},
    'estateApp.tasks.cleanup_*': {'queue': 'bulk'},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
