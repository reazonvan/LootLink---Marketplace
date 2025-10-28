"""
Декораторы для views.
"""
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
import time


def api_rate_limit(max_requests: int = 60, time_window: int = 60):
    """
    Декоратор для ограничения количества запросов к API endpoints.
    
    Args:
        max_requests: Максимальное количество запросов
        time_window: Временное окно в секундах
    
    Usage:
        @api_rate_limit(max_requests=30, time_window=60)
        def my_api_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Получаем IP адрес
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Ключ для кеша
            cache_key = f'api_rate_limit:{view_func.__name__}:{ip}'
            
            # Получаем историю запросов
            requests_history = cache.get(cache_key, [])
            now = time.time()
            
            # Удаляем старые запросы
            requests_history = [t for t in requests_history if now - t < time_window]
            
            # Проверяем лимит
            if len(requests_history) >= max_requests:
                return JsonResponse({
                    'error': 'Слишком много запросов. Попробуйте позже.',
                    'retry_after': int(time_window - (now - requests_history[0]))
                }, status=429)
            
            # Добавляем новый запрос
            requests_history.append(now)
            cache.set(cache_key, requests_history, time_window)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def ajax_required(view_func):
    """
    Декоратор для проверки что запрос - AJAX.
    Возвращает 400 для не-AJAX запросов.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'Требуется AJAX запрос'
            }, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper

