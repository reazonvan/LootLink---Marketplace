"""
Настройки для локальной разработки.

Использование:
    DJANGO_SETTINGS_MODULE=config.settings.development

Особенности:
- DEBUG=True по умолчанию (можно отключить через .env)
- Без принудительной защиты cookie (HTTP, не HTTPS)
- Никаких принудительных secure-заголовков
- Sentry не подключается
- Email backend по умолчанию — console (см. .env)
"""

from .base import *  # noqa: F401, F403
from .base import config

# Включаем DEBUG по умолчанию для dev (может быть переопределено в .env)
DEBUG = config("DEBUG", default=True, cast=bool)

# В dev любые хосты — удобно при тестировании с разных устройств в локальной сети
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(",")

# Cookies без secure-флага (HTTP)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Локальный домен куки не используем — иначе ломается на 127.0.0.1
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None

# Быстрый хешер паролей для dev (production использует Argon2id/PBKDF2 1M итераций).
# Защита от случайного использования в prod — фиксируем явный env-маркер.
import os as _os

assert _os.environ.get("DJANGO_ENV", "dev").lower() in ("dev", "development", "local"), (
    "config.settings.development НЕЛЬЗЯ использовать в production. "
    "Установите DJANGO_ENV=development или используйте config.settings.production."
)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Отключаем Daphne в dev — используем стандартный WSGI runserver.
# Daphne (ASGI) убивает соединения по таймауту раньше, чем Django отвечает.
# WebSocket чат всё равно требует Redis, которого нет в dev.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "daphne"]

# SQLite не держит конкурентные записи — ставим таймаут ожидания блокировки.
# ВАЖНО: не затираем существующие OPTIONS (для postgres там client_encoding и пр.).
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"]["timeout"] = 30
# SQLite + WAL: дефолтные DEFERRED-транзакции под конкурентной нагрузкой
# (поллинг уведомлений/чата + записи сессии/last_login/LoginHistory при логине)
# застревают на upgrade read→write и дают многосекундные залипания (логин 5–15с).
# IMMEDIATE берёт write-lock сразу на BEGIN → чистое ожидание busy_timeout без
# стола. Ключ поддерживается Django 5.1+ и только для sqlite.
if "sqlite" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"]["OPTIONS"]["transaction_mode"] = "IMMEDIATE"
    # synchronous=NORMAL безопасен в WAL (теряется максимум последняя транзакция
    # при отключении питания, без повреждения БД) и убирает fsync на каждый
    # commit — именно он на Windows даёт многосекундные «холодные» записи.
    DATABASES["default"]["OPTIONS"]["init_command"] = "PRAGMA synchronous=NORMAL"

# Отключаем тяжёлые security-middleware, которые пишут в БД на каждый запрос.
# В dev они бесполезны и вызывают "database is locked" на SQLite.
MIDDLEWARE = [
    m
    for m in MIDDLEWARE
    if m
    not in (
        "core.middleware_audit.BruteForceProtectionMiddleware",
        "core.middleware_audit.SecurityAuditMiddleware",
    )
]

# Celery: выполняем задачи синхронно без Redis-брокера.
# Без этого .delay() пытается 20 раз подключиться к Redis → 20с зависания.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Channels: in-memory вместо Redis (WebSocket чат всё равно не работает без Redis).
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Доверенные origins для CSRF (proxy Windsurf browser preview)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://127.0.0.1:62732,http://localhost:62732",
).split(",")
