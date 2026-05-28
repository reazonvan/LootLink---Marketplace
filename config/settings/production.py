"""Настройки для продакшна.

Использование:
    DJANGO_SETTINGS_MODULE=config.settings.production

Особенности:
- DEBUG=False (форсирован)
- Sentry для мониторинга ошибок
- Принудительный HTTPS (HSTS, secure cookies)
- Защита от прокси-спуфинга через X-Forwarded-Proto
- fail-fast при отсутствии PAYMENT_DETAILS_KEY/TRUSTED_PROXIES
"""

import warnings

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
from django.core.exceptions import ImproperlyConfigured as _ImpConfig  # noqa: E402

if config("ADMIN_URL", default="admin/") == "admin/":
    raise _ImpConfig(
        "В production ADMIN_URL='admin/' запрещён. Задайте непредсказуемый путь "
        "в .env (например, 'a8sd9-mgmt-7zx2/')."
    )

# P0-4: отсутствие ключа шифрования payment_details — fail-fast.
# Withdrawal.payment_details без Fernet — PCI-DSS нарушение,
# запуск с пустым ключом недопустим.
if not config("PAYMENT_DETAILS_KEY", default=""):
    raise _ImpConfig(
        "PAYMENT_DETAILS_KEY не задан в production. Без Fernet-ключа "
        "Withdrawal.payment_details будет храниться в открытом виде "
        "(нарушение PCI-DSS). Сгенерировать: "
        'python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"'
    )

# P2-12: в production TRUSTED_PROXIES обязателен (иначе XFF-спуфинг → обход rate-limit).
if not config("TRUSTED_PROXIES", default=""):
    raise _ImpConfig(
        "TRUSTED_PROXIES не задан в production. Без него get_client_ip "
        "доверяет любому X-Forwarded-For, что позволяет атакующему "
        "обойти rate-limit и брутфорс-защиту. Задайте IP/CIDR "
        "реверс-прокси через запятую (например 172.16.0.0/12)."
    )

# Опционально: предупреждение если USE_REDIS=False
# (warning, не raise — в edge-cases dev/test может быть полезно).
