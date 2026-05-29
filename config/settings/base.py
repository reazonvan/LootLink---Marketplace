"""
Базовые настройки Django для LootLink.

Этот файл содержит общие настройки, которые применяются во всех окружениях
(development, production, test). Окружение-специфичные значения переопределяются
в соответствующих модулях:
- development.py — для локальной разработки (DEBUG, SQLite, console email)
- production.py  — для продакшна (Sentry, secure cookies, HSTS)
- test.py        — для pytest (fast hashers, in-memory cache, eager Celery)
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from decouple import config

# Build paths inside the project
# settings/base.py → config/settings/base.py → корень проекта = parent.parent.parent
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY ОБЯЗАТЕЛЬНО должен быть в .env файле! Без default для безопасности.
try:
    SECRET_KEY = config("SECRET_KEY")
except Exception:
    raise ImproperlyConfigured(
        "SECRET_KEY not found in environment variables! "
        "Add SECRET_KEY=your-secret-key-here to your .env file. "
        'Generate one using: python -c "from django.core.management.utils '
        'import get_random_secret_key; print(get_random_secret_key())"'
    )

# DEBUG переопределяется в development/production/test
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="lootlink.ru,www.lootlink.ru,127.0.0.1,localhost"
).split(",")

# CSRF Trusted Origins для HTTPS
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="https://lootlink.ru,https://www.lootlink.ru"
).split(",")

# Application definition
INSTALLED_APPS = [
    "daphne",  # Должен быть первым для ASGI
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",  # Для SEO sitemap
    "django.contrib.postgres",  # Для SearchVectorField
    # Third party apps
    "channels",
    "crispy_forms",
    "crispy_bootstrap5",
    "storages",
    "rest_framework",
    "django_filters",
    "django_celery_beat",
    "django_otp",
    "django_otp.plugins.otp_totp",
    # Local apps
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "listings.apps.ListingsConfig",
    "transactions.apps.TransactionsConfig",
    "chat.apps.ChatConfig",
    "payments.apps.PaymentsConfig",
    "api.apps.ApiConfig",
    "admin_panel.apps.AdminPanelConfig",  # Кастомная админ-панель
]

# django-otp (2FA)
OTP_TOTP_ISSUER = "LootLink"

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # Rate Limiting (Throttling) для защиты от DDoS и злоупотреблений
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",  # Анонимные пользователи: 100 запросов в час
        "user": "1000/hour",  # Аутентифицированные: 1000 запросов в час
        "burst": "60/minute",  # Burst лимит: 60 запросов в минуту
        "create": "20/hour",  # Создание объектов: 20 в час
        "modify": "100/hour",  # Модификация: 100 в час
    },
}

MIDDLEWARE = [
    # Request ID первым — чтобы все последующие логи подхватили идентификатор
    "core.middleware_logging.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # GZipMiddleware убран: Caddy уже сжимает (encode zstd gzip),
    # а GZip + HTTPS = уязвимость BREACH
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Кастомные middleware для безопасности
    "core.middleware.SimpleRateLimitMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "core.middleware_audit.BruteForceProtectionMiddleware",  # Защита от брутфорса
    "core.middleware_audit.SecurityAuditMiddleware",  # Аудит безопасности
    # Обновление last_seen
    "core.middleware_activity.UpdateLastSeenMiddleware",
    # Админ-панель
    "admin_panel.middleware.AdminPanelContextMiddleware",  # Счетчики для sidebar
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                "core.context_processors.notifications_processor",
                "core.context_processors.wallet_balance_processor",
                "core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Channels configuration
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://localhost:6379/2")],
        },
    },
}

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DB_ENGINE = config("DB_ENGINE", default="postgresql")

if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": config("SQLITE_PATH", default=str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="lootlink_db"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD"),  # Для PostgreSQL пароль обязателен.
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            # Daphne (ASGI) — каждый запрос в отдельном потоке,
            # CONN_MAX_AGE=0 закрывает соединение после запроса, предотвращая утечку.
            # Persistent connections: меньше latency на каждом запросе.
            # CONN_HEALTH_CHECKS защищает от зависших соединений.
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=600, cast=int),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "client_encoding": "UTF8",
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000",
            },
        }
    }

# Кастомный путь для стандартной Django-админки (защита от ботов).
# В production задаётся через .env, в dev по умолчанию остаётся 'admin/'.
ADMIN_URL = config("ADMIN_URL", default="admin/")

# Custom User Model
AUTH_USER_MODEL = "accounts.CustomUser"

# Authentication Backends (case-insensitive username)
AUTHENTICATION_BACKENDS = [
    "accounts.backends.CaseInsensitiveModelBackend",  # Кастомный backend для case-insensitive логина
    "django.contrib.auth.backends.ModelBackend",  # Fallback на стандартный
]

# Password hashers — Argon2id первым (быстрее и безопаснее PBKDF2),
# fallback на старые алгоритмы для совместимости со старыми хешами в БД.
# Argon2id — победитель Password Hashing Competition (PHC) 2015,
# рекомендован OWASP. Соответствует требованию диплома 1.3.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ManifestStaticFilesStorage добавляет content-hash в имена файлов
# (style.abc123.css) и пишет staticfiles.json — это даёт корректный
# cache-busting при долгом max-age=2592000 в Caddyfile. Без него после
# deploy юзер видит старый CSS/JS до истечения TTL.
# Локально (DEBUG=True) используем встроенный bypass, чтобы не пересобирать
# manifest на каждый чих.
STORAGES = {
    "default": {
        "BACKEND": (
            "storages.backends.s3boto3.S3Boto3Storage"
            if config("USE_S3", default=False, cast=bool)
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
        ),
    },
}

# Media files configuration
USE_S3 = config("USE_S3", default=False, cast=bool)

if USE_S3:
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_DEFAULT_ACL = "public-read"
    AWS_LOCATION = "media"

    # S3 Media settings
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/"
else:
    # Local media settings
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout redirects
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "listings:catalog"
LOGOUT_REDIRECT_URL = "listings:home"

# Listings
MAX_ACTIVE_LISTINGS = config("MAX_ACTIVE_LISTINGS", default=50, cast=int)

# Messages framework
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

# Email configuration
# Production: Yandex SMTP (smtp.yandex.ru:465, SSL)
# В .env задайте EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.yandex.ru")
EMAIL_PORT = config("EMAIL_PORT", default=465, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@lootlink.ru")

# Email timeout settings
EMAIL_TIMEOUT = 10  # секунд

# SMS Settings (SMS.ru для отправки СМС в России)
SMS_ENABLED = config("SMS_ENABLED", default=False, cast=bool)
SMS_RU_API_KEY = config("SMS_RU_API_KEY", default="")

# Telegram Bot
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")

# Web Push Notifications
VAPID_PUBLIC_KEY = config("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = config("VAPID_PRIVATE_KEY", default="")

# Session and Cookie security (общие настройки, secure_* переопределяются в окружениях)
SESSION_COOKIE_HTTPONLY = True
# CSRF cookie HttpOnly — защита от XSS-кражи. WebSocket-клиент использует
# CSRF из мета-тега <meta name="csrf-token"> или X-CSRFToken header,
# поэтому JS-доступ к самой cookie не нужен.
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 1209600  # 2 недели
SESSION_COOKIE_NAME = "lootlink_sessionid"
CSRF_COOKIE_NAME = "lootlink_csrftoken"
# В проде задаем домен куки для общего входа между apex/www.
SESSION_COOKIE_DOMAIN = (
    config("SESSION_COOKIE_DOMAIN", default=".lootlink.ru" if not DEBUG else "") or None
)
CSRF_COOKIE_DOMAIN = (
    config("CSRF_COOKIE_DOMAIN", default=".lootlink.ru" if not DEBUG else "") or None
)

# Cache configuration
# В production Redis обязателен (rate-limit, sessions, channels).
# В dev — LocMemCache достаточно. См. .env / .env.example.
USE_REDIS = config("USE_REDIS", default=False, cast=bool)

if USE_REDIS:
    # Redis для production
    REDIS_URL = config("REDIS_URL", default="redis://redis:6379/1")

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "retry_on_timeout": True,
                },
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                "IGNORE_EXCEPTIONS": True,  # Не падать если Redis недоступен
            },
            "KEY_PREFIX": "lootlink",
            "TIMEOUT": 300,  # 5 минут по умолчанию
        }
    }

    # Session: cached_db — read через Redis (быстро), write через БД (надёжно).
    # Под нагрузкой dbb-only бэкенд делает UPDATE django_session на каждый
    # запрос → лок на одну строку на пользователя → bottleneck.
    # cached_db даёт O(1) lookup из Redis, fallback на БД при cache miss.
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
    SESSION_CACHE_ALIAS = "default"
else:
    # Локальный кеш для разработки
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
            "OPTIONS": {"MAX_ENTRIES": 10000},
        }
    }

# File upload settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
# Защита от DoS через хеш-коллизии в формах (1000+ полей).
# https://docs.djangoproject.com/en/5.2/ref/settings/#data-upload-max-number-fields
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Pagination settings
PAGINATION_ITEMS_PER_PAGE = {
    "listings": 12,
    "reviews": 10,
    "conversations": 20,
    "messages": 50,
    "notifications": 20,
    "purchases": 20,
    "sales": 20,
}

# Celery Configuration
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 минут максимум на задачу

# Периодические задачи Celery Beat
CELERY_BEAT_SCHEDULE = {
    "cleanup-old-data-daily": {
        "task": "core.tasks.cleanup_old_data",
        "schedule": 86400.0,  # Раз в день (24 часа)
    },
    "update-user-ratings-hourly": {
        "task": "core.tasks.update_user_ratings",
        "schedule": 3600.0,  # Раз в час
    },
    "cleanup-audit-logs-weekly": {
        "task": "core.tasks.cleanup_security_audit_logs",
        "schedule": 604800.0,  # Раз в неделю (7 дней)
        "kwargs": {"days": 90},  # Удаляем логи старше 90 дней
    },
    "cleanup-login-attempts-daily": {
        "task": "core.tasks.cleanup_login_attempts",
        "schedule": 86400.0,  # Раз в день
        "kwargs": {"days": 30},  # Удаляем попытки старше 30 дней
    },
    # Автоматическое освобождение escrow
    "auto-release-escrow-hourly": {
        "task": "payments.auto_release_escrow",
        "schedule": 3600.0,  # Раз в час
    },
    # Проверка pending withdrawals
    "check-pending-withdrawals-daily": {
        "task": "payments.check_pending_withdrawals",
        "schedule": 86400.0,  # Раз в день
    },
    # Прогрев кэша каталога (TTL контекста = 10 мин, перепрогрев каждые 4 мин)
    "warm-catalog-cache": {
        "task": "listings.tasks.warm_catalog_cache",
        "schedule": 240.0,
    },
}

# ЮKassa settings
YOOKASSA_SHOP_ID = config("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = config("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_WEBHOOK_ALLOWED_IPS = config("YOOKASSA_WEBHOOK_ALLOWED_IPS", default="")
SITE_URL = config("SITE_URL", default="https://lootlink.ru")

# Комиссия платформы (P0-11): процент от суммы сделки, удерживается с продавца
# при release_to_seller. Например, 5 = 5%.
PLATFORM_COMMISSION_PERCENT = config("PLATFORM_COMMISSION_PERCENT", default="0", cast=str)

# Ключ Fernet для шифрования Withdrawal.payment_details (P0-4 PCI-DSS).
# Сгенерировать: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# В production задаётся в .env (никогда не коммитить!).
PAYMENT_DETAILS_KEY = config("PAYMENT_DETAILS_KEY", default="")

# HMAC-секрет для верификации webhook YooKassa (P0-3).
# YooKassa подписывает webhook'и; задайте секрет в личном кабинете и здесь.
YOOKASSA_WEBHOOK_SECRET = config("YOOKASSA_WEBHOOK_SECRET", default="")

# Доверенные IP/CIDR для X-Forwarded-For доверия (P0-14).
# Caddy/nginx обычно ставит правильный XFF; если запрос пришёл напрямую,
# не доверяем XFF. Пустой список = доверять любому XFF (НЕ для prod).
TRUSTED_PROXIES = [
    ip.strip() for ip in config("TRUSTED_PROXIES", default="127.0.0.1,::1").split(",") if ip.strip()
]

# Публичные контакты и соцсети — рендерятся в footer и страницах
# поддержки. Пустые значения скрывают соответствующие ссылки в шаблоне.
SUPPORT_EMAIL = config("SUPPORT_EMAIL", default="support@lootlink.ru")
SOCIAL_DISCORD_URL = config("SOCIAL_DISCORD_URL", default="")
SOCIAL_TELEGRAM_URL = config("SOCIAL_TELEGRAM_URL", default="")
SOCIAL_VK_URL = config("SOCIAL_VK_URL", default="")

# Юридические реквизиты для /requisites/. Пока не заполнены —
# страница покажет дружелюбное предупреждение «реквизиты оформляются».
# Заполнить ПЕРЕД подключением реальных платежей и публичным запуском.
LEGAL_NAME = config("LEGAL_NAME", default="")
LEGAL_INN = config("LEGAL_INN", default="")
LEGAL_OGRN = config("LEGAL_OGRN", default="")  # ОГРН для ООО, ОГРНИП для ИП
LEGAL_OGRN_LABEL = config("LEGAL_OGRN_LABEL", default="ОГРН")
LEGAL_ADDRESS = config("LEGAL_ADDRESS", default="")
LEGAL_BANK_NAME = config("LEGAL_BANK_NAME", default="")
LEGAL_BANK_BIC = config("LEGAL_BANK_BIC", default="")
LEGAL_BANK_ACCOUNT = config("LEGAL_BANK_ACCOUNT", default="")
LEGAL_BANK_CORR = config("LEGAL_BANK_CORR", default="")

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} [{request_id}] {module} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "request_id": {
            "()": "core.middleware_logging.RequestIDFilter",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        # stdout с verbose-форматом — для docker logs / loki / cloudwatch.
        # Тот же formatter что у файловых, но без request_id-фильтра, чтобы
        # фоновые задачи и management-команды (без request scope) тоже шли в stdout.
        "stdout_verbose": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "lootlink.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "errors.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "security_file": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "security.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "listings": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "transactions": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "chat": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "INFO",
    },
}
