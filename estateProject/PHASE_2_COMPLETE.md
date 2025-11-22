# Phase 2 Implementation - Complete

## Overview
Phase 2 focuses on **Error Tracking, Rate Limiting, and Audit Logging** for the multi-tenant architecture.

**Status**: ✅ COMPLETE (November 19, 2025)

---

## 1. API Rate Limiting (`throttles.py`)

### Components
- **SubscriptionTierThrottle**: Tier-based rate limiting
  - Starter: 100 requests/hour
  - Professional: 1,000 requests/hour
  - Enterprise: 10,000 requests/hour (custom)
  - Trial: 500 requests/hour

- **AnonymousUserThrottle**: IP-based throttling for unauthenticated users
  - 50 requests/hour limit
  - Prevents abuse from unknown IPs

- **APILimitExceededHandler**: Sends notifications when limits are hit

### Configuration
```python
# In REST_FRAMEWORK settings
'DEFAULT_THROTTLE_CLASSES': [
    'estateApp.throttles.SubscriptionTierThrottle',
    'estateApp.throttles.AnonymousUserThrottle',
]

'DEFAULT_THROTTLE_RATES': {
    'anon': '50/hour',
    'user': '1000/hour',
}
```

### Usage in Views
```python
from rest_framework.views import APIView
from estateApp.throttles import SubscriptionTierThrottle

class PropertyListView(APIView):
    throttle_classes = [SubscriptionTierThrottle]
    
    def get(self, request):
        # Will be throttled based on company subscription tier
        pass
```

---

## 2. Advanced Permissions (`permissions.py`)

### Permission Classes

#### Core Permissions
- **IsAuthenticated**: Only authenticated users
- **IsCompanyOwnerOrAdmin**: Owner or admin access only
- **IsCompanyMember**: Must be company member
- **SubscriptionRequiredPermission**: Active subscription check
- **TenantIsolationPermission**: Strict multi-tenant isolation

#### Feature-Based Permissions
- **FeatureAccessPermission**: Feature gates by subscription tier
  - Maps features to minimum required tier
  - Prevents unauthorized feature access

#### Advanced Permissions
- **APIKeyPermission**: API key validation
- **ReadOnlyPermission**: GET/HEAD/OPTIONS only
- **IsOwnerOrReadOnly**: Owner edit, others read
- **SubscriptionTierPermission**: Custom tier-based limits

### Feature Tier Mapping
```python
FEATURE_TIERS = {
    'advanced_analytics': 'professional',
    'api_access': 'professional',
    'custom_branding': 'professional',
    'bulk_operations': 'professional',
    'automation': 'enterprise',
    'sso': 'enterprise',
    'advanced_reporting': 'enterprise',
    'white_label': 'enterprise',
}
```

### Usage in Views
```python
from rest_framework.views import APIView
from estateApp.permissions import FeatureAccessPermission

class AdvancedAnalyticsView(APIView):
    permission_classes = [FeatureAccessPermission]
    required_feature = 'advanced_analytics'
    
    def get(self, request):
        # Only accessible to Professional+ tier
        pass
```

---

## 3. Multi-Method Authentication (`authentication.py`)

### Authentication Classes

#### Standard Methods
- **BearerTokenAuthentication**: Bearer token in Authorization header
- **APIKeyAuthentication**: X-API-Key header support
- **TenantAwareTokenAuthentication**: Token + company extraction
- **SessionAuthentication**: Django session auth with company

#### Advanced Methods
- **JWTTenantAuthentication**: JWT with tenant claim (company_id)
- **OAuthTokenAuthentication**: OAuth token for third-party integrations

### Configuration
```python
# In settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'estateApp.authentication.APIKeyAuthentication',
        'estateApp.authentication.BearerTokenAuthentication',
        'estateApp.authentication.TenantAwareTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

### Authentication Usage

#### API Key
```bash
curl -H "X-API-Key: your-api-key" https://api.example.com/api/properties/
```

#### Bearer Token
```bash
curl -H "Authorization: Bearer your-token" https://api.example.com/api/properties/
```

#### JWT
```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." https://api.example.com/api/properties/
```

---

## 4. Multi-Tenant Middleware (`tenant_middleware.py`)

### Middleware Components

#### TenantMiddleware
- Extracts company from: URL params, headers, authenticated user, API key
- Sets `request.company` for all views
- Public path handling

#### TenantIsolationMiddleware
- Enforces strict tenant isolation
- Prevents cross-tenant data access
- Logs isolation violations

#### RateLimitMiddleware
- Tracks API usage statistics
- Updates daily usage cache
- Adds usage headers to responses

#### RequestLoggingMiddleware
- Logs all API requests
- Creates audit trail
- Tracks request/response times

#### SecurityHeadersMiddleware
- Adds security headers
- Prevents common vulnerabilities

#### CompanyContextMiddleware
- Manages company context in thread-local storage
- Available to signals and background tasks

### Middleware Configuration
```python
# In settings.py MIDDLEWARE list
MIDDLEWARE = [
    # ... other middleware
    'estateApp.tenant_middleware.TenantMiddleware',
    'estateApp.tenant_middleware.TenantIsolationMiddleware',
    'estateApp.tenant_middleware.RateLimitMiddleware',
    'estateApp.tenant_middleware.RequestLoggingMiddleware',
    'estateApp.tenant_middleware.SecurityHeadersMiddleware',
    'estateApp.tenant_middleware.CompanyContextMiddleware',
]
```

---

## 5. Advanced Filtering (`api_filters.py`)

### Filter Backends

#### Automatic Filtering
- **CompanyAwareFilterBackend**: Auto-filters by company
- **SearchFilterBackend**: Full-text search across fields
- **OrderingFilterBackend**: Result ordering

#### Date & Status Filtering
- **DateRangeFilterBackend**: Date range filtering
- **StatusFilterBackend**: Status field filtering
- **OwnerFilterBackend**: Filter by creator

#### Advanced Filtering
- **RelationshipFilterBackend**: Related field filtering
- **BulkOperationFilterBackend**: Multiple ID filtering
- **AggregationFilterBackend**: Aggregation queries

### Usage in Views
```python
from rest_framework.viewsets import ModelViewSet
from estateApp.api_filters import get_default_filters

class PropertyViewSet(ModelViewSet):
    queryset = Property.objects.all()
    filter_backends = get_default_filters().filters
    
    def get_queryset(self):
        # Automatically filtered by company, search, ordering, etc.
        return super().get_queryset()
```

### Query Parameters
```
# Search
GET /api/properties/?search=luxury

# Date range
GET /api/properties/?start_date=2025-01-01&end_date=2025-12-31

# Ordering
GET /api/properties/?ordering=-created_at,name

# Status
GET /api/properties/?status=active

# Bulk
GET /api/properties/?ids=1,2,3,4,5

# Relationships
GET /api/properties/?agent_id=42&category_id=7
```

---

## 6. Error Tracking (`error_tracking.py`)

### Components

#### SentryErrorTracker
- Initializes Sentry with Django integration
- Captures exceptions with context
- Sets user and request context
- Tracks error metadata

#### ErrorHandler
- Centralized error handling
- Different handlers for: API errors, Celery tasks, DB errors, External APIs
- Automatic Sentry integration

#### Decorators
- **@track_errors**: Auto-capture exceptions in functions
- **@track_operation**: Performance monitoring
- Tracks slow operations

#### ErrorNotificationService
- Sends email alerts for critical errors
- Quota exceeded notifications
- Admin notifications

#### PerformanceMonitor
- Tracks operation performance
- Warns on slow operations
- Captures to Sentry

### Configuration (`.env`)
```env
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_SEND_PII=False
ERROR_TRACKING_ENABLED=True
NOTIFY_ADMINS_ON_ERROR=True
```

### Usage Examples

#### Track Function Errors
```python
from estateApp.error_tracking import track_errors

@track_errors(error_type='celery')
def process_payment(company_id, amount):
    # Exceptions automatically captured
    pass
```

#### Handle API Errors
```python
from estateApp.error_tracking import ErrorHandler

try:
    process_listing(data)
except Exception as e:
    ErrorHandler.handle_api_error(e, request=request, view=self)
```

#### Monitor Performance
```python
from estateApp.error_tracking import PerformanceMonitor

@PerformanceMonitor.track_operation(operation_type='database', threshold=0.5)
def complex_query():
    # Warns if takes > 0.5s
    pass
```

---

## 7. Audit Logging (`audit_logging.py`)

### AuditLog Model
Tracks all significant actions with:
- User who performed action
- Company context
- Action type (CREATE, UPDATE, DELETE, etc.)
- Object affected (content type + ID)
- Old and new values (for changes)
- Request context (IP, user agent, path)
- Status (success/failure)
- Timestamps

### Action Types
```
CREATE            - Object created
UPDATE            - Object modified
DELETE            - Object deleted
READ              - Data accessed
LOGIN/LOGOUT      - Authentication
PERMISSION_CHANGE - Permission updated
SUBSCRIPTION_CHANGE - Tier changed
API_KEY_CREATED   - API key created
API_KEY_REVOKED   - API key revoked
EXPORT            - Data exported
IMPORT            - Data imported
BULK_OPERATION    - Bulk action performed
SECURITY_EVENT    - Security issue
PAYMENT           - Payment processed
```

### AuditLogger - Logging Actions

#### Log Creation
```python
from estateApp.audit_logging import AuditLogger

AuditLogger.log_create(
    user=request.user,
    company=request.company,
    instance=property_obj,
    request=request,
    extra_fields=['address', 'price']
)
```

#### Log Update
```python
AuditLogger.log_update(
    user=request.user,
    company=request.company,
    instance=property_obj,
    old_values={'price': 100000},
    new_values={'price': 120000},
    request=request
)
```

#### Log Deletion
```python
AuditLogger.log_delete(
    user=request.user,
    company=request.company,
    instance=property_obj,
    request=request
)
```

#### Log Specialized Events
```python
# Permission change
AuditLogger.log_permission_change(
    user=admin_user,
    company=company,
    target_user=user,
    old_perms=['view', 'edit'],
    new_perms=['view', 'edit', 'delete'],
    request=request
)

# Subscription change
AuditLogger.log_subscription_change(
    user=admin_user,
    company=company,
    old_tier='starter',
    new_tier='professional',
    request=request
)

# API key action
AuditLogger.log_api_key_action(
    user=user,
    company=company,
    api_key=key,
    action='API_KEY_CREATED',
    request=request
)

# Data export
AuditLogger.log_export(
    user=user,
    company=company,
    export_type='properties',
    record_count=523,
    request=request
)

# Payment
AuditLogger.log_payment(
    user=user,
    company=company,
    amount=299.99,
    status='SUCCESS',
    transaction_id='txn_12345',
    request=request
)

# Security event
AuditLogger.log_security_event(
    user=None,
    company=company,
    event_type='suspicious_activity',
    description='Multiple failed login attempts',
    severity='HIGH',
    request=request
)
```

### AuditLogQuery - Querying Logs

```python
from estateApp.audit_logging import AuditLogQuery

# Get user's recent actions (last 7 days)
logs = AuditLogQuery.get_user_actions(user, company=company, days=7)

# Get all company activity
logs = AuditLogQuery.get_company_activity(company, days=30)

# Get specific action type
logs = AuditLogQuery.get_company_activity(company, action='DELETE')

# Get failed actions
logs = AuditLogQuery.get_failed_actions(company, days=7)

# Get object history
logs = AuditLogQuery.get_object_history(property_obj)

# Get security events
logs = AuditLogQuery.get_security_events(company, severity='HIGH')

# Get statistics
stats = AuditLogQuery.get_statistics(company, days=7)
# Returns: total_actions, by_action, by_user, successful, failed
```

---

## 8. Settings Configuration (`settings_config.py`)

### DRF Configuration
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [...],
    'DEFAULT_PERMISSION_CLASSES': [...],
    'DEFAULT_THROTTLE_CLASSES': [...],
    'DEFAULT_FILTER_BACKENDS': [...],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

### Middleware Stack
All multi-tenant middleware configured and ordered

### Sentry Configuration
- Automatic error tracking
- Performance monitoring
- Trace sampling
- PII handling

### Audit Logging Configuration
- Enable/disable audit logging
- Retention period (default: 365 days)
- Actions to always audit
- Optional audit actions

### Rate Limiting Configuration
- Enable/disable rate limiting
- Per-tier API call limits
- Cache backend configuration

### Subscription Tiers
```python
SUBSCRIPTION_TIERS = {
    'starter': {
        'api_calls_daily': 10000,
        'max_properties': 50,
        'max_users': 1,
    },
    'professional': {
        'api_calls_daily': 100000,
        'max_properties': 500,
        'max_users': 5,
    },
    'enterprise': {
        'api_calls_daily': None,  # Unlimited
        'max_properties': None,
        'max_users': None,
    },
}
```

### Feature Flags
Maps features to minimum subscription tier required:
- `api_access` → Professional
- `advanced_analytics` → Professional
- `custom_branding` → Professional
- `automation` → Enterprise
- `sso` → Enterprise
- `white_label` → Enterprise

---

## Integration Guide

### Step 1: Update `settings.py`
Import and apply all configurations:
```python
from estateApp.settings_config import *

# Override/customize as needed
SENTRY_DSN = os.environ.get('SENTRY_DSN')
ADMIN_EMAILS = ['admin@example.com']
```

### Step 2: Configure Environment Variables
```bash
# Error Tracking
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
SENTRY_TRACES_SAMPLE_RATE=0.1
ERROR_TRACKING_ENABLED=True

# Audit Logging
AUDIT_LOGGING_ENABLED=True
AUDIT_LOG_RETENTION_DAYS=365

# Rate Limiting
RATE_LIMIT_ENABLED=True
REDIS_URL=redis://localhost:6379/1

# Email Notifications
ADMIN_EMAILS=admin@example.com,support@example.com
NOTIFY_ADMINS_ON_ERROR=True
```

### Step 3: Create Audit Log Migration
```python
# In estateApp/migrations/
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('estateApp', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                # ... fields from audit_logging.py AuditLog model
            ],
        ),
    ]
```

Then run:
```bash
python manage.py migrate
```

### Step 4: Use in Views/Serializers

```python
# In serializers or views
from estateApp.permissions import FeatureAccessPermission, SubscriptionRequiredPermission
from estateApp.throttles import SubscriptionTierThrottle
from estateApp.audit_logging import AuditLogger

class PropertyViewSet(ModelViewSet):
    permission_classes = [
        SubscriptionRequiredPermission,
        FeatureAccessPermission,
    ]
    throttle_classes = [SubscriptionTierThrottle]
    required_feature = 'api_access'
    
    def perform_create(self, serializer):
        instance = serializer.save()
        AuditLogger.log_create(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            request=self.request,
        )
    
    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_values = model_to_dict(old_instance)
        
        instance = serializer.save()
        new_values = model_to_dict(instance)
        
        AuditLogger.log_update(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    def perform_destroy(self, instance):
        AuditLogger.log_delete(
            user=self.request.user,
            company=self.request.company,
            instance=instance,
            request=self.request,
        )
        instance.delete()
```

---

## Testing

### Test Error Tracking
```python
from estateApp.error_tracking import SentryErrorTracker, track_errors

def test_error_tracking():
    try:
        raise ValueError("Test error")
    except Exception as e:
        SentryErrorTracker.capture_exception(e, tags={'test': 'true'})

@track_errors(error_type='test')
def test_decorator():
    raise RuntimeError("Decorated error")
```

### Test Rate Limiting
```python
from rest_framework.test import APIClient

client = APIClient()
for i in range(100):
    response = client.get('/api/properties/')
# 101st request should be throttled
response = client.get('/api/properties/')
assert response.status_code == 429  # Too Many Requests
```

### Test Audit Logging
```python
from estateApp.audit_logging import AuditLogger, AuditLogQuery

AuditLogger.log_create(
    user=user,
    company=company,
    instance=obj,
)

logs = AuditLogQuery.get_company_activity(company)
assert logs.count() >= 1
assert logs[0].action == 'CREATE'
```

---

## Performance Considerations

### Caching
- Company subscription cached for 1 hour
- Rate limit counters in Redis
- API responses cached for 5 minutes

### Database
- Audit logs indexed by company and created_at
- Queries optimized for multi-tenant data

### Throttling
- Per-company rate limits reduce abuse
- Anonymous users limited to prevent scraping

---

## Next Steps (Phase 3)

1. **Migrate Endpoints to DRF**
   - Move 30+ endpoints from estateApp to DRF app
   - Apply new permissions, throttles, and middleware
   - Add audit logging to all endpoints

2. **API Documentation**
   - Swagger/OpenAPI schema
   - Rate limit documentation
   - Authentication guide

3. **Monitoring & Dashboards**
   - API usage dashboard
   - Error rate monitoring
   - Performance metrics

---

## Files Created

✅ `estateApp/throttles.py` - Rate limiting
✅ `estateApp/permissions.py` - Advanced permissions
✅ `estateApp/authentication.py` - Multi-method authentication
✅ `estateApp/tenant_middleware.py` - Multi-tenant middleware
✅ `estateApp/api_filters.py` - Advanced filtering
✅ `estateApp/error_tracking.py` - Error tracking with Sentry
✅ `estateApp/audit_logging.py` - Audit logging model and service
✅ `estateApp/settings_config.py` - Configuration templates

---

**Completion Date**: November 19, 2025
**Status**: ✅ READY FOR TESTING & INTEGRATION
