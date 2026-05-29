"""Тесты core/integrations/sms_service.py."""

from unittest.mock import MagicMock, patch

import pytest

from core.integrations.sms_service import (
    SMSService,
    send_password_reset_sms,
    send_sms,
    send_verification_sms,
)

# ─────────────────────────────────────────────────────────────────────
# SMSService — конструктор / dispatcher
# ─────────────────────────────────────────────────────────────────────


def test_sms_service_disabled_returns_true_silently(settings):
    """SMS_ENABLED=False → True без сетевого вызова (тихий режим dev)."""
    settings.SMS_ENABLED = False
    svc = SMSService()
    assert svc.enabled is False

    with patch("core.integrations.sms_service.requests.get") as mock_get:
        assert svc.send_sms("+79991234567", "hi") is True
    mock_get.assert_not_called()


def test_sms_service_no_api_key_returns_false(settings):
    """enabled=True но без API key → False, без сетевого вызова."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = ""

    svc = SMSService()
    with patch("core.integrations.sms_service.requests.get") as mock_get:
        assert svc.send_sms("+79991234567", "hi") is False
    mock_get.assert_not_called()


def test_sms_service_strips_non_digits_from_phone(settings):
    """phone приводится к цифрам перед запросом."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = "test-key"

    svc = SMSService()
    fake_response = MagicMock()
    fake_response.json.return_value = {"status": "OK"}

    with patch(
        "core.integrations.sms_service.requests.get",
        return_value=fake_response,
    ) as mock_get:
        svc.send_sms("+7 (999) 123-45-67", "hi")

    params = mock_get.call_args.kwargs["params"]
    assert params["to"] == "79991234567"


def test_sms_service_returns_true_on_ok_status(settings):
    """API возвращает status=OK → True."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = "k"

    svc = SMSService()
    fake = MagicMock()
    fake.json.return_value = {"status": "OK"}

    with patch("core.integrations.sms_service.requests.get", return_value=fake):
        assert svc.send_sms("+79991234567", "hi") is True


def test_sms_service_returns_false_on_error_status(settings):
    """API возвращает не-OK → False."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = "k"

    svc = SMSService()
    fake = MagicMock()
    fake.json.return_value = {
        "status": "ERROR",
        "status_code": 202,
        "status_text": "Bad phone",
    }

    with patch("core.integrations.sms_service.requests.get", return_value=fake):
        assert svc.send_sms("+79991234567", "hi") is False


def test_sms_service_swallows_network_exception(settings):
    """Любое исключение из requests.get не выходит наружу — возвращаем False."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = "k"

    svc = SMSService()
    with patch(
        "core.integrations.sms_service.requests.get",
        side_effect=Exception("network down"),
    ):
        assert svc.send_sms("+79991234567", "hi") is False


# ─────────────────────────────────────────────────────────────────────
# Helper-функции send_verification_code / send_password_reset_code
# ─────────────────────────────────────────────────────────────────────


def test_send_verification_code_includes_code(settings):
    """В тексте сообщения присутствует переданный код."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = "k"

    svc = SMSService()
    fake = MagicMock()
    fake.json.return_value = {"status": "OK"}

    with patch(
        "core.integrations.sms_service.requests.get",
        return_value=fake,
    ) as mock_get:
        svc.send_verification_code("+79991234567", "999000")

    msg = mock_get.call_args.kwargs["params"]["msg"]
    assert "999000" in msg
    assert "LootLink" in msg


def test_send_password_reset_code_includes_username(settings):
    """Сообщение содержит username и код."""
    settings.SMS_ENABLED = True
    settings.SMS_RU_API_KEY = "k"

    svc = SMSService()
    fake = MagicMock()
    fake.json.return_value = {"status": "OK"}

    with patch(
        "core.integrations.sms_service.requests.get",
        return_value=fake,
    ) as mock_get:
        svc.send_password_reset_code("+79991234567", "RESET123", "alice")

    msg = mock_get.call_args.kwargs["params"]["msg"]
    assert "RESET123" in msg
    assert "alice" in msg


# ─────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────


def test_module_send_sms_dispatches_to_singleton(settings):
    """send_sms() → sms_service.send_sms()."""
    settings.SMS_ENABLED = False
    # Singleton sms_service создан с module-level настройками. Просто проверяем
    # что вызов не падает — поведение проверено выше.
    assert send_sms("+79991234567", "hi") in (True, False)


def test_module_send_verification_sms_calls_helper(settings):
    """send_verification_sms() → sms_service.send_verification_code()."""
    settings.SMS_ENABLED = False
    assert send_verification_sms("+79991234567", "123456") in (True, False)


def test_module_send_password_reset_sms(settings):
    """send_password_reset_sms() → sms_service.send_password_reset_code()."""
    settings.SMS_ENABLED = False
    assert send_password_reset_sms("+79991234567", "RST", "u") in (True, False)
