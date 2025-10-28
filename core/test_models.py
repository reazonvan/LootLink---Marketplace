"""
Comprehensive тесты для моделей core.
"""
import pytest
from core.models import Notification
from django.utils import timezone


@pytest.mark.django_db
class TestNotificationModel:
    """Тесты модели Notification."""
    
    def test_notification_creation(self, verified_user):
        """Создание уведомления."""
        notification = Notification.objects.create(
            user=verified_user,
            notification_type='system',
            title='Test Notification',
            message='Test Message',
            link='/test/'
        )
        
        assert notification.user == verified_user
        assert notification.notification_type == 'system'
        assert not notification.is_read
    
    def test_notification_str(self, verified_user):
        """Строковое представление."""
        notification = Notification.objects.create(
            user=verified_user,
            notification_type='system',
            title='Test',
            message='Message'
        )
        
        assert verified_user.username in str(notification)
        assert 'Test' in str(notification)
    
    def test_mark_as_read(self, verified_user):
        """Отметка как прочитанное."""
        notification = Notification.objects.create(
            user=verified_user,
            notification_type='system',
            title='Test',
            message='Message'
        )
        
        assert not notification.is_read
        assert notification.read_at is None
        
        notification.mark_as_read()
        
        assert notification.is_read
        assert notification.read_at is not None
    
    def test_create_notification_classmethod(self, verified_user):
        """Классовый метод create_notification."""
        notification = Notification.create_notification(
            user=verified_user,
            notification_type='system',
            title='Test',
            message='Message',
            link='/test/'
        )
        
        assert notification is not None
        assert notification.user == verified_user
    
    def test_mark_all_as_read(self, verified_user):
        """Отметка всех как прочитанные."""
        # Создаем несколько уведомлений
        for i in range(5):
            Notification.objects.create(
                user=verified_user,
                notification_type='system',
                title=f'Test {i}',
                message=f'Message {i}'
            )
        
        # Проверяем что все непрочитанные
        assert Notification.objects.filter(user=verified_user, is_read=False).count() == 5
        
        # Отмечаем все
        Notification.mark_all_as_read(verified_user)
        
        # Проверяем что все прочитанные
        assert Notification.objects.filter(user=verified_user, is_read=False).count() == 0
        assert Notification.objects.filter(user=verified_user, is_read=True).count() == 5
    
    def test_notification_ordering(self, verified_user):
        """Уведомления сортируются по дате (новые first)."""
        notif1 = Notification.objects.create(
            user=verified_user,
            notification_type='system',
            title='Old',
            message='Old'
        )
        
        notif2 = Notification.objects.create(
            user=verified_user,
            notification_type='system',
            title='New',
            message='New'
        )
        
        notifications = list(Notification.objects.all())
        assert notifications[0] == notif2  # Новое первое


@pytest.mark.django_db
class TestNotificationTypes:
    """Тесты разных типов уведомлений."""
    
    def test_all_notification_types_valid(self, verified_user):
        """Все типы уведомлений валидны."""
        types = [
            'new_message',
            'purchase_request',
            'request_accepted',
            'request_rejected',
            'deal_completed',
            'new_review',
            'system',
        ]
        
        for notification_type in types:
            notification = Notification.objects.create(
                user=verified_user,
                notification_type=notification_type,
                title=f'Test {notification_type}',
                message='Test'
            )
            assert notification.notification_type == notification_type

