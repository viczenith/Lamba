# ==============================================================================
# PRODUCTION SETTINGS FOR SCALING
# ==============================================================================
# This file extends base settings for production deployment
# Can handle 10,000 - 100,000 concurrent users with proper infrastructure
# ==============================================================================

import os
from .settings import *  # Import all base settings

# ==============================================================================
# SECURITY SETTINGS (CRITICAL FOR PRODUCTION)
# ==============================================================================
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# HTTPS Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# ==============================================================================
# DATABASE CONFIGURATION (PostgreSQL with Connection Pooling)
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'estate_db'),
        'USER': os.environ.get('DB_USER', 'estate_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # Persistent connections
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30s query timeout
        },
        'ATOMIC_REQUESTS': True,
    }
}

# ==============================================================================
# READ REPLICA CONFIGURATION (Uncomment when ready to scale)
# ==============================================================================
# DATABASES['replica'] = {
#     'ENGINE': 'django.db.backends.postgresql',
#     'NAME': os.environ.get('DB_NAME', 'estate_db'),
#     'USER': os.environ.get('DB_USER', 'estate_user'),
#     'PASSWORD': os.environ.get('DB_PASSWORD'),
#     'HOST': os.environ.get('DB_REPLICA_HOST', 'localhost'),  # Replica host
#     'PORT': os.environ.get('DB_PORT', '5432'),
#     'CONN_MAX_AGE': 60,
# }
# DATABASE_ROUTERS = ['estateApp.db_routers.PrimaryReplicaRouter']

# ==============================================================================
# REDIS CACHING (Critical for Performance)
# ==============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Don't crash if Redis is down
        },
        'KEY_PREFIX': 'estate',
        'TIMEOUT': 300,  # 5 minutes default
    },
    # Separate cache for sessions (higher priority)
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        },
        'KEY_PREFIX': 'session',
        'TIMEOUT': 86400,  # 24 hours for sessions
    },
}

# Use Redis for sessions (MUCH faster than database)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'

# ==============================================================================
# CELERY CONFIGURATION (Background Tasks)
# ==============================================================================
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevent task hoarding
CELERY_TASK_ACKS_LATE = True  # Acknowledge after completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Task routing for priority queues
CELERY_TASK_ROUTES = {
    'estateApp.tasks.send_*': {'queue': 'high_priority'},
    'estateApp.tasks.generate_*': {'queue': 'low_priority'},
    'estateApp.tasks.process_bulk_*': {'queue': 'bulk'},
}

# ==============================================================================
# AWS S3 STORAGE (Media Files)
# ==============================================================================
if os.environ.get('USE_S3', 'false').lower() == 'true':
    # AWS Credentials
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    
    # S3 Settings
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # 1 day cache
    }
    AWS_DEFAULT_ACL = None  # Use bucket default ACL
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False  # Public URLs
    
    # CloudFront CDN (if configured)
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_CLOUDFRONT_DOMAIN')
    
    # Storage backends
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    
    # Media URL
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    else:
        MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/media/'

# ==============================================================================
# LOGGING CONFIGURATION (Production)
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/estate/django.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/estate/security.log',
            'maxBytes': 50 * 1024 * 1024,  # 50 MB
            'backupCount': 20,
            'formatter': 'json',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'estateApp': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ==============================================================================
# PERFORMANCE OPTIMIZATIONS
# ==============================================================================

# Template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# Disable template debug in production
TEMPLATES[0]['OPTIONS']['debug'] = False

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = False  # Only save when modified

# ==============================================================================
# MONITORING (Sentry - Error Tracking)
# ==============================================================================
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of requests for performance monitoring
        send_default_pii=False,
        environment=os.environ.get('ENVIRONMENT', 'production'),
    )

# ==============================================================================
# CORS & API SETTINGS
# ==============================================================================
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True

# API Rate Limiting (via middleware)
API_RATE_LIMIT = {
    'default': '1000/hour',
    'authenticated': '5000/hour',
    'anonymous': '100/hour',
}

# ==============================================================================
# HEALTH CHECK ENDPOINT
# ==============================================================================
# Add to urls.py: path('health/', health_check, name='health_check')
