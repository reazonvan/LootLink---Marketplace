"""
Настройки для запуска pytest.

Использование:
    DJANGO_SETTINGS_MODULE=config.settings.test

Особенности:
- DEBUG=False (тесты не должны зависеть от debug-режима)
- Быстрый password hasher (MD5) — ускоряет создание пользователей в фикстурах
- In-memory кэш (без Redis)
- Eager Celery (синхронное выполнение задач, без брокера)
- Минимум логирования в файлы
- SQLite по умолчанию (быстрее PostgreSQL для тестов)
"""

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, config

DEBUG = False

# Самый быстрый hasher для тестов (НЕ использовать в проде!)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory cache — изолирует тесты друг от друга
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Celery: синхронное выполнение, без брокера
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# SQLite в файле для тестов (быстрее, чем PostgreSQL)
# pytest-django по умолчанию использует --reuse-db для ускорения повторных запусков.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": config("TEST_SQLITE_PATH", default=str(BASE_DIR / "db.test.sqlite3")),
    }
}

# Email — locmem backend, чтобы проверять mail.outbox в тестах
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Cookies без secure-флага (тесты на HTTP)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None

# Минимум логирования в файлы — pytest и так выводит всё в stdout
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "WARNING",
    },
}

# Channels: in-memory layer для тестов WebSocket (без Redis)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ═══════════════════════════════════════════════════════════════
# P0-фиксы безопасности — отключаем для тестов (тесты проверяют
# бизнес-логику, не финансовую модель платформы).
# ═══════════════════════════════════════════════════════════════

# Без комиссии в тестах — старые тесты ожидают 100% продавцу.
# Конкретные тесты комиссии — отдельной фикстурой override_settings.
PLATFORM_COMMISSION_PERCENT = "0"

# Без HMAC-проверки webhook — для тестов webhook view с mock-сервисом.
# Тесты HMAC сами включают переменную через override_settings.
YOOKASSA_WEBHOOK_SECRET = ""

# Никаких proxy в тестах
TRUSTED_PROXIES = ["127.0.0.1", "::1"]
