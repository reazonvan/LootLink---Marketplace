"""
Утилиты для отправки Web Push уведомлений.
"""
import json
import logging
from pywebpush import webpush, WebPushException
from django.conf import settings
from core.models_notifications import PushSubscription

logger = logging.getLogger(__name__)


def send_push_notification(user, title, body, url=None, icon=None):
    """
    Отправка push уведомления пользователю.

    Args:
        user: Пользователь
        title: Заголовок уведомления
        body: Текст уведомления
        url: URL для перехода при клике (опционально)
        icon: URL иконки (опционально)

    Returns:
        dict: Результат отправки {'sent': int, 'failed': int}
    """
    if not hasattr(settings, 'VAPID_PRIVATE_KEY') or not settings.VAPID_PRIVATE_KEY:
        logger.error("VAPID keys not configured")
        return {'sent': 0, 'failed': 0}

    subscriptions = PushSubscription.objects.filter(
        user=user,
        is_active=True
    )

    if not subscriptions.exists():
        logger.info(f"No active push subscriptions for user {user.username}")
        return {'sent': 0, 'failed': 0}

    # Формируем payload
    payload = {
        'title': title,
        'body': body,
        'icon': icon or '/static/img/logo.png',
    }

    if url:
        payload['url'] = url

    sent_count = 0
    failed_count = 0

    for subscription in subscriptions:
        try:
            subscription_info = subscription.subscription_info

            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    'sub': f'mailto:{settings.DEFAULT_FROM_EMAIL}'
                }
            )

            sent_count += 1
            logger.info(f"Push notification sent to {user.username}")

        except WebPushException as e:
            logger.error(f"Failed to send push to {user.username}: {e}")
            failed_count += 1

            # Если подписка невалидна (410 Gone), деактивируем её
            if e.response and e.response.status_code == 410:
                subscription.is_active = False
                subscription.save()
                logger.info(f"Deactivated invalid subscription for {user.username}")

        except Exception as e:
            logger.error(f"Unexpected error sending push to {user.username}: {e}")
            failed_count += 1

    return {'sent': sent_count, 'failed': failed_count}


def send_push_to_multiple_users(users, title, body, url=None, icon=None):
    """
    Отправка push уведомления нескольким пользователям.

    Args:
        users: QuerySet или список пользователей
        title: Заголовок уведомления
        body: Текст уведомления
        url: URL для перехода при клике (опционально)
        icon: URL иконки (опционально)

    Returns:
        dict: Результат отправки {'sent': int, 'failed': int}
    """
    total_sent = 0
    total_failed = 0

    for user in users:
        result = send_push_notification(user, title, body, url, icon)
        total_sent += result['sent']
        total_failed += result['failed']

    return {'sent': total_sent, 'failed': total_failed}
