"""
Кастомные Throttle классы для API rate limiting.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """
    Burst лимит - быстрые запросы в короткий период.
    Защита от spamming и abuse.
    """
    scope = 'burst'


class CreateRateThrottle(UserRateThrottle):
    """
    Лимит для создания новых объектов (POST запросы).
    Более строгий лимит чтобы предотвратить спам.
    """
    scope = 'create'
    
    def allow_request(self, request, view):
        # Применяем только к POST запросам
        if request.method != 'POST':
            return True
        return super().allow_request(request, view)


class ModifyRateThrottle(UserRateThrottle):
    """
    Лимит для модификации объектов (PUT, PATCH, DELETE).
    """
    scope = 'modify'
    
    def allow_request(self, request, view):
        # Применяем к PUT, PATCH, DELETE
        if request.method not in ['PUT', 'PATCH', 'DELETE']:
            return True
        return super().allow_request(request, view)


class StrictAnonRateThrottle(AnonRateThrottle):
    """
    Строгий лимит для анонимных пользователей на критичных эндпоинтах.
    """
    scope = 'anon'
    
    def get_cache_key(self, request, view):
        # Используем IP + User-Agent для более точного определения
        if request.user and request.user.is_authenticated:
            return None  # Не применяем к аутентифицированным
            
        ident = self.get_ident(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:50]
        return self.cache_format % {
            'scope': self.scope,
            'ident': f'{ident}_{hash(user_agent)}'
        }

