"""Views для управления Web Push подписками.

CSRF: запросы — AJAX от авторизованного пользователя. CSRF-токен берётся
JS-клиентом из <meta name="csrf-token"> в base.html и отправляется в
X-CSRFToken header. Стандартная Django CSRF-защита включена.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models_notifications import PushSubscription

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def subscribe_push(request):
    """Создание новой push подписки."""
    try:
        data = json.loads(request.body)

        subscription_info = data.get("subscription")
        if not subscription_info:
            return JsonResponse({"error": "Missing subscription data"}, status=400)

        endpoint = subscription_info.get("endpoint")
        if not endpoint:
            return JsonResponse({"error": "Invalid subscription data"}, status=400)

        # Создаем или обновляем подписку
        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            subscription_info__endpoint=endpoint,
            defaults={
                "subscription_info": subscription_info,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "is_active": True,
            },
        )
        logger.info(
            "push subscription %s: user=%s id=%s",
            "created" if created else "updated",
            request.user.pk,
            subscription.pk,
        )

        return JsonResponse(
            {
                "success": True,
                "created": created,
                "message": "Подписка успешно создана" if created else "Подписка обновлена",
            }
        )

    except json.JSONDecodeError:
        logger.info("push subscribe bad JSON: user=%s", request.user.pk)
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("push subscribe failed: user=%s", request.user.pk)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def unsubscribe_push(request):
    """Отписка от push уведомлений."""
    try:
        data = json.loads(request.body)
        endpoint = data.get("endpoint")

        if not endpoint:
            return JsonResponse({"error": "Missing endpoint"}, status=400)

        deleted_count = PushSubscription.objects.filter(
            user=request.user, subscription_info__endpoint=endpoint
        ).delete()[0]
        logger.info(
            "push unsubscribe: user=%s deleted=%s",
            request.user.pk,
            deleted_count,
        )

        return JsonResponse(
            {
                "success": True,
                "deleted": deleted_count > 0,
                "message": "Подписка удалена" if deleted_count > 0 else "Подписка не найдена",
            }
        )

    except json.JSONDecodeError:
        logger.info("push unsubscribe bad JSON: user=%s", request.user.pk)
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("push unsubscribe failed: user=%s", request.user.pk)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_vapid_public_key(request):
    """Получение публичного VAPID ключа."""
    from django.conf import settings

    public_key = getattr(settings, "VAPID_PUBLIC_KEY", "")

    if not public_key:
        return JsonResponse({"error": "VAPID key not configured"}, status=500)

    return JsonResponse({"publicKey": public_key})
