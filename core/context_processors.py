"""
Context processors для глобального доступа к данным.
"""
from django.conf import settings


def notifications_processor(request):
    """
    Добавляет количество непрочитанных уведомлений в контекст шаблона.
    Использует кэширование для снижения нагрузки на БД.
    """
    unread_count = 0
    
    if request.user.is_authenticated:
        from django.core.cache import cache
        from core.models import Notification
        
        # Кэшируем количество уведомлений на 1 минуту
        cache_key = f'unread_notif_count_{request.user.id}'
        unread_count = cache.get(cache_key)
        
        if unread_count is None:
            unread_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
            cache.set(cache_key, unread_count, 60)  # 1 минута
    
    return {
        'unread_notifications_count': unread_count
    }


def site_context(request):
    """
    Добавляет нормализованный SITE_URL и canonical URL в контекст.
    Нужен для корректных SEO-мета-тегов без хардкода домена.
    """
    configured_site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    site_url = configured_site_url or request.build_absolute_uri('/').rstrip('/')

    return {
        'site_url': site_url,
        'canonical_url': f'{site_url}{request.path}',
    }

