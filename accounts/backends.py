"""
Кастомный authentication backend для case-insensitive логина
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


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
            return None
        except User.MultipleObjectsReturned:
            # Если каким-то образом есть дубликаты (не должно быть)
            # Берем первого
            user = User.objects.filter(username__iexact=username).first()
        
        # Проверяем пароль
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

