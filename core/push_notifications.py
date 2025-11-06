"""
Push уведомления для браузера (Web Push API).
"""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class WebPushService:
    """
    Сервис для отправки Push уведомлений в браузер.
    """
    
    def __init__(self):
        self.vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
        self.vapid_public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
        self.vapid_claims = getattr(settings, 'VAPID_CLAIMS', {})
        self.enabled = bool(self.vapid_private_key and self.vapid_public_key)
        
        if self.enabled:
            try:
                from pywebpush import webpush
                self.webpush = webpush
            except ImportError:
                logger.warning('pywebpush not installed. Install: pip install pywebpush')
                self.enabled = False
    
    def send_notification(self, subscription_info, title, body, icon=None, url=None):
        """
        Отправить Push уведомление.
        
        Args:
            subscription_info: dict с subscription данными от браузера
            title: Заголовок уведомления
            body: Текст уведомления
            icon: URL иконки
            url: URL для перехода при клике
        
        Returns:
            bool: Успешность отправки
        """
        if not self.enabled or not subscription_info:
            return False
        
        try:
            data = {
                'title': title,
                'body': body,
                'icon': icon or '/static/favicon.svg',
                'url': url or '/'
            }
            
            self.webpush(
                subscription_info=subscription_info,
                data=str(data),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            
            logger.info(f'Push notification sent: {title}')
            return True
            
        except Exception as e:
            logger.error(f'Failed to send push notification: {e}')
            return False


# Singleton
web_push_service = WebPushService()

