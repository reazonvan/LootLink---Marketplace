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
        
        try:
            # Case-insensitive поиск по username
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            # Запускаем hasher для защиты от timing атак
            User().set_password(password)
            # Логируем неудачную попытку входа
            if request:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
                security_logger.warning(
                    f'Failed login attempt: username={username} | IP={ip} | Reason=UserNotFound'
                )
            return None
        except User.MultipleObjectsReturned:
            # Если каким-то образом есть дубликаты (не должно быть)
            # Берем первого и логируем проблему
            security_logger.error(f'Multiple users found with username (case-insensitive): {username}')
            user = User.objects.filter(username__iexact=username).first()
        
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
                f'Failed login attempt: username={username} | IP={ip} | Reason=InvalidPassword'
            )
        
        return None

