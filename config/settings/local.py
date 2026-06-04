"""
Локальный полнофункциональный режим разработки.

Запуск:
    DJANGO_SETTINGS_MODULE=config.settings.local DJANGO_ENV=local \
    DB_ENGINE=postgresql DB_HOST=localhost manage.py runserver 0.0.0.0:8000

Отличия от development.py (который заточен под SQLite-lite):
- Работает на PostgreSQL (нет холодных залипаний записи, как на SQLite/Windows).
- daphne НЕ убирается → runserver поднимается как ASGI → живой WebSocket-чат.
- Channels: in-memory достаточно для одного dev-процесса (Redis не обязателен).
- DEBUG, без secure-cookie/HSTS, email в консоль, быстрый MD5-хешер.
"""

import os as _os

from .base import *  # noqa: F401, F403
from .base import config

# Защита от случайного запуска в проде.
assert _os.environ.get("DJANGO_ENV", "local").lower() in ("dev", "development", "local"), (
    "config.settings.local — только для локалки. Для прода используйте "
    "config.settings.production."
)

DEBUG = True
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0").split(",")

# Локальный HTTP — никаких secure-флагов и редиректов на HTTPS.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
).split(",")

# Существующие dev-аккаунты захешированы MD5 — оставляем этот хешер,
# иначе они не залогинятся.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Письма в консоль (не слать реальные, даже если .env=SMTP).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Статика без manifest: cache-busting в dev не нужен, а ManifestStaticFilesStorage
# заставил бы {% static %} читать staticfiles.json, которого локально нет.
STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ASGI: base.py держит daphne первым в INSTALLED_APPS → manage.py runserver
# работает как ASGI-сервер (Daphne) и обслуживает WebSocket (/ws/chat/...).
# In-memory channel layer хватает для одного процесса dev-сервера.
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# Celery синхронно, без брокера/воркера.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Тяжёлые security-middleware пишут в БД на каждый запрос — в dev не нужны.
MIDDLEWARE = [
    m
    for m in MIDDLEWARE  # noqa: F405
    if m
    not in (
        "core.middleware_audit.BruteForceProtectionMiddleware",
        "core.middleware_audit.SecurityAuditMiddleware",
    )
]

# Приводим OPTIONS под конкретный движок БД.
_opts = DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
if "sqlite" in DATABASES["default"]["ENGINE"]:  # noqa: F405
    # Запасной путь, если кто-то запустит local на sqlite.
    _opts["timeout"] = 30
    _opts["transaction_mode"] = "IMMEDIATE"
    _opts["init_command"] = "PRAGMA synchronous=NORMAL"
else:
    # PostgreSQL: убрать sqlite-only ключи, если просочились.
    for _k in ("timeout", "transaction_mode", "init_command"):
        _opts.pop(_k, None)
