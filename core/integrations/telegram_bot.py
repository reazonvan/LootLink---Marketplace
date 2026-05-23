"""
Telegram бот для уведомлений.

Phase 13: синхронный bot.send_message() вынесен в Celery-таск
send_telegram_async, чтобы сетевой вызов к Telegram API не блокировал
view/обработчики и не валил запрос при сбое API.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from celery import shared_task
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


def _get_bot():
    """
    Лениво создаёт инстанс Bot — только когда токен задан и нужна
    реальная отправка. Если токена нет — None, и таск тихо выходит.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        return None
    try:
        return Bot(token=token)
    except Exception as e:
        logger.error(f"Ошибка инициализации Telegram бота: {e}")
        return None


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_async(self, chat_id, text, parse_mode="HTML"):
    """
    Асинхронная отправка Telegram-сообщения.

    Args:
        chat_id: Telegram chat_id получателя.
        text: Текст сообщения.
        parse_mode: HTML или Markdown.

    Поведение:
        - Если бот не настроен (нет токена) — тихо выходит, ничего не делая.
        - Если chat_id пуст — тоже выход.
        - При TelegramError — retry до max_retries.
    """
    if not chat_id:
        return

    bot = _get_bot()
    if bot is None:
        # Интеграция отключена/не настроена — это не ошибка.
        return

    try:
        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )
        logger.info(f"Telegram message sent to {chat_id}")
    except TelegramError as e:
        logger.warning(f"Failed to send Telegram message to {chat_id}: {e}")
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded sending Telegram to {chat_id}")
    except Exception as e:
        logger.exception(f"Unexpected error sending Telegram to {chat_id}: {e}")


def _enqueue_telegram(chat_id, text, parse_mode="HTML"):
    """
    Внутренний хелпер: ставит отправку в Celery, корректно работая внутри
    транзакции (откладывает .delay() до коммита).
    """
    if not chat_id:
        return
    transaction.on_commit(lambda: send_telegram_async.delay(chat_id, text, parse_mode))


class TelegramNotificationService:
    """
    Сервис для отправки уведомлений через Telegram.

    Все методы запускают отправку асинхронно через Celery —
    публичный API остался прежним (notify_*), но теперь они возвращают
    bool: True если задача поставлена в очередь, False если отключено
    или у пользователя нет настроенного chat_id.
    """

    def __init__(self):
        self.token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.enabled = bool(self.token)

    def send_message(self, chat_id, text, parse_mode="HTML"):
        """
        Поставить сообщение в очередь Celery.

        Args:
            chat_id: Telegram ID пользователя
            text: Текст сообщения
            parse_mode: Формат (HTML или Markdown)

        Returns:
            bool: True если отправка запланирована, False если бот выключен.
        """
        if not self.enabled or not chat_id:
            return False

        _enqueue_telegram(chat_id, text, parse_mode)
        return True

    def notify_new_message(self, user, message_from):
        """Уведомление о новом сообщении."""
        if not user.profile.telegram_chat_id or not user.profile.telegram_notifications:
            return False

        text = f"""
<b>Новое сообщение</b>

От: {message_from}
Время: {timezone.now().strftime('%H:%M')}

Откройте чат на сайте LootLink
        """

        return self.send_message(user.profile.telegram_chat_id, text)

    def notify_purchase_request(self, user, listing_title, buyer_name):
        """Уведомление о запросе на покупку."""
        if not user.profile.telegram_chat_id or not user.profile.telegram_notifications:
            return False

        text = f"""
<b>Новый запрос на покупку</b>

Товар: {listing_title}
От: {buyer_name}

Откройте LootLink для подтверждения
        """

        return self.send_message(user.profile.telegram_chat_id, text)

    def notify_price_change(self, user, listing_title, old_price, new_price):
        """Уведомление об изменении цены."""
        if not user.profile.telegram_chat_id or not user.profile.telegram_notifications:
            return False

        change = "снижена" if new_price < old_price else "повышена"

        text = f"""
<b>Цена {change}</b>

Товар: {listing_title}
Было: {old_price} ₽
Стало: {new_price} ₽

Посмотрите на LootLink
        """

        return self.send_message(user.profile.telegram_chat_id, text)


# Singleton
telegram_service = TelegramNotificationService()
