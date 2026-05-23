"""
Тесты 2FA (двухфакторная аутентификация).
"""

import base64
import re

from django.urls import reverse

import pytest


@pytest.mark.django_db
class TestSetup2FA:
    """Тесты страницы настройки 2FA."""

    def test_setup_requires_login(self, client):
        """Анонимный пользователь редиректится."""
        response = client.get(reverse("accounts:setup_2fa"))
        assert response.status_code == 302

    def test_setup_renders_qr(self, authenticated_client):
        """Страница setup отдаёт QR-код и секрет."""
        response = authenticated_client.get(reverse("accounts:setup_2fa"))

        assert response.status_code == 200
        assert response.context["2fa_enabled"] is False
        assert response.context["qr_code"]  # base64 PNG
        assert response.context["secret_key"]
        assert response.context["device_id"]

    def test_secret_key_is_base32(self, authenticated_client):
        """Секрет 2FA должен быть в base32 (для совместимости с Google Authenticator)."""
        response = authenticated_client.get(reverse("accounts:setup_2fa"))

        secret = response.context["secret_key"]

        # base32 алфавит: A-Z и 2-7, плюс возможный padding '='.
        assert re.fullmatch(
            r"[A-Z2-7=]+", secret
        ), f"Секрет 2FA должен быть в base32, получено: {secret!r}"

        # Должен корректно декодироваться обратно из base32.
        # Если django-otp хранит ключ в hex — наша конвертация в base32
        # должна быть обратимой.
        try:
            decoded = base64.b32decode(secret)
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"Секрет {secret!r} не валидный base32: {exc}")

        # django-otp по умолчанию генерирует 20-байтовый ключ.
        assert len(decoded) == 20
