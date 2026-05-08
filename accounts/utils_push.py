"""
Утилиты для отправки Web Push уведомлений.

Phase 13: синхронный сетевой вызов webpush() вынесен в Celery-таск
send_push_async, чтобы не блокировать request/response цикл и не валить
view, если push-сервер браузера медленный или недоступен.
"""
import json
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from pywebpush import webpush, WebPushException

from core.models_notifications import PushSubscription

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push_async(self, subscription_id, payload_json):
    """
    Асинхронная отправка push-уведомления конкретной подписке.

    Args:
        subscription_id: ID PushSubscription.
        payload_json: JSON-строка с payload (title/body/url/icon).

    Особенности:
        - 410 Gone от push-сервера => подписка деактивируется (битая).
        - Прочие сетевые/HTTP-ошибки => retry с экспоненциальным backoff.
        - VAPID-ключи проверяются однократно: если их нет, сразу выходим.
    """
    if not getattr(settings, 'VAPID_PRIVATE_KEY', ''):
        logger.warning('VAPID_PRIVATE_KEY not configured — push skipped')
        return

    sub = PushSubscription.objects.filter(
        id=subscription_id, is_active=True
    ).first()
    if not sub:
        return

    try:
        webpush(
            subscription_info=sub.subscription_info,
            data=payload_json,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                'sub': f'mailto:{settings.DEFAULT_FROM_EMAIL}'
            },
        )
        logger.info(
            f'Push sent to subscription #{sub.id} (user={sub.user_id})'
        )
    except WebPushException as e:
        # 410 Gone => подписка протухла, деактивируем без retry.
        if e.response is not None and e.response.status_code == 410:
            sub.is_active = False
            sub.save(update_fields=['is_active'])
            logger.info(
                f'Deactivated stale subscription #{sub.id} (410 Gone)'
            )
            return
        logger.warning(
            f'WebPushException for subscription #{sub.id}: {e}'
        )
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(
                f'Max retries exceeded for push subscription #{sub.id}'
            )
    except Exception as e:
        logger.exception(
            f'Unexpected error sending push to subscription #{sub.id}: {e}'
        )
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(
                f'Max retries exceeded (unexpected) for push subscription '
                f'#{sub.id}'
            )


def send_push_notification(user, title, body, url=None, icon=None):
    """
    Постановка push-уведомлений в очередь Celery для всех активных
    подписок пользователя.

    Args:
        user: Пользователь.
        title: Заголовок.
        body: Текст.
        url: URL для перехода (опционально).
        icon: URL иконки (опционально).

    Returns:
        dict: {'queued': N, 'failed': 0} — сколько задач поставлено в очередь.
              Реальная отправка произойдёт асинхронно в воркере.
    """
    if not getattr(settings, 'VAPID_PRIVATE_KEY', ''):
        logger.error('VAPID keys not configured')
        return {'queued': 0, 'failed': 0, 'sent': 0}

    subscription_ids = list(
        PushSubscription.objects.filter(
            user=user, is_active=True
        ).values_list('id', flat=True)
    )

    if not subscription_ids:
        logger.info(
            f'No active push subscriptions for user {user.username}'
        )
        return {'queued': 0, 'failed': 0, 'sent': 0}

    payload = {
        'title': title,
        'body': body,
        'icon': icon or '/static/img/logo.png',
    }
    if url:
        payload['url'] = url

    payload_json = json.dumps(payload)

    queued = 0
    for sub_id in subscription_ids:
        # Откладываем .delay() до коммита: если транзакция, в которой
        # генерируется уведомление, откатится — задача не уйдёт в воркер.
        transaction.on_commit(
            lambda sid=sub_id: send_push_async.delay(sid, payload_json)
        )
        queued += 1

    # Ключ 'sent' оставлен для обратной совместимости с прежними вызовами,
    # которые читали результат.
    return {'queued': queued, 'failed': 0, 'sent': queued}


def send_push_to_multiple_users(users, title, body, url=None, icon=None):
    """
    Постановка push-уведомлений в очередь для нескольких пользователей.

    Args:
        users: QuerySet или список пользователей.
        title: Заголовок.
        body: Текст.
        url: URL для перехода (опционально).
        icon: URL иконки (опционально).

    Returns:
        dict: {'queued': N, 'failed': 0}
    """
    total_queued = 0
    total_failed = 0

    for user in users:
        result = send_push_notification(user, title, body, url, icon)
        total_queued += result.get('queued', 0)
        total_failed += result.get('failed', 0)

    return {'queued': total_queued, 'failed': total_failed, 'sent': total_queued}
