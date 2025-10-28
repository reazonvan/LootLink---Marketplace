"""
Декораторы для проверки прав доступа персонала
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def owner_required(view_func):
    """Только для владельца сайта (superuser)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Доступ запрещен. Требуются права владельца.')
            return redirect('listings:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Для администраторов и выше (staff)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Доступ запрещен. Требуются права администратора.')
            return redirect('listings:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def moderator_required(view_func):
    """Для модераторов и выше"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Проверка: is_staff ИЛИ есть роль модератора
        if not (request.user.is_staff or hasattr(request.user, 'profile') and request.user.profile.is_moderator):
            messages.error(request, 'Доступ запрещен. Требуются права модератора.')
            return redirect('listings:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def verified_required(view_func):
    """Только для пользователей с подтвержденным email"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.profile.is_verified:
            messages.warning(
                request,
                'Для доступа к этой функции необходимо подтвердить email. '
                'Проверьте почту или запросите новое письмо.'
            )
            return redirect('accounts:resend_verification_email')
        return view_func(request, *args, **kwargs)
    return wrapper


def api_rate_limit(max_requests=60, time_window=60):
    """
    Rate limiting для API endpoints
    
    Args:
        max_requests: Максимум запросов
        time_window: Временное окно в секундах
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.core.cache import cache
            from django.http import JsonResponse
            
            # Ключ для кеша
            cache_key = f'api_rate_limit_{request.user.id}_{view_func.__name__}'
            
            # Получить текущее количество запросов
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= max_requests:
                return JsonResponse({
                    'error': 'Слишком много запросов. Попробуйте позже.',
                    'retry_after': time_window
                }, status=429)
            
            # Увеличить счетчик
            cache.set(cache_key, current_requests + 1, time_window)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def staff_member_required(view_func):
    """Для всех сотрудников (staff, moderator, admin, owner)"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        is_staff_member = (
            request.user.is_staff or
            request.user.is_superuser or
            (hasattr(request.user, 'profile') and request.user.profile.is_moderator)
        )
        
        if not is_staff_member:
            messages.error(request, 'Доступ запрещен. Требуются права сотрудника.')
            return redirect('listings:home')
        return view_func(request, *args, **kwargs)
    return wrapper
