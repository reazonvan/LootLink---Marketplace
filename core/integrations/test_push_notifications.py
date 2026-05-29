"""Тесты core/integrations/push_notifications.py — WebPushService."""

from unittest.mock import MagicMock, patch

import pytest

from core.integrations.push_notifications import WebPushService


def test_web_push_service_disabled_without_vapid_keys(settings):
    """Без VAPID-ключей сервис disabled и send_notification возвращает False."""
    settings.VAPID_PRIVATE_KEY = ""
    settings.VAPID_PUBLIC_KEY = ""

    svc = WebPushService()
    assert svc.enabled is False
    assert svc.send_notification({"endpoint": "x"}, "t", "b") is False


def test_web_push_service_returns_false_without_subscription(settings):
    """Даже включённый сервис возвращает False при пустом subscription_info."""
    settings.VAPID_PRIVATE_KEY = "priv"
    settings.VAPID_PUBLIC_KEY = "pub"

    svc = WebPushService()
    # enabled может быть False если pywebpush не установлен — но даже
    # если включён, без subscription отдаёт False
    assert svc.send_notification(None, "t", "b") is False
    assert svc.send_notification({}, "t", "b") is False


def test_web_push_service_send_calls_webpush(settings):
    """Когда всё на месте — вызывает self.webpush с переданными аргументами."""
    settings.VAPID_PRIVATE_KEY = "priv"
    settings.VAPID_PUBLIC_KEY = "pub"
    settings.VAPID_CLAIMS = {"sub": "mailto:test@x.io"}

    svc = WebPushService()
    if not svc.enabled:
        pytest.skip("pywebpush not installed in test env")

    mock_webpush = MagicMock()
    svc.webpush = mock_webpush

    sub = {"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "k", "auth": "a"}}
    result = svc.send_notification(sub, "Hi", "Body", icon="/x.png", url="/page")

    assert result is True
    mock_webpush.assert_called_once()
    kwargs = mock_webpush.call_args.kwargs
    assert kwargs["subscription_info"] == sub
    assert "Hi" in kwargs["data"]
    assert "Body" in kwargs["data"]
    assert kwargs["vapid_private_key"] == "priv"


def test_web_push_service_send_swallows_exception(settings):
    """Если webpush бросает — возвращаем False, не пропускаем исключение наружу."""
    settings.VAPID_PRIVATE_KEY = "priv"
    settings.VAPID_PUBLIC_KEY = "pub"

    svc = WebPushService()
    if not svc.enabled:
        pytest.skip("pywebpush not installed in test env")

    svc.webpush = MagicMock(side_effect=RuntimeError("FCM down"))

    result = svc.send_notification({"endpoint": "x"}, "t", "b")
    assert result is False


def test_web_push_service_uses_default_icon_and_url(settings):
    """Без icon/url проставляются дефолтные значения."""
    settings.VAPID_PRIVATE_KEY = "priv"
    settings.VAPID_PUBLIC_KEY = "pub"

    svc = WebPushService()
    if not svc.enabled:
        pytest.skip("pywebpush not installed in test env")

    svc.webpush = MagicMock()
    svc.send_notification({"endpoint": "x"}, "t", "b")

    data_str = svc.webpush.call_args.kwargs["data"]
    assert "/static/favicon.svg" in data_str
    assert "/" in data_str  # default url
