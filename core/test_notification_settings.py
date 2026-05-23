"""
Тесты страницы настроек уведомлений (POST → save).
"""

from django.urls import reverse

import pytest

from core.models_notifications import NotificationSettings


@pytest.mark.django_db
class TestNotificationSettingsView:
    """Тесты сохранения настроек уведомлений."""

    def test_get_requires_login(self, client):
        """Анонимный пользователь редиректится на login."""
        response = client.get(reverse("core:notification_settings"))
        assert response.status_code == 302

    def test_get_creates_settings(self, authenticated_client, verified_user):
        """GET создаёт NotificationSettings, если его не было."""
        assert not NotificationSettings.objects.filter(user=verified_user).exists()

        response = authenticated_client.get(reverse("core:notification_settings"))

        assert response.status_code == 200
        assert NotificationSettings.objects.filter(user=verified_user).exists()

    def test_post_saves_settings(self, authenticated_client, verified_user):
        """POST сохраняет состояние чекбоксов."""
        # Сначала GET, чтобы создались дефолтные настройки.
        authenticated_client.get(reverse("core:notification_settings"))

        # POST: оставляем только email_review, остальное снимаем.
        response = authenticated_client.post(
            reverse("core:notification_settings"),
            data={"email_review": "on"},
        )
        assert response.status_code == 302

        settings_obj = NotificationSettings.objects.get(user=verified_user)
        assert settings_obj.email_review is True
        assert settings_obj.email_new_message is False
        assert settings_obj.email_purchase_request is False
        assert settings_obj.email_price_offer is False

    def test_post_all_checked(self, authenticated_client, verified_user):
        """POST со всеми включёнными чекбоксами."""
        response = authenticated_client.post(
            reverse("core:notification_settings"),
            data={
                "email_new_message": "on",
                "email_purchase_request": "on",
                "email_price_offer": "on",
                "email_review": "on",
            },
        )
        assert response.status_code == 302

        settings_obj = NotificationSettings.objects.get(user=verified_user)
        assert settings_obj.email_new_message is True
        assert settings_obj.email_purchase_request is True
        assert settings_obj.email_price_offer is True
        assert settings_obj.email_review is True
