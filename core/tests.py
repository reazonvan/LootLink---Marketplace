"""
Unit тесты для приложения core.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class NotificationModelTest(TestCase):
    """Тесты для модели Notification."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notification_creation(self):
        """Тест создания уведомления."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Test Notification',
            message='This is a test notification',
            link='/test/'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'new_message')
        self.assertEqual(notification.title, 'Test Notification')
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
    
    def test_mark_as_read(self):
        """Тест отметки уведомления как прочитанного."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='Test',
            message='Test message'
        )
        
        # Изначально непрочитано
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        
        # Отмечаем как прочитанное
        notification.mark_as_read()
        
        # Проверяем
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_create_notification_classmethod(self):
        """Тест создания уведомления через classmethod."""
        notification = Notification.create_notification(
            user=self.user,
            notification_type='purchase_request',
            title='New Purchase Request',
            message='Someone wants to buy your item',
            link='/transactions/1/'
        )
        
        self.assertIsInstance(notification, Notification)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.link, '/transactions/1/')
    
    def test_mark_all_as_read(self):
        """Тест отметки всех уведомлений как прочитанных."""
        # Создаем несколько уведомлений
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Message 1',
            message='Content 1'
        )
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Message 2',
            message='Content 2'
        )
        Notification.objects.create(
            user=self.user,
            notification_type='new_review',
            title='Review',
            message='New review'
        )
        
        # Все должны быть непрочитанными
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(),
            3
        )
        
        # Отмечаем все как прочитанные
        Notification.mark_all_as_read(self.user)
        
        # Все должны быть прочитанными
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(),
            0
        )
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=True).count(),
            3
        )
    
    def test_notification_ordering(self):
        """Тест сортировки уведомлений (новые первыми)."""
        notif1 = Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='First',
            message='First notification'
        )
        notif2 = Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='Second',
            message='Second notification'
        )
        
        notifications = list(Notification.objects.all())
        # Новые должны быть первыми (ordering = ['-created_at'])
        self.assertEqual(notifications[0], notif2)
        self.assertEqual(notifications[1], notif1)


class NotificationViewsTest(TestCase):
    """Тесты для views уведомлений."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notifications_list_requires_login(self):
        """Тест требования авторизации для списка уведомлений."""
        url = reverse('core:notifications_list')
        response = self.client.get(url)
        
        # Должен быть редирект на страницу входа
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_notifications_list_authenticated(self):
        """Тест доступа к списку уведомлений для авторизованного пользователя."""
        self.client.login(username='testuser', password='testpass123')
        
        # Создаем уведомления
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Test Notification',
            message='Test'
        )
        
        url = reverse('core:notifications_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Notification')
    
    def test_mark_notification_read(self):
        """Тест отметки уведомления как прочитанного."""
        self.client.login(username='testuser', password='testpass123')
        
        notification = Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='Test',
            message='Test message'
        )
        
        url = reverse('core:mark_notification_read', kwargs={'pk': notification.pk})
        response = self.client.post(url)
        
        # Проверяем что уведомление отмечено как прочитанное
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
    
    def test_mark_all_notifications_read(self):
        """Тест отметки всех уведомлений как прочитанных."""
        self.client.login(username='testuser', password='testpass123')
        
        # Создаем несколько уведомлений
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Notification 1',
            message='Test 1'
        )
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Notification 2',
            message='Test 2'
        )
        
        url = reverse('core:mark_all_notifications_read')
        response = self.client.post(url)
        
        # Все уведомления должны быть прочитанными
        unread_count = Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
        self.assertEqual(unread_count, 0)
    
    def test_unread_notifications_count_api(self):
        """Тест API для получения количества непрочитанных уведомлений."""
        self.client.login(username='testuser', password='testpass123')
        
        # Создаем уведомления
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Unread 1',
            message='Test',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            notification_type='new_message',
            title='Unread 2',
            message='Test',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='Read',
            message='Test',
            is_read=True
        )
        
        url = reverse('core:unread_notifications_count')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 2)
    
    def test_cannot_read_other_users_notification(self):
        """Тест запрета отметки чужого уведомления как прочитанного."""
        # Создаем второго пользователя
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        # Создаем уведомление для user2
        notification = Notification.objects.create(
            user=user2,
            notification_type='system',
            title='Private',
            message='Private notification'
        )
        
        # Пытаемся прочитать от имени testuser
        self.client.login(username='testuser', password='testpass123')
        url = reverse('core:mark_notification_read', kwargs={'pk': notification.pk})
        response = self.client.post(url)
        
        # Должна быть ошибка 404
        self.assertEqual(response.status_code, 404)


class CoreViewsTest(TestCase):
    """Тесты для других views приложения core."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        self.client = Client()
    
    def test_about_page_loads(self):
        """Тест загрузки страницы 'О нас'."""
        url = reverse('about')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'О нас')
    
    def test_rules_page_loads(self):
        """Тест загрузки страницы 'Правила'."""
        url = reverse('rules')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Правила')
    
    def test_about_page_shows_statistics(self):
        """Тест отображения статистики на странице 'О нас'."""
        url = reverse('about')
        response = self.client.get(url)
        
        # Проверяем что есть статистика
        self.assertIn('total_users', response.context)
        self.assertIn('total_listings', response.context)
        self.assertIn('total_deals', response.context)
