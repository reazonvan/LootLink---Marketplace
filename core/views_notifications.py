"""
Views для настроек уведомлений.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models_notifications import NotificationSettings, PushSubscription


@login_required
def notification_settings(request):
    """Настройки уведомлений"""
    settings_obj, created = NotificationSettings.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        # Email settings
        settings_obj.email_new_message = request.POST.get('email_new_message') == 'on'
        settings_obj.email_purchase_request = request.POST.get('email_purchase_request') == 'on'
        settings_obj.email_price_offer = request.POST.get('email_price_offer') == 'on'
        settings_obj.email_review = request.POST.get('email_review') == 'on'
        
        # Telegram settings
        settings_obj.telegram_enabled = request.POST.get('telegram_enabled') == 'on'
        
        # Digest frequency
        settings_obj.digest_frequency = request.POST.get('digest_frequency', 'realtime')
        
        settings_obj.save()
        
        messages.success(request, 'Настройки уведомлений сохранены')
        return redirect('core:notification_settings')
    
    context = {
        'settings': settings_obj
    }
    return render(request, 'core/notification_settings.html', context)


@login_required
@require_http_methods(['POST'])
def subscribe_push(request):
    """Подписка на Push уведомления"""
    import json
    
    try:
        subscription_info = json.loads(request.body)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Создаем или обновляем подписку
        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            subscription_info__endpoint=subscription_info.get('endpoint'),
            defaults={
                'subscription_info': subscription_info,
                'user_agent': user_agent,
                'is_active': True
            }
        )
        
        # Обновляем настройки
        settings_obj, _ = NotificationSettings.objects.get_or_create(user=request.user)
        settings_obj.push_enabled = True
        settings_obj.push_subscription = subscription_info
        settings_obj.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Push уведомления включены'
        })
        
    except Exception as e:
        logger.error(f'Error subscribing to push: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(['POST'])
def link_telegram(request):
    """Связать аккаунт с Telegram"""
    import secrets
    
    # Генерируем уникальный код для связывания
    link_code = secrets.token_urlsafe(16)
    
    # Сохраняем в сессии
    request.session['telegram_link_code'] = link_code
    request.session['telegram_link_expires'] = (
        timezone.now() + timezone.timedelta(minutes=10)
    ).isoformat()
    
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', 'LootLinkBot')
    link_url = f'https://t.me/{bot_username}?start={link_code}'
    
    return JsonResponse({
        'success': True,
        'link_code': link_code,
        'link_url': link_url,
        'bot_username': bot_username
    })

