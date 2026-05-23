"""
Сигналы безопасности: запись LoginHistory при входе/неудаче.

Подключаются через AccountsConfig.ready().
"""

import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from .models_security import LoginHistory

logger = logging.getLogger("django.security")


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Запись успешного входа в LoginHistory."""
    if request is None:
        return
    # force_login() в тестах создаёт request без META/REMOTE_ADDR —
    # пропускаем, чтобы не ломать тесты NOT NULL constraint.
    ip = LoginHistory.get_client_ip(request)
    if not ip:
        return
    try:
        LoginHistory.log_login(user=user, request=request, success=True)
    except Exception as exc:
        logger.warning("LoginHistory.log_login failed: %s", exc)


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    """Запись неудачной попытки входа.

    P3-7: ищем пользователя и по username, и по email — иначе при логине через
    email signal не находил пользователя и логировал только в файл.
    """
    if request is None:
        return
    login_value = credentials.get("username", "<unknown>")
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if "@" in (login_value or ""):
        user = User.objects.filter(email__iexact=login_value).first()
    else:
        user = User.objects.filter(username__iexact=login_value).first()

    if user is None:
        logger.info(
            "Failed login attempt for non-existent user=%s ip=%s",
            login_value,
            LoginHistory.get_client_ip(request),
        )
        return
    try:
        LoginHistory.log_login(
            user=user,
            request=request,
            success=False,
            failure_reason="Неверный пароль",
        )
    except Exception as exc:
        logger.warning("LoginHistory.log_login (failed) error: %s", exc)
