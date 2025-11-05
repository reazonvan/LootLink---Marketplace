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
            # Обновляем last_seen при каждом запросе (оптимизация через cache)
            try:
                from django.core.cache import cache
                from accounts.models import Profile
                
                # Используем кэш чтобы не обновлять БД при каждом запросе
                cache_key = f'last_seen_updated_{request.user.id}'
                
                # Обновляем только если кэш отсутствует (раз в 2 минуты)
                if not cache.get(cache_key):
                    now = timezone.now()
                    Profile.objects.filter(user=request.user).update(last_seen=now)
                    # Ставим флаг на 2 минуты
                    cache.set(cache_key, True, 120)
            except Exception:
                # Если профиля нет или ошибка - не ломаем запрос
                pass
        
        return None

