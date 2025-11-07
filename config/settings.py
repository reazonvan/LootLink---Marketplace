"""
Django settings for LootLink project.
"""
import os
from pathlib import Path
from decouple import config
from django.core.exceptions import ImproperlyConfigured

# Sentry для мониторинга ошибок (только в production)
if not config('DEBUG', default=False, cast=bool):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=config('SENTRY_DSN', default=''),
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
        environment=config('ENVIRONMENT', default='production'),
        release=config('RELEASE_VERSION', default='1.0.0'),
    )

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY ОБЯЗАТЕЛЬНО должен быть в .env файле! Без default для безопасности
try:
    SECRET_KEY = config('SECRET_KEY')
except Exception:
    raise ImproperlyConfigured(
        'SECRET_KEY not found in environment variables! '
        'Add SECRET_KEY=your-secret-key-here to your .env file. '
        'Generate one using: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,91.218.245.178').split(',')

# CSRF Trusted Origins для HTTPS
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://91.218.245.178,https://91.218.245.178'
).split(',')

# Application definition
INSTALLED_APPS = [
    'daphne',  # Должен быть первым для ASGI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',  # Для SEO sitemap
    
    # Third party apps
    'channels',
    'crispy_forms',
    'crispy_bootstrap5',
    'storages',
    'rest_framework',
    'django_filters',
    'django_otp',
    'django_otp.plugins.otp_totp',
    
    # Local apps
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'listings.apps.ListingsConfig',
    'transactions.apps.TransactionsConfig',
    'chat.apps.ChatConfig',
    'payments.apps.PaymentsConfig',
    'api.apps.ApiConfig',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Rate Limiting (Throttling) для защиты от DDoS и злоупотреблений
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # Анонимные пользователи: 100 запросов в час
        'user': '1000/hour',  # Аутентифицированные: 1000 запросов в час
        'burst': '60/minute',  # Burst лимит: 60 запросов в минуту
        'create': '20/hour',  # Создание объектов: 20 в час
        'modify': '100/hour',  # Модификация: 100 в час
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Сжатие ответов
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Кастомные middleware для безопасности
    'core.middleware.SimpleRateLimitMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'core.middleware_audit.BruteForceProtectionMiddleware',  # Защита от брутфорса
    'core.middleware_audit.SecurityAuditMiddleware',  # Аудит безопасности
    # Обновление last_seen
    'core.middleware_activity.UpdateLastSeenMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.notifications_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://localhost:6379/2')],
        },
    },
}

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='lootlink_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),  # Пароль ОБЯЗАТЕЛЬНО должен быть в .env файле!
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        # Connection Pooling - переиспользование подключений
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),  # 10 минут
        'OPTIONS': {
            'client_encoding': 'UTF8',
            # Дополнительные оптимизации PostgreSQL
            'connect_timeout': 10,  # Таймаут подключения 10 секунд
            'options': '-c statement_timeout=30000'  # Таймаут запроса 30 секунд
        },
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Authentication Backends (case-insensitive username)
AUTHENTICATION_BACKENDS = [
    'accounts.backends.CaseInsensitiveModelBackend',  # Кастомный backend для case-insensitive логина
    'django.contrib.auth.backends.ModelBackend',  # Fallback на стандартный
]

# Password validation
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
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files configuration
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_DEFAULT_ACL = 'public-read'
    AWS_LOCATION = 'media'
    
    # S3 Media settings
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
else:
    # Local media settings
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout redirects
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'listings:catalog'
LOGOUT_REDIRECT_URL = 'listings:home'

# Messages framework
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# Email configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@lootlink.com')

# SMS Settings (SMS.ru для отправки СМС в России)
SMS_ENABLED = config('SMS_ENABLED', default=False, cast=bool)
SMS_RU_API_KEY = config('SMS_RU_API_KEY', default='')

# Security settings for production
if not DEBUG:
    # SSL/HTTPS настройки (можно отключить через .env если нет сертификата)
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
    
    # HSTS настройки (включать только когда есть SSL)
    if SECURE_SSL_REDIRECT:
        SECURE_HSTS_SECONDS = 31536000  # 1 год
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Базовая безопасность (всегда включено)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# Session and Cookie security
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1209600  # 2 недели

# Cache configuration
USE_REDIS = config('USE_REDIS', default=False, cast=bool)

if USE_REDIS:
    # Redis для production
    REDIS_URL = config('REDIS_URL', default='redis://redis:6379/1')
    
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True,
                },
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                'IGNORE_EXCEPTIONS': True,  # Не падать если Redis недоступен
            },
            'KEY_PREFIX': 'lootlink',
            'TIMEOUT': 300,  # 5 минут по умолчанию
        }
    }
    
    # Session хранение в Redis для production
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Локальный кеш для разработки
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'OPTIONS': {
                'MAX_ENTRIES': 10000
            }
        }
    }

# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# Pagination settings
PAGINATION_ITEMS_PER_PAGE = {
    'listings': 12,
    'reviews': 10,
    'conversations': 20,
    'messages': 50,
    'notifications': 20,
    'purchases': 20,
    'sales': 20,
}

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 минут максимум на задачу

# Периодические задачи Celery Beat
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-data-daily': {
        'task': 'core.tasks.cleanup_old_data',
        'schedule': 86400.0,  # Раз в день (24 часа)
    },
    'update-user-ratings-hourly': {
        'task': 'core.tasks.update_user_ratings',
        'schedule': 3600.0,  # Раз в час
    },
    'cleanup-audit-logs-weekly': {
        'task': 'core.tasks.cleanup_security_audit_logs',
        'schedule': 604800.0,  # Раз в неделю (7 дней)
        'kwargs': {'days': 90}  # Удаляем логи старше 90 дней
    },
    'cleanup-login-attempts-daily': {
        'task': 'core.tasks.cleanup_login_attempts',
        'schedule': 86400.0,  # Раз в день
        'kwargs': {'days': 30}  # Удаляем попытки старше 30 дней
    },
    # Автоматическое освобождение escrow
    'auto-release-escrow-hourly': {
        'task': 'payments.auto_release_escrow',
        'schedule': 3600.0,  # Раз в час
    },
    # Проверка pending withdrawals
    'check-pending-withdrawals-daily': {
        'task': 'payments.check_pending_withdrawals',
        'schedule': 86400.0,  # Раз в день
    },
}

# ЮKassa settings
YOOKASSA_SHOP_ID = config('YOOKASSA_SHOP_ID', default='')
YOOKASSA_SECRET_KEY = config('YOOKASSA_SECRET_KEY', default='')
SITE_URL = config('SITE_URL', default='http://91.218.245.178')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'lootlink.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'listings': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'transactions': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'chat': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
}

