"""
Кастомный authentication backend для case-insensitive логина
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()
security_logger = logging.getLogger("django.security")


def _get_ip(request) -> str:
    if request is None:
        return "unknown"
    from core.utils import get_client_ip

    return get_client_ip(request) or "unknown"


class CaseInsensitiveModelBackend(ModelBackend):
    """
    Backend для аутентификации с case-insensitive username/email.

    Позволяет входить как Argear, argear, ARGEAR и т.д.
    Использует get_client_ip (учитывает trusted proxies) вместо REMOTE_ADDR.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        login_value = (username or "").strip()
        if not login_value:
            return None

        try:
            # Allow login by either username or email.
            if "@" in login_value:
                user = User.objects.get(email__iexact=login_value)
            else:
                user = User.objects.get(username__iexact=login_value)
        except User.DoesNotExist:
            # Защита от timing-атак: всё равно прогоняем hasher.
            User().set_password(password)
            if request:
                ip = _get_ip(request)
                security_logger.warning(
                    f"Failed login attempt: username={login_value} | IP={ip} | Reason=UserNotFound"
                )
                self._log_failed_login(request, login_value, ip)
            return None
        except User.MultipleObjectsReturned:
            security_logger.error(
                f"Multiple users found with login value (case-insensitive): {login_value}"
            )
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            if request:
                ip = _get_ip(request)
                security_logger.info(f"Successful login: username={user.username} | IP={ip}")
            return user

        if user and request:
            ip = _get_ip(request)
            security_logger.warning(
                f"Failed login attempt: username={login_value} | IP={ip} | Reason=InvalidPassword"
            )
            self._log_failed_login(request, login_value, ip)

        return None

    @staticmethod
    def _log_failed_login(request, username, ip_address):
        """Записываем неудачную попытку в SecurityAuditLog для brute force protection."""
        try:
            from core.models_audit import SecurityAuditLog

            SecurityAuditLog.log(
                action_type="login_failed",
                description=f"Неудачная попытка входа: {username}",
                risk_level="medium",
                request=request,
                metadata={"username": username, "ip_address": ip_address},
            )
        except Exception:
            # Запись в аудит не должна ломать логин-флоу, но молчать
            # тоже нельзя — security-логгер увидит инцидент.
            security_logger.exception(
                "Failed to write SecurityAuditLog for login_failed event " "(username=%s, ip=%s)",
                username,
                ip_address,
            )
