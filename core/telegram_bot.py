"""
Telegram бот для уведомлений.
"""
import logging
from django.conf import settings
from django.utils import timezone
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Сервис для отправки уведомлений через Telegram.
    """
    
    def __init__(self):
        self.token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.enabled = bool(self.token)
        
        if self.enabled:
            try:
                self.bot = Bot(token=self.token)
            except Exception as e:
                logger.error(f'Ошибка инициализации Telegram бота: {e}')
                self.enabled = False
    
    def send_message(self, chat_id, text, parse_mode='HTML'):
        """
        Отправить сообщение пользователю.
        
        Args:
            chat_id: Telegram ID пользователя
            text: Текст сообщения
            parse_mode: Формат (HTML или Markdown)
        
        Returns:
            bool: Успешность отправки
        """
        if not self.enabled or not chat_id:
            return False
        
        try:
            self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f'Telegram message sent to {chat_id}')
            return True
        except TelegramError as e:
            logger.error(f'Failed to send Telegram message: {e}')
            return False
    
    def notify_new_message(self, user, message_from):
        """Уведомление о новом сообщении"""
        if not user.profile.telegram_chat_id or not user.profile.telegram_notifications:
            return False
        
        text = f"""
🔔 <b>Новое сообщение</b>

От: {message_from}
Время: {timezone.now().strftime('%H:%M')}

Откройте чат на сайте LootLink
        """
        
        return self.send_message(user.profile.telegram_chat_id, text)
    
    def notify_purchase_request(self, user, listing_title, buyer_name):
        """Уведомление о запросе на покупку"""
        if not user.profile.telegram_chat_id or not user.profile.telegram_notifications:
            return False
        
        text = f"""
💰 <b>Новый запрос на покупку!</b>

Товар: {listing_title}
От: {buyer_name}

Откройте LootLink для подтверждения
        """
        
        return self.send_message(user.profile.telegram_chat_id, text)
    
    def notify_price_change(self, user, listing_title, old_price, new_price):
        """Уведомление об изменении цены"""
        if not user.profile.telegram_chat_id or not user.profile.telegram_notifications:
            return False
        
        change = 'снижена' if new_price < old_price else 'повышена'
        
        text = f"""
💵 <b>Цена {change}!</b>

Товар: {listing_title}
Было: {old_price} ₽
Стало: {new_price} ₽

Посмотрите на LootLink
        """
        
        return self.send_message(user.profile.telegram_chat_id, text)


# Singleton
telegram_service = TelegramNotificationService()

