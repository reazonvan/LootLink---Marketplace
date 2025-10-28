"""
Утилиты для core приложения.
"""
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import QuerySet
from typing import Optional


def paginate_queryset(queryset: QuerySet, request, per_page: int = 20):
    """
    Универсальная функция пагинации.
    
    Args:
        queryset: Django QuerySet для пагинации
        request: HTTP request объект
        per_page: Количество элементов на странице
    
    Returns:
        Page object с пагинированными данными
    
    Example:
        page_obj = paginate_queryset(listings, request, per_page=12)
    """
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # Если номер страницы не целое число, вернуть первую страницу
        page_obj = paginator.page(1)
    except EmptyPage:
        # Если страница вне диапазона, вернуть последнюю
        page_obj = paginator.page(paginator.num_pages)
    
    return page_obj


def get_cached_or_set(cache_key: str, callable_func, timeout: int = 300):
    """
    Получить данные из кеша или вычислить и закешировать.
    
    Args:
        cache_key: Ключ для кеша
        callable_func: Функция для вычисления значения
        timeout: Время жизни в кеше (секунды)
    
    Returns:
        Закешированное или свежевычисленное значение
    
    Example:
        stats = get_cached_or_set(
            'homepage_stats',
            lambda: calculate_stats(),
            timeout=300
        )
    """
    result = cache.get(cache_key)
    
    if result is None:
        result = callable_func()
        cache.set(cache_key, result, timeout)
    
    return result


def invalidate_cache_pattern(pattern: str):
    """
    Инвалидировать все ключи кеша по паттерну.
    
    Args:
        pattern: Паттерн для поиска ключей (например, 'user_profile_*')
    
    Example:
        invalidate_cache_pattern('user_profile_*')
    """
    try:
        # Работает только с django-redis
        from django_redis import get_redis_connection
        
        redis_conn = get_redis_connection("default")
        keys = redis_conn.keys(f"lootlink:*:{pattern}")
        
        if keys:
            redis_conn.delete(*keys)
            return len(keys)
        return 0
    except Exception as e:
        # Fallback если Redis недоступен
        print(f"Cache invalidation failed: {e}")
        return 0


def get_client_ip(request) -> str:
    """
    Получить IP адрес клиента из request.
    
    Args:
        request: HTTP request объект
    
    Returns:
        IP адрес клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        # Берем первый IP из списка (клиентский IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip


def clean_phone_number(phone: str) -> str:
    """
    Очистить и нормализовать номер телефона.
    
    Args:
        phone: Номер телефона в любом формате
    
    Returns:
        Номер в формате +7 (999) 123-45-67
    
    Example:
        clean_phone_number("89991234567")  # → "+7 (999) 123-45-67"
        clean_phone_number("+7 999 123 45 67")  # → "+7 (999) 123-45-67"
    """
    import re
    
    # Удаляем все нецифровые символы
    digits = re.sub(r'\D', '', phone)
    
    # Нормализуем формат
    if len(digits) == 11 and digits.startswith('8'):
        # 8 (xxx) xxx-xx-xx → +7 (xxx) xxx-xx-xx
        digits = '7' + digits[1:]
    
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    
    return phone  # Вернуть как есть если не удалось распознать


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Обрезать текст до максимальной длины.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Добавить в конец если обрезано
    
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_price(price: float, currency: str = '₽') -> str:
    """
    Форматировать цену с разделителями тысяч.
    
    Args:
        price: Цена
        currency: Символ валюты
    
    Returns:
        Отформатированная строка
    
    Example:
        format_price(1500.50)  # → "1 500.50 ₽"
    """
    return f"{price:,.2f} {currency}".replace(',', ' ')


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """
    Проверить расширение файла.
    
    Args:
        filename: Имя файла
        allowed_extensions: Список разрешенных расширений ['jpg', 'png']
    
    Returns:
        True если расширение разрешено
    """
    import os
    
    ext = os.path.splitext(filename)[1][1:].lower()
    return ext in [e.lower() for e in allowed_extensions]

