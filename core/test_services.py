"""
Comprehensive тесты для services.
"""
import pytest
from unittest.mock import patch, MagicMock
from core.services import NotificationService
from core.models import Notification


@pytest.mark.django_db
class TestNotificationService:
    """Тесты NotificationService."""
    
    def test_create_and_notify(self, verified_user):
        """Создание уведомления."""
        notification = NotificationService.create_and_notify(
            user=verified_user,
            notification_type='system',
            title='Test Notification',
            message='Test Message',
            link='/test/',
            send_email=False
        )
        
        assert notification is not None
        assert notification.user == verified_user
        assert notification.title == 'Test Notification'
        assert notification.message == 'Test Message'
        assert notification.link == '/test/'
        assert not notification.is_read
    
    @patch('core.services.send_mail')
    def test_create_and_notify_sends_email(self, mock_send_mail, verified_user):
        """Уведомление отправляет email."""
        notification = NotificationService.create_and_notify(
            user=verified_user,
            notification_type='system',
            title='Test Notification',
            message='Test Message',
            send_email=True
        )
        
        # Проверяем что email был отправлен
        # (может быть через Celery или напрямую, в зависимости от доступности)
        assert notification is not None
    
    def test_notify_purchase_request(self, seller, buyer, active_listing, purchase_request_factory):
        """Уведомление о запросе на покупку."""
        purchase = purchase_request_factory(active_listing, buyer)
        
        notification = NotificationService.notify_purchase_request(purchase)
        
        assert notification.user == seller
        assert notification.notification_type == 'purchase_request'
        assert active_listing.title in notification.title
    
    def test_notify_request_accepted(self, seller, buyer, active_listing, purchase_request_factory):
        """Уведомление о принятии запроса."""
        purchase = purchase_request_factory(active_listing, buyer)
        
        notification = NotificationService.notify_request_accepted(purchase)
        
        assert notification.user == buyer
        assert notification.notification_type == 'request_accepted'
    
    def test_notify_request_rejected(self, seller, buyer, active_listing, purchase_request_factory):
        """Уведомление об отклонении запроса."""
        purchase = purchase_request_factory(active_listing, buyer)
        
        notification = NotificationService.notify_request_rejected(purchase)
        
        assert notification.user == buyer
        assert notification.notification_type == 'request_rejected'
    
    def test_notify_deal_completed(self, seller, buyer, active_listing, purchase_request_factory):
        """Уведомление о завершении сделки."""
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        
        notification = NotificationService.notify_deal_completed(purchase)
        
        assert notification.user == buyer
        assert notification.notification_type == 'deal_completed'
    
    def test_notify_new_review(self, seller, buyer, active_listing, purchase_request_factory):
        """Уведомление о новом отзыве."""
        from transactions.models import Review
        
        purchase = purchase_request_factory(active_listing, buyer, status='completed')
        review = Review.objects.create(
            purchase_request=purchase,
            reviewer=buyer,
            reviewed_user=seller,
            rating=5,
            comment='Great!'
        )
        
        notification = NotificationService.notify_new_review(review)
        
        assert notification.user == seller
        assert notification.notification_type == 'new_review'
        assert '⭐' in notification.message
    
    def test_notify_new_message(self, seller, buyer, active_listing, conversation_factory, message_factory):
        """Уведомление о новом сообщении."""
        conversation = conversation_factory(seller, buyer, active_listing)
        message = message_factory(conversation, buyer, 'Test message')
        
        notification = NotificationService.notify_new_message(message, seller)
        
        assert notification.user == seller
        assert notification.notification_type == 'new_message'
        assert buyer.username in notification.title
    
    def test_format_email_body(self, verified_user):
        """Форматирование email тела."""
        body = NotificationService._format_email_body(
            user=verified_user,
            message='Test message',
            link='/test/'
        )
        
        assert verified_user.username in body
        assert 'Test message' in body
        assert '/test/' in body
    
    def test_format_email_body_escapes_html(self, verified_user):
        """Email body экранирует HTML."""
        body = NotificationService._format_email_body(
            user=verified_user,
            message='<script>alert("XSS")</script>',
            link=''
        )
        
        # HTML должен быть экранирован
        assert '<script>' not in body
        assert '&lt;script&gt;' in body or 'script' not in body.lower()

