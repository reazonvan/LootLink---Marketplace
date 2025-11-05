"""
Context processors для глобального доступа к данным.
"""

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

