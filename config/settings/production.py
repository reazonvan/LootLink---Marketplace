"""
Настройки для продакшна.

Использование:
    DJANGO_SETTINGS_MODULE=config.settings.production

Особенности:
- DEBUG=False (форсирован)
- Sentry для мониторинга ошибок
- Принудительный HTTPS (HSTS, secure cookies)
- Защита от прокси-спуфинга через X-Forwarded-Proto
- Предупреждение, если USE_REDIS=False (rate-limit/channels работают per-worker)
"""

import warnings

from django.core.exceptions import ImproperlyConfigured as _ImpConfig

from .base import *  # noqa: F401, F403
from .base import config

# В проде DEBUG всегда False, никаких .env-овверайдов
DEBUG = False

# Sentry для мониторинга ошибок
_SENTRY_DSN = config("SENTRY_DSN", default="")
if _SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% трейсов достаточно для мониторинга
        send_default_pii=False,  # Не отправлять персональные данные
        environment=config("ENVIRONMENT", default="production"),
        release=config("RELEASE_VERSION", default="1.0.0"),
    )

# Защита от прокси-спуфинга — Caddy/nginx должен задавать X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# SSL/HTTPS настройки
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)

# HSTS включаем только когда SSL активен
if SECURE_SSL_REDIRECT:
    SECURE_HSTS_SECONDS = 31536000  # 1 год
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Базовая безопасность
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Предупреждение, если в проде Redis отключён
if not config("USE_REDIS", default=False, cast=bool):
    warnings.warn(
        "USE_REDIS=False in production: rate-limit и channels работают локально "
        "(per-worker), что некорректно при множественных Daphne workers. "
        "Установите USE_REDIS=True в production .env",
        RuntimeWarning,
    )

# P2-17: в продакшне ADMIN_URL должен быть непредсказуемым
if config("ADMIN_URL", default="admin/") == "admin/":
    raise _ImpConfig(
        "В production ADMIN_URL='admin/' запрещён. Задайте непредсказуемый путь "
        "в .env (например, 'a8sd9-mgmt-7zx2/')."
    )

# P0-4 (CRITICAL): без ключа шифрования Withdrawal.payment_details будут
# писаться в открытом виде → PCI-DSS нарушение. В prod падаем сразу.
if not config("PAYMENT_DETAILS_KEY", default=""):
    raise _ImpConfig(
        "PAYMENT_DETAILS_KEY обязателен в production. Сгенерируйте Fernet-ключ: "
        'python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())" — и пропишите в .env.'
    )

# P2-12 (CRITICAL): без TRUSTED_PROXIES атакующий подделывает X-Forwarded-For
# и обходит rate-limit, брутфорс-защиту и IP-whitelist YooKassa webhook.
if not config("TRUSTED_PROXIES", default=""):
    raise _ImpConfig(
        "TRUSTED_PROXIES обязателен в production (IP/CIDR через запятую). "
        "Например: TRUSTED_PROXIES=127.0.0.1,::1 для Caddy на том же хосте."
    )

# P0-3 (CRITICAL): без HMAC-секрета YooKassa webhook принимает любой payload.
# В сочетании с подменой XFF — полный обход проверки источника.
if not config("YOOKASSA_WEBHOOK_SECRET", default=""):
    raise _ImpConfig(
        "YOOKASSA_WEBHOOK_SECRET обязателен в production. Задайте секрет "
        "в личном кабинете YooKassa и в .env."
    )
