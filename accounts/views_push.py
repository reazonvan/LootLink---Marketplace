"""
Views для управления Web Push подписками.
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from core.models_notifications import PushSubscription


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def subscribe_push(request):
    """Создание новой push подписки."""
    try:
        data = json.loads(request.body)

        subscription_info = data.get('subscription')
        if not subscription_info:
            return JsonResponse({'error': 'Missing subscription data'}, status=400)

        endpoint = subscription_info.get('endpoint')
        if not endpoint:
            return JsonResponse({'error': 'Invalid subscription data'}, status=400)

        # Создаем или обновляем подписку
        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            subscription_info__endpoint=endpoint,
            defaults={
                'subscription_info': subscription_info,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'is_active': True,
            }
        )

        return JsonResponse({
            'success': True,
            'created': created,
            'message': 'Подписка успешно создана' if created else 'Подписка обновлена'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def unsubscribe_push(request):
    """Отписка от push уведомлений."""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')

        if not endpoint:
            return JsonResponse({'error': 'Missing endpoint'}, status=400)

        deleted_count = PushSubscription.objects.filter(
            user=request.user,
            subscription_info__endpoint=endpoint
        ).delete()[0]

        return JsonResponse({
            'success': True,
            'deleted': deleted_count > 0,
            'message': 'Подписка удалена' if deleted_count > 0 else 'Подписка не найдена'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_vapid_public_key(request):
    """Получение публичного VAPID ключа."""
    from django.conf import settings

    public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')

    if not public_key:
        return JsonResponse({'error': 'VAPID key not configured'}, status=500)

    return JsonResponse({
        'publicKey': public_key
    })
