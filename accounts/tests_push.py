"""
Тесты для Web Push уведомлений.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models_notifications import PushSubscription

User = get_user_model()


class PushNotificationTests(TestCase):
    """Тесты для push уведомлений."""

    def setUp(self):
        """Настройка тестов."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_subscribe_push(self):
        """Тест подписки на push уведомления."""
        subscription_data = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
                "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
            }
        }

        response = self.client.post(
            "/accounts/push/subscribe/",
            data=json.dumps(subscription_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Проверяем что подписка создана
        self.assertTrue(PushSubscription.objects.filter(user=self.user).exists())

    def test_unsubscribe_push(self):
        """Тест отписки от push уведомлений."""
        # Создаем подписку
        subscription_info = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {"p256dh": "test_p256dh_key", "auth": "test_auth_key"},
        }
        PushSubscription.objects.create(user=self.user, subscription_info=subscription_info)

        # Отписываемся
        response = self.client.post(
            "/accounts/push/unsubscribe/",
            data=json.dumps({"endpoint": subscription_info["endpoint"]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Проверяем что подписка удалена
        self.assertFalse(PushSubscription.objects.filter(user=self.user).exists())

    def test_get_vapid_key(self):
        """Тест получения VAPID ключа."""
        from django.conf import settings

        # Пропускаем тест если VAPID ключ не настроен
        if not hasattr(settings, "VAPID_PUBLIC_KEY") or not settings.VAPID_PUBLIC_KEY:
            self.skipTest("VAPID_PUBLIC_KEY not configured")

        response = self.client.get("/accounts/push/vapid-key/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("publicKey", data)

    def test_subscribe_requires_auth(self):
        """Тест что подписка требует авторизации."""
        self.client.logout()

        response = self.client.post(
            "/accounts/push/subscribe/",
            data=json.dumps({"subscription": {}}),
            content_type="application/json",
        )

        # Должен редиректить на логин
        self.assertEqual(response.status_code, 302)

    def test_subscribe_requires_csrf_token(self):
        """Тест что подписка требует CSRF-токен (без csrf_exempt).

        Регрессия на удаление `@csrf_exempt` из views_push.subscribe_push:
        Django Client по умолчанию пропускает CSRF — поэтому здесь
        используется enforce_csrf_checks=True. JS-фронтенд должен передавать
        токен в X-CSRFToken header (см. static/js/push-notifications.js).
        """
        from django.middleware.csrf import _get_new_csrf_string, _mask_cipher_secret

        # Клиент с принудительной проверкой CSRF
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="testuser", password="testpass123")

        # 1) Без CSRF-токена должно вернуть 403
        response = csrf_client.post(
            "/accounts/push/subscribe/",
            data=json.dumps({"subscription": {"endpoint": "https://example.com/x"}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403, msg="subscribe должен требовать CSRF")

        # 2) С CSRF-токеном (cookie + X-CSRFToken header) должно работать
        secret = _get_new_csrf_string()
        token = _mask_cipher_secret(secret)
        csrf_client.cookies["lootlink_csrftoken"] = secret

        response_ok = csrf_client.post(
            "/accounts/push/subscribe/",
            data=json.dumps(
                {
                    "subscription": {
                        "endpoint": "https://example.com/csrf-ok",
                        "keys": {"p256dh": "k", "auth": "a"},
                    },
                }
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response_ok.status_code, 200)
        self.assertTrue(response_ok.json()["success"])
