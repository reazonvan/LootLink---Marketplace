"""
Middleware для rate limiting и защиты от брутфорса.
"""

import logging
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden

# Логгер для безопасности
security_logger = logging.getLogger("django.security")


class SimpleRateLimitMiddleware:
    """
    Простое middleware для ограничения количества запросов.
    Защита от брутфорса на критичных эндпоинтах.
    """

    # Настройки rate limiting
    RATE_LIMITS = {
        # Аутентификация
        "/accounts/login/": (5, 300),  # 5 попыток за 5 минут
        "/accounts/register/": (3, 600),  # 3 попытки за 10 минут
        "/accounts/password-reset/": (3, 600),  # 3 попытки за 10 минут
        # Создание контента
        "/listing/create/": (10, 3600),  # 10 объявлений в час
        "/transactions/purchase-request/": (20, 3600),  # 20 запросов в час
        # Сообщения и уведомления
        "/chat/conversation/": (50, 60),  # 50 сообщений в минуту
        "/notifications/mark-read/": (100, 60),  # 100 запросов в минуту
        "/notifications/mark-all-read/": (5, 60),  # 5 запросов в минуту
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем POST запросы и определенные пути на rate limiting
        should_check = False

        # Проверяем POST запросы на защищенные эндпоинты
        if request.method == "POST":
            for path in self.RATE_LIMITS:
                if request.path.startswith(path):
                    should_check = True
                    break

        if should_check:
            if not self._check_rate_limit(request):
                # Логируем подозрительную активность.
                # request.user может отсутствовать если AuthenticationMiddleware
                # не выполнился (например, в unit-тестах с голым RequestFactory).
                ip = self._get_client_ip(request)
                request_user = getattr(request, "user", None)
                if request_user is not None and request_user.is_authenticated:
                    user_repr = request_user
                else:
                    user_repr = "Anonymous"
                security_logger.warning(
                    f"Rate limit exceeded: {request.path} | User: {user_repr} | IP: {ip}"
                )
                return HttpResponseForbidden(
                    "Слишком много попыток. Пожалуйста, подождите несколько минут."
                )

        response = self.get_response(request)
        return response

    def _check_rate_limit(self, request):
        """Атомарная проверка лимита запросов через cache.incr.

        cache.incr — атомарная операция в Redis, что закрывает race condition
        (несколько параллельных запросов больше не могут все пройти лимит).
        """
        ip = self._get_client_ip(request)

        # Точное соответствие пути → точный лимит. Иначе — startswith.
        if request.path in self.RATE_LIMITS:
            max_attempts, time_window = self.RATE_LIMITS[request.path]
        else:
            for prefix, limits in self.RATE_LIMITS.items():
                if request.path.startswith(prefix):
                    max_attempts, time_window = limits
                    break
            else:
                max_attempts, time_window = (10, 60)

        # Используем разные buckets per time-window для fixed-window лимита.
        cache_key = f"rate_limit:{request.path}:{ip}"

        try:
            current = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, time_window)
            current = 1

        return current <= max_attempts

    @staticmethod
    def _get_client_ip(request):
        from core.utils import get_client_ip

        return get_client_ip(request)


class SecurityHeadersMiddleware:
    """
    Middleware для добавления заголовков безопасности.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # CSP-nonce генерируем ДО get_response, чтобы шаблоны успели подставить
        # его в инлайн-<script nonce="{{ request.csp_nonce }}">.
        request.csp_nonce = secrets.token_urlsafe(16)

        response = self.get_response(request)

        # Заголовки безопасности.
        # X-XSS-Protection УДАЛЁН: deprecated в современных браузерах,
        # фактически может включать уязвимости в IE/старом Safari
        # (https://owasp.org/www-project-secure-headers/#x-xss-protection).
        # Защита от XSS — через CSP ниже + escape в шаблонах.
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy.
        # В dev мягче (http:, unsafe-eval для отладки), в prod — строже.
        if settings.DEBUG:
            img_src = "img-src 'self' data: https: blob: http:; "
            connect_src = "connect-src 'self'; "
            enforce_script_extra = " 'unsafe-eval'"
        else:
            img_src = "img-src 'self' data: https: blob:; "
            connect_src = "connect-src 'self' wss://lootlink.ru https://cdn.jsdelivr.net; "
            enforce_script_extra = ""

        common = (
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
            + img_src
            + "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com data:; "
            + connect_src
            + "frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        )

        # Enforcing: 'unsafe-inline' для script сохранён — в шаблонах ещё
        # остаются инлайн-обработчики (onclick=/onchange=...), которые nonce не
        # покрывает. ВАЖНО: nonce-source в enforcing НЕ добавляем, иначе браузер
        # проигнорирует 'unsafe-inline' и обработчики сломаются.
        response["Content-Security-Policy"] = (
            f"script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'{enforce_script_extra}; "
            + common
        )

        # Report-Only: строгая политика без script 'unsafe-inline' (только nonce).
        # Ничего не блокирует — лишь репортит оставшиеся нарушения (инлайн
        # on*=-обработчики), чтобы их вычистить и затем перенести strict-политику
        # в enforcing (убрав 'unsafe-inline').
        response["Content-Security-Policy-Report-Only"] = (
            f"script-src 'self' https://cdn.jsdelivr.net 'nonce-{request.csp_nonce}'; " + common
        )

        return response
