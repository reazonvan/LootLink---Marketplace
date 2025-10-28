"""
Context processors для глобального доступа к данным.
"""

def notifications_processor(request):
    """
    Добавляет количество непрочитанных уведомлений в контекст шаблона.
    """
    unread_count = 0
    
    if request.user.is_authenticated:
        from core.models import Notification
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
    
    return {
        'unread_notifications_count': unread_count
    }

