from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from .models import Notification


def custom_404(request, exception):
    """Кастомная страница 404."""
    return render(request, '404.html', status=404)


def custom_500(request):
    """Кастомная страница 500."""
    return render(request, '500.html', status=500)


def about(request):
    """Страница 'О нас' с реальной статистикой из PostgreSQL."""
    from accounts.models import CustomUser
    from listings.models import Listing, Game
    from transactions.models import PurchaseRequest
    
    # Реальная статистика
    total_users = CustomUser.objects.count()
    total_listings = Listing.objects.filter(status='active').count()
    total_deals = PurchaseRequest.objects.filter(status='completed').count()
    total_games = Game.objects.filter(is_active=True).count()
    
    context = {
        'total_users': total_users,
        'total_listings': total_listings,
        'total_deals': total_deals,
        'total_games': total_games,
    }
    
    return render(request, 'pages/about.html', context)


def rules(request):
    """Страница 'Правила'."""
    return render(request, 'pages/rules.html')


# ========== СИСТЕМА УВЕДОМЛЕНИЙ ==========

@login_required
def notifications_list(request):
    """Список уведомлений пользователя с пагинацией и автопрочтением."""
    from django.core.cache import cache
    
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Пагинация - 20 уведомлений на страницу
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Автоматически отмечаем видимые уведомления как прочитанные (первая страница)
    if not page_number or page_number == '1':
        # Отмечаем первые 10 уведомлений как прочитанные (верхние на странице)
        unread_on_page = [n for n in page_obj.object_list if not n.is_read][:10]
        if unread_on_page:
            # Используем update для массового обновления
            from django.utils import timezone
            notification_ids = [n.id for n in unread_on_page]
            Notification.objects.filter(id__in=notification_ids).update(
                is_read=True,
                read_at=timezone.now()
            )
            # Инвалидируем кэш
            cache_key = f'unread_notif_count_{request.user.id}'
            cache.delete(cache_key)
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj.object_list,
    }
    
    return render(request, 'core/notifications_list.html', context)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, pk):
    """Отметить уведомление как прочитанное."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    # Если AJAX запрос
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Уведомление отмечено как прочитанное'
        })
    
    # Иначе редирект
    return redirect('core:notifications_list')


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Отметить все уведомления пользователя как прочитанные."""
    Notification.mark_all_as_read(request.user)
    
    # Если AJAX запрос
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Все уведомления отмечены как прочитанные'
        })
    
    # Иначе редирект
    return redirect('core:notifications_list')


@login_required
@require_http_methods(["GET"])
def unread_notifications_count(request):
    """API endpoint для получения количества непрочитанных уведомлений (AJAX) с rate limiting."""
    from core.decorators import api_rate_limit
    
    # Применяем rate limiting: максимум 120 запросов в минуту
    @api_rate_limit(max_requests=120, time_window=60)
    def _get_count():
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'count': count
        })
    
    return _get_count()

