"""
DEPLOYMENT GUIDE - PHASE 5 SUBSCRIPTION MANAGEMENT
Quick start guide for getting the system live
"""

DEPLOYMENT_STEPS = """

╔════════════════════════════════════════════════════════════════════════════════╗
║                      PHASE 5 DEPLOYMENT CHECKLIST                             ║
║                     Subscription Management System                            ║
╚════════════════════════════════════════════════════════════════════════════════╝


STEP 1: PRE-DEPLOYMENT VERIFICATION (15 minutes)
════════════════════════════════════════════════════════════════════════════════════

1. Run system check:
   $ cd /path/to/estateProject
   $ python manage.py check
   Expected: System check identified no issues (0 silenced).

2. Run test suite:
   $ python manage.py test estateApp.tests.test_subscription_lifecycle
   Expected: 29/29 tests PASSING

3. Verify migrations exist:
   $ python manage.py showmigrations estateApp | grep 0056
   Expected: 0056_companyusage_healthcheck_subscriptionalert_and_more

4. Check file structure:
   ✓ estateApp/services/alerts.py exists
   ✓ estateApp/middleware/subscription_middleware.py exists
   ✓ estateApp/management/commands/check_subscriptions.py exists
   ✓ estateApp/tests/test_subscription_lifecycle.py exists


STEP 2: DATABASE MIGRATION (5 minutes)
════════════════════════════════════════════════════════════════════════════════════

1. Backup current database:
   $ cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)
   OR if PostgreSQL:
   $ pg_dump multi_tenant_db > multi_tenant_db.backup.$(date +%Y%m%d_%H%M%S).sql

2. Run migrations:
   $ python manage.py migrate estateApp
   Expected: "Applying estateApp.0056... OK"

3. Verify tables created:
   $ python manage.py dbshell
   > SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%subscription%';
   Expected: Should show new tables

4. Exit database shell:
   > .quit


STEP 3: CONFIGURATION (10 minutes)
════════════════════════════════════════════════════════════════════════════════════

1. Verify middleware in settings.py:
   Check MIDDLEWARE list includes:
   ✓ 'estateApp.middleware.subscription_middleware.SubscriptionValidationMiddleware'
   ✓ 'estateApp.middleware.subscription_middleware.SubscriptionRateLimitMiddleware'

2. Configure email settings in .env:
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com

3. Verify logging configuration:
   In settings.py, ensure LOGGING includes:
   'loggers': {
       'estateApp.services.alerts': {'level': 'INFO'},
       'estateApp.middleware.subscription_middleware': {'level': 'INFO'},
   }

4. Create log directory for cron job:
   $ mkdir -p /var/log/realestate
   $ chmod 755 /var/log/realestate


STEP 4: SCHEDULER SETUP (Choose One)
════════════════════════════════════════════════════════════════════════════════════

OPTION A: Cron Job (Recommended for Simple Setup)
───────────────────────────────────────────────────

1. Edit crontab:
   $ crontab -e

2. Add this line (runs every 6 hours):
   0 */6 * * * cd /path/to/estateProject && python manage.py check_subscriptions --verbose >> /var/log/realestate/subscription_checks.log 2>&1

3. Verify cron is registered:
   $ crontab -l | grep check_subscriptions
   Expected: Should see the cron entry

4. Monitor log file:
   $ tail -f /var/log/realestate/subscription_checks.log


OPTION B: Celery Beat (Recommended for Production)
──────────────────────────────────────────────────

1. Add to estateProject/celery_app.py:

   from celery.schedules import crontab
   from celery import Celery

   # ... existing code ...

   app.conf.beat_schedule = {
       'check-subscriptions': {
           'task': 'estateApp.tasks.check_subscriptions_task',
           'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
       },
   }

2. Add to estateApp/tasks.py:

   from celery import shared_task
   from django.core.management import call_command
   import logging

   logger = logging.getLogger(__name__)

   @shared_task(bind=True, name='estateApp.tasks.check_subscriptions_task')
   def check_subscriptions_task(self):
       """Celery task to check subscriptions every 6 hours"""
       try:
           call_command('check_subscriptions', verbose=True)
           return "Subscription check completed successfully"
       except Exception as e:
           logger.error(f"Subscription check failed: {str(e)}")
           raise

3. Start Celery Beat:
   $ celery -A estateProject worker -B --loglevel=info

4. Verify in logs:
   Expected: "Scheduler: Sending due task check-subscriptions"


STEP 5: TEMPLATE UPDATES (20 minutes)
════════════════════════════════════════════════════════════════════════════════════

1. Open templates/admin_side/index.html

2. Add alert section at top of content:

   {% if alerts.critical_alerts %}
   <div class="alert-container critical">
     {% for alert in alerts.critical_alerts %}
     <div class="alert alert-danger alert-dismissible" role="alert">
       <h5>{{ alert.title }}</h5>
       <p>{{ alert.message }}</p>
       {% if alert.action_url %}
       <a href="{{ alert.action_url }}" class="btn btn-primary">
         {{ alert.action_label }}
       </a>
       {% endif %}
       {% if alert.dismissible %}
       <button type="button" class="close" data-dismiss="alert">
         <span>&times;</span>
       </button>
       {% endif %}
     </div>
     {% endfor %}
   </div>
   {% endif %}

3. Add subscription widget:

   <div class="subscription-widget card">
     <div class="card-body">
       <h6>Subscription Status</h6>
       {% if subscription_info.is_trial %}
       <span class="badge badge-warning">Trial</span>
       <p>Days remaining: <strong>{{ subscription_info.days_remaining }}</strong></p>
       {% else %}
       <span class="badge badge-{% if subscription_info.is_active %}success{% else %}danger{% endif %}">
         {{ subscription_info.status|upper }}
       </span>
       {% endif %}
       
       {% if subscription_info.is_read_only %}
       <p class="text-danger"><strong>Read-Only Mode Active</strong></p>
       {% endif %}
     </div>
   </div>

4. Add usage metrics:

   {% if usage_metrics %}
   <div class="usage-metrics">
     {% for metric in usage_metrics %}
     <div class="metric-card">
       <h6>{{ metric.feature }}</h6>
       <div class="progress">
         <div class="progress-bar 
           {% if metric.is_exceeded %}bg-danger
           {% elif metric.is_warning %}bg-warning
           {% else %}bg-success{% endif %}"
         style="width: {{ metric.percentage }}%">
           {{ metric.percentage }}%
         </div>
       </div>
       <small>{{ metric.usage }} / {{ metric.limit }}</small>
     </div>
     {% endfor %}
   </div>
   {% endif %}


STEP 6: CREATE URL ROUTES (10 minutes)
════════════════════════════════════════════════════════════════════════════════════

Add to estateApp/urls.py:

from django.urls import path
from . import views

urlpatterns = [
    # ... existing routes ...
    
    # Trial and subscription endpoints
    path('trial-expired/', views.trial_expired, name='trial_expired'),
    path('account-suspended/', views.account_suspended, name='account_suspended'),
    path('upgrade/', views.upgrade_subscription, name='upgrade_subscription'),
    path('billing/renew/', views.renew_subscription, name='renew_subscription'),
]

Add to estateApp/views.py:

@login_required
def trial_expired(request):
    """Display trial expired page"""
    return render(request, 'trial_expired.html')

@login_required
def account_suspended(request):
    """Display account suspended page"""
    return render(request, 'account_suspended.html')

@login_required
def upgrade_subscription(request):
    """Display upgrade options"""
    return render(request, 'upgrade_subscription.html')

@login_required
def renew_subscription(request):
    """Display renew options"""
    return render(request, 'renew_subscription.html')


STEP 7: TEST IN STAGING (30 minutes)
════════════════════════════════════════════════════════════════════════════════════

1. Create test company:
   $ python manage.py shell
   >>> from estateApp.models import Company
   >>> from django.utils import timezone
   >>> from datetime import timedelta
   >>> 
   >>> test_co = Company.objects.create(
   ...     company_name="Test Subscription Co",
   ...     registration_number="TEST001",
   ...     registration_date="2025-01-01",
   ...     location="Test",
   ...     ceo_name="Test CEO",
   ...     ceo_dob="1990-01-01",
   ...     email="test@company.com",
   ...     phone="+1234567890",
   ...     subscription_status='trial',
   ...     trial_ends_at=timezone.now() + timedelta(days=7)
   ... )
   >>> print(f"Created company ID: {test_co.id}")

2. Test alert generation:
   >>> from estateApp.services.alerts import SubscriptionAlertService
   >>> alerts = SubscriptionAlertService.get_required_alerts(test_co)
   >>> print(alerts['warnings'])
   Expected: Should show warning alert for trial ending

3. Test management command:
   $ python manage.py check_subscriptions --company-id 1 --verbose
   Expected: Should process company without errors

4. Create admin user:
   $ python manage.py shell
   >>> from estateApp.models import CustomUser
   >>> user = CustomUser.objects.create_user(
   ...     email='admin@test.com',
   ...     full_name='Admin User',
   ...     phone='+1111111111',
   ...     password='testpass123',
   ...     company_profile=test_co,
   ...     role='admin',
   ...     admin_level='company',
   ...     address='Test Address'
   ... )

5. Access dashboard:
   Visit http://localhost:8000/admin-dashboard/
   Expected: Should see alerts in dashboard

6. Verify alerts display:
   Check browser console for errors
   Verify alerts render correctly
   Test alert dismissal


STEP 8: PRODUCTION DEPLOYMENT (15 minutes)
════════════════════════════════════════════════════════════════════════════════════

1. Perform final backup:
   $ pg_dump multi_tenant_db > multi_tenant_db.backup.pre-phase5.sql

2. Deploy code:
   $ git pull origin main
   $ pip install -r requirements.txt

3. Run migrations:
   $ python manage.py migrate estateApp

4. Collect static files (if needed):
   $ python manage.py collectstatic --noinput

5. Restart application:
   $ systemctl restart realestate_app
   OR for gunicorn:
   $ pkill gunicorn
   $ nohup gunicorn estateProject.wsgi:application --bind 0.0.0.0:8000 &

6. Start cron/celery (if using scheduler):
   $ crontab -e  # Add schedule
   OR
   $ celery -A estateProject worker -B --loglevel=info

7. Verify deployment:
   Visit http://yourdomain.com/admin-dashboard/
   Check system logs for errors
   Monitor subscription_checks.log


STEP 9: MONITORING & MAINTENANCE (Ongoing)
════════════════════════════════════════════════════════════════════════════════════

Daily Tasks:
□ Monitor /var/log/realestate/subscription_checks.log
□ Check for alert creation errors
□ Verify no database locks

Weekly Tasks:
□ Review subscription status of top 10 customers
□ Check email delivery logs
□ Verify read-only mode enforcement

Monthly Tasks:
□ Review alert statistics
□ Analyze trial conversion rates
□ Check data retention policies


STEP 10: ROLLBACK PLAN (In case of issues)
════════════════════════════════════════════════════════════════════════════════════

If Critical Error Occurs:

1. Stop the application:
   $ systemctl stop realestate_app

2. Restore database backup:
   $ psql < multi_tenant_db.backup.pre-phase5.sql

3. Revert code:
   $ git revert <commit-hash>

4. Clear middleware cache:
   $ python manage.py clear_cache

5. Restart application:
   $ systemctl start realestate_app

6. Verify rollback:
   $ python manage.py check


════════════════════════════════════════════════════════════════════════════════════
ESTIMATED DEPLOYMENT TIME: 2-3 hours
SUCCESS CRITERIA: All steps complete, 29 tests passing, no errors in logs
════════════════════════════════════════════════════════════════════════════════════
"""

print(DEPLOYMENT_STEPS)
