"""
Кастомный authentication backend для case-insensitive логина
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
security_logger = logging.getLogger('django.security')


class CaseInsensitiveModelBackend(ModelBackend):
    """
    Backend для аутентификации с case-insensitive username.
    
    Позволяет входить как Argear, argear, ARGEAR и т.д.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        login_value = (username or "").strip()
        if not login_value:
            return None
        
        try:
            # Allow login by either username or email.
            if '@' in login_value:
                user = User.objects.get(email__iexact=login_value)
            else:
                user = User.objects.get(username__iexact=login_value)
        except User.DoesNotExist:
            # Запускаем hasher для защиты от timing атак
            User().set_password(password)
            # Логируем неудачную попытку входа
            if request:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
                security_logger.warning(
                    f'Failed login attempt: username={login_value} | IP={ip} | Reason=UserNotFound'
                )
            return None
        except User.MultipleObjectsReturned:
            # FIX: при дубликатах — отказываем в аутентификации вместо выбора первого
            security_logger.error(f'Multiple users found with login value (case-insensitive): {login_value}')
            return None
        
        # Проверяем пароль
        if user and user.check_password(password) and self.user_can_authenticate(user):
            # Успешный вход
            if request:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
                security_logger.info(f'Successful login: username={user.username} | IP={ip}')
            return user
        
        # Неудачная попытка - неверный пароль
        if user and request:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            security_logger.warning(
                f'Failed login attempt: username={login_value} | IP={ip} | Reason=InvalidPassword'
            )
        
        return None

