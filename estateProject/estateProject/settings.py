from pathlib import Path
import os
import secrets
import dj_database_url
from dotenv import load_dotenv

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

def get_bool_env(var_name: str, default: bool = False) -> bool:
    value = os.environ.get(var_name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y", "on"}


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_bool_env('DEBUG', default=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        secret_file = BASE_DIR / '.secret_key'
        if secret_file.exists():
            SECRET_KEY = secret_file.read_text().strip()
        else:
            SECRET_KEY = secrets.token_urlsafe(64)
            secret_file.write_text(SECRET_KEY)
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable is required')



raw_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [host.strip() for host in raw_allowed_hosts.split(',') if host.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*']


# Application definition

# Security: Dynamic Admin URL (generated at startup)
import secrets
ADMIN_URL_SLUG = secrets.token_urlsafe(32)  # Generate random slug

# Security: Rate Limiting Configuration
SECURITY_RATE_LIMIT_LOGIN_ATTEMPTS = 5  # Max attempts
SECURITY_RATE_LIMIT_LOGIN_WINDOW = 300  # 5 minutes
SECURITY_RATE_LIMIT_LOCKOUT_DURATION = 900  # 15 minutes

# Security: IP Whitelist for Super Admin (optional, empty = allow all)
SUPERADMIN_IP_WHITELIST = []  # Example: ['127.0.0.1', '192.168.1.0/24']

# Security: Session Settings
# Cookie security flags should be enabled in production (DEBUG=False)
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_AGE = 3600  # 1 hour default
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Security: Password Validation (Enhanced)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'channels',
    
    # Core Apps
    'estateApp',
    'adminSupport',
    'DRF',
    
    # Super Admin - Master Tenant Management
    'superAdmin',
    
    # Third-party apps
    'widget_tweaks',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
]

REST_FRAMEWORK = {
    # ===== AUTHENTICATION =====
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    
    # ===== PERMISSIONS =====
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    
    # ===== EXCEPTION HANDLING =====
    'EXCEPTION_HANDLER': 'DRF.shared_drf.exception_handler.custom_exception_handler',
    
    # ===== PAGINATION =====
    'DEFAULT_PAGINATION_CLASS': 'DRF.shared_drf.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    
    # ===== FILTERING & SEARCH =====
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    
    # ===== THROTTLING =====
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    
    # ===== RENDERING & PARSING =====
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    
    # ===== API DOCUMENTATION =====
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.AutoSchema',
    
    # ===== VALIDATION & ERRORS =====
    'COERCE_DECIMAL_TO_STRING': False,
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Session expiration middleware (must be after authentication)
    'estateApp.middleware.SessionExpirationMiddleware',
    
    # ADVANCED SECURITY MIDDLEWARE (after authentication)
    'estateApp.middleware.AdvancedSecurityMiddleware',     # Request validation & rate limiting
    'estateApp.middleware.SessionSecurityMiddleware',      # Session hijacking protection
    'estateApp.middleware.PageLoadOptimizationMiddleware', # Performance optimization
    
    # ENHANCED Multi-Tenant Middleware (MUST be after authentication)
    # These layers provide automatic query interception + security enforcement
    'superAdmin.enhanced_middleware.EnhancedTenantIsolationMiddleware',  # Auto-detects tenant, sets context
    'superAdmin.enhanced_middleware.TenantValidationMiddleware',          # Validates tenant context
    'estateApp.middleware.ReadOnlyModeMiddleware',                        # Server-side read-only enforcement
    'superAdmin.enhanced_middleware.SubscriptionEnforcementMiddleware',   # Plan limit enforcement
    'superAdmin.enhanced_middleware.AuditLoggingMiddleware',              # Compliance audit trail
    'superAdmin.enhanced_middleware.SecurityHeadersMiddleware',           # XSS/MIME/clickjacking protection
]

CORS_ALLOWED_ORIGINS = [
  "http://localhost:8080",
  "http://localhost:5601",
  "http://192.168.110.208:5555",
  "http://192.168.110.208:8000",
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'estateProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'estateApp.context_processors.chat_notifications',
                'estateApp.context_processors.user_notifications',
                'estateApp.context_processors.dashboard_url',
                'estateApp.context_processors.subscription_alerts',
                'estateApp.context_processors.plan_usage',
            ],
        },
    },
]

WSGI_APPLICATION = 'estateProject.wsgi.application'
ASGI_APPLICATION = 'estateProject.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')],
        },
    }
}


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Load environment variables
load_dotenv()

# Database configuration
# DATABASES = {
#     'default': dj_database_url.config(
#         default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
#         conn_max_age=600,
#         conn_health_checks=True,
#     )
# }

# For local development, you can uncomment this to use SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# If you need to use the old style PostgreSQL configuration, uncomment and modify this:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('POSTGRES_DB', ''),
#         'USER': os.environ.get('POSTGRES_USER', ''),
#         'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
#         'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
#         'PORT': os.environ.get('POSTGRES_PORT', '5432'),
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# For production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'estateApp', 'static'),
    os.path.join(BASE_DIR, 'adminSupport', 'static'),
]


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


AUTH_USER_MODEL = 'estateApp.CustomUser'
CSRF_FAILURE_VIEW = 'estateApp.views.custom_csrf_failure_view'


LOGIN_URL = '/login/'
# LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/' 

# Canonical session settings (use 1 hour sliding expiry)
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True


AUTHENTICATION_BACKENDS = (
    'estateApp.backends.EmailBackend',
)

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.SUCCESS: 'success',
}

# ============================================
# ADVANCED SECURITY SETTINGS
# ============================================

# Session Security
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True     # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF protection
SESSION_COOKIE_AGE = 86400         # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # Refresh session on each request

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG     # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True        # Prevent JavaScript access
CSRF_COOKIE_SAMESITE = 'Lax'       # Additional CSRF protection
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # Add your production domains here
]

# Security Headers (some handled by middleware)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# HTTPS Settings (enable in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Rate Limiting Configuration
RATE_LIMIT_ENABLED = True
RATE_LIMIT_LOGIN_ATTEMPTS = 5      # Max login attempts
RATE_LIMIT_LOGIN_WINDOW = 300      # 5 minutes window
RATE_LIMIT_API_REQUESTS = 100      # Max API requests per minute
RATE_LIMIT_PAGE_REQUESTS = 60      # Max page loads per minute

# Security Logging
SECURITY_LOG_ENABLED = True
SECURITY_LOG_FAILED_LOGINS = True
SECURITY_LOG_SUSPICIOUS_REQUESTS = True

# Logging Configuration for Security Events
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security': {
            'format': '[{asctime}] {levelname} {name} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'security',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'security',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
LOGS_DIR = BASE_DIR / 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Firebase / push notifications 
FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH')
FIREBASE_DEFAULT_ICON = os.environ.get('FIREBASE_DEFAULT_ICON', 'ic_chat_notification')
FIREBASE_DEFAULT_COLOR = os.environ.get('FIREBASE_DEFAULT_COLOR', '#075E54')
FIREBASE_DEFAULT_CHANNEL_ID = os.environ.get('FIREBASE_DEFAULT_CHANNEL_ID', 'chat_messages')
FIREBASE_DEFAULT_SOUND = os.environ.get('FIREBASE_DEFAULT_SOUND', 'default')

# Payment Gateway Configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY', '')

# Redis Configuration
# In production, set REDIS_URL in your environment variables
# Example: rediss://default:password@host:port
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')  # Default for local dev

# Celery settings
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/1"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = 'default'

# Redis specific settings
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'ssl_cert_reqs': 'CERT_NONE',  # For self-signed certs
    'retry_on_timeout': True,
    'socket_keepalive': True,
    'socket_timeout': 30,
    'socket_connect_timeout': 30,
}

CELERY_TASK_ROUTES = {
    "estateApp.tasks.dispatch_notification_batch": {"queue": "notifications"},
    "estateApp.tasks.dispatch_notification_stream": {"queue": "notifications"},
}

# Worker settings
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 30
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_DISABLE_RATE_LIMITS = True

