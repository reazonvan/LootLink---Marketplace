"""
Middleware для обновления last_seen пользователя.
"""

from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

LAST_SEEN_THROTTLE_SECONDS = 300  # обновляем не чаще раза в 5 минут


class UpdateLastSeenMiddleware(MiddlewareMixin):
    """Обновляет Profile.last_seen, дросселируя записи через кеш."""

    def process_request(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        cache_key = f"last_seen:{user.id}"
        if cache.get(cache_key):
            return None

        from accounts.models import Profile

        Profile.objects.filter(user=user).update(last_seen=timezone.now())
        cache.set(cache_key, 1, LAST_SEEN_THROTTLE_SECONDS)
        return None
