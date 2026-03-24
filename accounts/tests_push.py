"""
Тесты для Web Push уведомлений.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models_notifications import PushSubscription

User = get_user_model()


class PushNotificationTests(TestCase):
    """Тесты для push уведомлений."""

    def setUp(self):
        """Настройка тестов."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_subscribe_push(self):
        """Тест подписки на push уведомления."""
        subscription_data = {
            'subscription': {
                'endpoint': 'https://fcm.googleapis.com/fcm/send/test123',
                'keys': {
                    'p256dh': 'test_p256dh_key',
                    'auth': 'test_auth_key'
                }
            }
        }

        response = self.client.post(
            '/accounts/push/subscribe/',
            data=json.dumps(subscription_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Проверяем что подписка создана
        self.assertTrue(
            PushSubscription.objects.filter(user=self.user).exists()
        )

    def test_unsubscribe_push(self):
        """Тест отписки от push уведомлений."""
        # Создаем подписку
        subscription_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/test123',
            'keys': {
                'p256dh': 'test_p256dh_key',
                'auth': 'test_auth_key'
            }
        }
        PushSubscription.objects.create(
            user=self.user,
            subscription_info=subscription_info
        )

        # Отписываемся
        response = self.client.post(
            '/accounts/push/unsubscribe/',
            data=json.dumps({'endpoint': subscription_info['endpoint']}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Проверяем что подписка удалена
        self.assertFalse(
            PushSubscription.objects.filter(user=self.user).exists()
        )

    def test_get_vapid_key(self):
        """Тест получения VAPID ключа."""
        from django.conf import settings

        # Пропускаем тест если VAPID ключ не настроен
        if not hasattr(settings, 'VAPID_PUBLIC_KEY') or not settings.VAPID_PUBLIC_KEY:
            self.skipTest('VAPID_PUBLIC_KEY not configured')

        response = self.client.get('/accounts/push/vapid-key/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('publicKey', data)

    def test_subscribe_requires_auth(self):
        """Тест что подписка требует авторизации."""
        self.client.logout()

        response = self.client.post(
            '/accounts/push/subscribe/',
            data=json.dumps({'subscription': {}}),
            content_type='application/json'
        )

        # Должен редиректить на логин
        self.assertEqual(response.status_code, 302)
