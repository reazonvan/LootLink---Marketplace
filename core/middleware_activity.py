"""
Middleware для обновления last_seen пользователя
"""
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from datetime import timedelta


class UpdateLastSeenMiddleware(MiddlewareMixin):
    """
    Обновляет last_seen для авторизованных пользователей.
    Обновление происходит не чаще чем раз в 5 минут (для снижения нагрузки на БД).
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Проверяем когда last_seen обновлялся последний раз
            try:
                profile = request.user.profile
                now = timezone.now()
                
                # Обновляем только если прошло больше 5 минут
                if not profile.last_seen or (now - profile.last_seen) > timedelta(minutes=5):
                    # Используем update для избежания сигналов и save()
                    from accounts.models import Profile
                    Profile.objects.filter(id=profile.id).update(last_seen=now)
                    # Обновляем объект в памяти
                    profile.last_seen = now
            except Exception:
                # Если профиля нет или ошибка - не ломаем запрос
                pass
        
        return None

