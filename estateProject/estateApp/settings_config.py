"""
Django settings configuration for multi-tenant architecture.
Consolidates all authentication, permission, throttle, and middleware settings.
"""

# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

AUTHENTICATION_BACKENDS = [
    'estateApp.authentication.APIKeyAuthentication',
    'estateApp.authentication.BearerTokenAuthentication',
    'estateApp.authentication.JWTTenantAuthentication',
    'estateApp.authentication.OAuthTokenAuthentication',
    'django.contrib.auth.backends.ModelBackend',  # Default Django auth
]

# REST Framework settings
REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'estateApp.authentication.APIKeyAuthentication',
        'estateApp.authentication.BearerTokenAuthentication',
        'estateApp.authentication.TenantAwareTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    
    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'estateApp.permissions.IsAuthenticated',
        'estateApp.permissions.TenantIsolationPermission',
    ],
    
    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'estateApp.throttles.SubscriptionTierThrottle',
        'estateApp.throttles.AnonymousUserThrottle',
    ],
    
    'DEFAULT_THROTTLE_RATES': {
        'anon': '50/hour',
        'user': '1000/hour',
    },
    
    # Filtering & Search
    'DEFAULT_FILTER_BACKENDS': [
        'estateApp.api_filters.CompanyAwareFilterBackend',
        'estateApp.api_filters.SearchFilterBackend',
        'estateApp.api_filters.OrderingFilterBackend',
        'estateApp.api_filters.DateRangeFilterBackend',
    ],
    
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    
    # Versioning
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    
    # Renderers
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    
    # Other
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'EXCEPTION_HANDLER': 'estateApp.utils.custom_exception_handler',
}

# ============================================================================
# MIDDLEWARE
# ============================================================================

MIDDLEWARE = [
    # Security
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    
    # Session & Auth
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # Custom middleware for multi-tenant
    'estateApp.tenant_middleware.TenantMiddleware',
    'estateApp.tenant_middleware.TenantIsolationMiddleware',
    'estateApp.tenant_middleware.RateLimitMiddleware',
    'estateApp.tenant_middleware.RequestLoggingMiddleware',
    'estateApp.tenant_middleware.SecurityHeadersMiddleware',
    'estateApp.tenant_middleware.CompanyContextMiddleware',
    
    # Localization
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================================
# ERROR TRACKING (SENTRY)
# ============================================================================

# Sentry configuration
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', 0.1))
SENTRY_PROFILES_SAMPLE_RATE = float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', 0.1))
SENTRY_SEND_PII = os.environ.get('SENTRY_SEND_PII', 'False').lower() == 'true'

# Error handling
ERROR_TRACKING_ENABLED = os.environ.get('ERROR_TRACKING_ENABLED', 'True').lower() == 'true'
NOTIFY_ADMINS_ON_ERROR = os.environ.get('NOTIFY_ADMINS_ON_ERROR', 'True').lower() == 'true'

# ============================================================================
# AUDIT LOGGING
# ============================================================================

AUDIT_LOGGING_ENABLED = os.environ.get('AUDIT_LOGGING_ENABLED', 'True').lower() == 'true'

# Events to always audit
ALWAYS_AUDIT_ACTIONS = [
    'DELETE',
    'PERMISSION_CHANGE',
    'SUBSCRIPTION_CHANGE',
    'API_KEY_CREATED',
    'API_KEY_REVOKED',
    'PAYMENT',
    'SECURITY_EVENT',
]

# Events to optionally audit
OPTIONAL_AUDIT_ACTIONS = [
    'CREATE',
    'UPDATE',
    'BULK_OPERATION',
    'EXPORT',
]

# Audit log retention
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 365))

# ============================================================================
# RATE LIMITING
# ============================================================================

RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'

# API Rate limits by subscription tier (requests per hour)
API_RATE_LIMITS = {
    'starter': 100,
    'trial': 500,
    'professional': 1000,
    'enterprise': 10000,
}

# Cache configuration for rate limiting
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'estateapp',
        'TIMEOUT': 300,
    }
}

# ============================================================================
# SUBSCRIPTION TIERS
# ============================================================================

SUBSCRIPTION_TIERS = {
    'starter': {
        'name': 'Starter',
        'price': 99,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'api_calls_daily': 10000,
        'max_properties': 50,
        'max_users': 1,
        'features': [
            'basic_listings',
            'email_support',
        ],
    },
    'professional': {
        'name': 'Professional',
        'price': 299,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'api_calls_daily': 100000,
        'max_properties': 500,
        'max_users': 5,
        'features': [
            'advanced_listings',
            'api_access',
            'custom_branding',
            'priority_support',
        ],
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 999,
        'currency': 'USD',
        'billing_cycle': 'monthly',
        'api_calls_daily': None,  # Unlimited
        'max_properties': None,
        'max_users': None,
        'features': [
            'white_label',
            'sso',
            'advanced_analytics',
            'dedicated_support',
            'custom_integrations',
        ],
    },
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURE_FLAGS = {
    'api_access': {
        'min_tier': 'professional',
        'enabled': True,
    },
    'advanced_analytics': {
        'min_tier': 'professional',
        'enabled': True,
    },
    'custom_branding': {
        'min_tier': 'professional',
        'enabled': True,
    },
    'automation': {
        'min_tier': 'enterprise',
        'enabled': True,
    },
    'sso': {
        'min_tier': 'enterprise',
        'enabled': True,
    },
    'white_label': {
        'min_tier': 'enterprise',
        'enabled': True,
    },
}

# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-api-key',
    'x-company-id',
    'x-csrf-token',
]

# CSRF settings
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# Session settings
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_TIMEOUT = 3600  # 1 hour

# ============================================================================
# API KEY SETTINGS
# ============================================================================

API_KEY_LENGTH = 32
API_KEY_EXPIRATION_DAYS = 365
API_KEY_ROTATION_ENABLED = True

# ============================================================================
# LOGGING
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/estateapp.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'json',
            'level': 'ERROR',
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/audit.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'estateApp': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG',
        },
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
        },
    },
}

# ============================================================================
# ADMIN EMAILS
# ============================================================================

ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', '').split(',')
NOTIFY_ON_QUOTA_EXCEEDED = True
NOTIFY_ON_PAYMENT_FAILURE = True

# ============================================================================
# CELERY & ASYNC TASKS
# ============================================================================

CELERY_ALWAYS_EAGER = DEBUG  # Execute tasks synchronously in development
CELERY_TASK_ROUTES = {
    'estateApp.tasks.send_error_notification': {'queue': 'priority'},
    'estateApp.tasks.cleanup_audit_logs': {'queue': 'background'},
}

# ============================================================================
# PERFORMANCE & CACHING
# ============================================================================

# Enable query optimization
ENABLE_QUERY_OPTIMIZATION = True

# Cache company subscription info
CACHE_SUBSCRIPTION_TTL = 3600  # 1 hour

# API response caching
API_CACHE_TIMEOUT = 300  # 5 minutes for GET requests

# ============================================================================
# EXPORT & IMPORT
# ============================================================================

ALLOW_DATA_EXPORT = True
ALLOW_DATA_IMPORT = True
MAX_IMPORT_FILE_SIZE = 52428800  # 50MB
ALLOWED_IMPORT_FORMATS = ['csv', 'json', 'xml']
ALLOWED_EXPORT_FORMATS = ['csv', 'json', 'xml', 'pdf', 'excel']
