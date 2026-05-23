"""
Декораторы для проверки прав доступа персонала
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def owner_required(view_func):
    """Только для владельца сайта (superuser)"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Доступ запрещен. Требуются права владельца.")
            return redirect("listings:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    """Для администраторов и выше (staff)"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Доступ запрещен. Требуются права администратора.")
            return redirect("listings:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def moderator_required(view_func):
    """Для модераторов и выше"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Проверка: is_staff ИЛИ есть роль модератора
        if not (
            request.user.is_staff
            or hasattr(request.user, "profile")
            and request.user.profile.is_moderator
        ):
            messages.error(request, "Доступ запрещен. Требуются права модератора.")
            return redirect("listings:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def verified_required(view_func):
    """Только для верифицированных пользователей (телефон/email подтверждены).

    Безопасный hasattr-фолбэк, чтобы не упасть на пользователях без Profile.
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        is_verified = bool(profile and profile.is_verified)
        if not is_verified:
            messages.warning(
                request,
                "Для доступа к этой функции необходимо подтвердить телефон. "
                "Перейдите на страницу верификации.",
            )
            return redirect("accounts:phone_verification_confirm")
        return view_func(request, *args, **kwargs)

    return wrapper


def api_rate_limit(max_requests=60, time_window=60):
    """
    Rate limiting для API endpoints.

    Анонимные пользователи ограничиваются по IP, авторизованные — по user.id.
    Использует cache.incr — атомарная операция (без race condition).

    Args:
        max_requests: Максимум запросов
        time_window: Временное окно в секундах
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.core.cache import cache
            from django.http import JsonResponse

            from core.utils import get_client_ip

            # Разделяем кеш для анонимов (по IP) и авторизованных (по user.id)
            if request.user.is_authenticated:
                bucket = f"u{request.user.id}"
            else:
                bucket = f"ip{get_client_ip(request)}"
            cache_key = f"api_rate_limit_{bucket}_{view_func.__name__}"

            try:
                current = cache.incr(cache_key)
            except ValueError:
                # Ключа ещё нет — создаём с TTL
                cache.set(cache_key, 1, time_window)
                current = 1

            if current > max_requests:
                return JsonResponse(
                    {
                        "error": "Слишком много запросов. Попробуйте позже.",
                        "retry_after": time_window,
                    },
                    status=429,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """Атомарная проверка rate-limit для использования в views.

    Returns:
        (allowed, current_count): allowed=False если лимит превышен.
    """
    from django.core.cache import cache

    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window_seconds)
        current = 1
    return current <= max_attempts, current


def staff_member_required(view_func):
    """Для всех сотрудников (staff, moderator, admin, owner).

    Безопасный fallback при отсутствии profile (без AttributeError).
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user
        profile = getattr(user, "profile", None)
        is_staff_member = (
            user.is_staff or user.is_superuser or (profile is not None and profile.is_moderator)
        )

        if not is_staff_member:
            messages.error(request, "Доступ запрещен. Требуются права сотрудника.")
            return redirect("listings:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def require_2fa(view_func):
    """P2-10: блокирует staff-доступ без настроенной 2FA.

    Применяется к админ-панели поверх staff_member_required.
    Если у staff-пользователя нет confirmed TOTP-устройства —
    перенаправление на setup_2fa с пояснением.
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = request.user
        profile = getattr(user, "profile", None)
        is_privileged = (
            user.is_staff or user.is_superuser or (profile is not None and profile.is_moderator)
        )
        if not is_privileged:
            return view_func(request, *args, **kwargs)

        has_2fa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        if not has_2fa:
            messages.error(
                request,
                "Для доступа к админ-панели обязательна двухфакторная "
                "аутентификация. Настройте её в настройках безопасности.",
            )
            return redirect("accounts:setup_2fa")
        return view_func(request, *args, **kwargs)

    return wrapper
