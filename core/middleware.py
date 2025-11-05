"""
Middleware для rate limiting и защиты от брутфорса.
"""
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.conf import settings
import time
import logging

# Логгер для безопасности
security_logger = logging.getLogger('django.security')


class SimpleRateLimitMiddleware:
    """
    Простое middleware для ограничения количества запросов.
    Защита от брутфорса на критичных эндпоинтах.
    """
    
    # Настройки rate limiting
    RATE_LIMITS = {
        # Аутентификация
        '/accounts/login/': (5, 300),  # 5 попыток за 5 минут
        '/accounts/register/': (3, 600),  # 3 попытки за 10 минут
        '/accounts/password-reset-request/': (3, 600),  # 3 попытки за 10 минут
        
        # Создание контента
        '/listing/create/': (10, 3600),  # 10 объявлений в час
        '/transactions/purchase-request/': (20, 3600),  # 20 запросов в час
        
        # Сообщения и уведомления
        '/chat/conversation/': (50, 60),  # 50 сообщений в минуту
        '/notifications/mark-read/': (100, 60),  # 100 запросов в минуту
        '/notifications/mark-all-read/': (5, 60),  # 5 запросов в минуту
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем POST запросы и определенные пути на rate limiting
        should_check = False
        
        # Проверяем POST запросы на защищенные эндпоинты
        if request.method == 'POST':
            for path in self.RATE_LIMITS:
                if request.path.startswith(path):
                    should_check = True
                    break
        
        if should_check:
            if not self._check_rate_limit(request):
                # Логируем подозрительную активность
                ip = self._get_client_ip(request)
                user = request.user if request.user.is_authenticated else 'Anonymous'
                security_logger.warning(
                    f'Rate limit exceeded: {request.path} | User: {user} | IP: {ip}'
                )
                return HttpResponseForbidden(
                    '❌ Слишком много попыток. Пожалуйста, подождите несколько минут.'
                )
        
        response = self.get_response(request)
        return response
    
    def _check_rate_limit(self, request):
        """Проверка лимита запросов."""
        # Получаем IP адрес
        ip = self._get_client_ip(request)
        
        # Получаем настройки для данного пути
        max_attempts, time_window = self.RATE_LIMITS.get(request.path, (10, 60))
        
        # Ключ для кеша
        cache_key = f'rate_limit:{request.path}:{ip}'
        
        # Получаем текущее количество попыток
        attempts = cache.get(cache_key, [])
        now = time.time()
        
        # Удаляем старые попытки (за пределами временного окна)
        attempts = [t for t in attempts if now - t < time_window]
        
        # Проверяем лимит
        if len(attempts) >= max_attempts:
            return False
        
        # Добавляем новую попытку
        attempts.append(now)
        cache.set(cache_key, attempts, time_window)
        
        return True
    
    def _get_client_ip(self, request):
        """Получение IP адреса клиента."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware для добавления заголовков безопасности.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Добавляем заголовки безопасности ВСЕГДА
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        # В production - строже, в development - разрешаем eval для отладки
        if not settings.DEBUG:
            # Production CSP - разрешаем Bootstrap и CDN
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' data: https: blob:; "
                "font-src 'self' https://cdn.jsdelivr.net data:; "
                "connect-src 'self' https://cdn.jsdelivr.net; "  # Добавлен CDN для загрузки ресурсов
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            # Development CSP - более мягкий для удобства разработки
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' data: https: blob: http:; "
                "font-src 'self' https://cdn.jsdelivr.net data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        
        return response

