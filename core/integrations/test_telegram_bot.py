"""Тесты core/integrations/telegram_bot.py.

Покрывают:
- send_telegram_async (Celery): пустой chat_id / нет токена / успешная отправка /
  TelegramError → retry
- TelegramNotificationService.send_message: enabled-флаг, очередь Celery
- notify_*: учёт profile.telegram_chat_id и telegram_notifications
"""

from unittest.mock import MagicMock, patch

import pytest

from core.integrations.telegram_bot import TelegramNotificationService, send_telegram_async

# ─────────────────────────────────────────────────────────────────────
# send_telegram_async (Celery task)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_send_telegram_async_returns_when_no_chat_id():
    """Пустой chat_id — выход без сетевого вызова."""
    with patch("core.integrations.telegram_bot._get_bot") as mock_bot:
        send_telegram_async(chat_id="", text="hi")
    mock_bot.assert_not_called()


@pytest.mark.django_db
def test_send_telegram_async_silent_without_token():
    """Если _get_bot вернул None (нет токена) — тихо выходит."""
    with patch("core.integrations.telegram_bot._get_bot", return_value=None):
        # Не должно поднимать
        send_telegram_async(chat_id="123", text="hi")


@pytest.mark.django_db
def test_send_telegram_async_sends_via_bot():
    """При настроенном боте вызывает bot.send_message с правильными аргументами."""
    mock_bot = MagicMock()
    with patch("core.integrations.telegram_bot._get_bot", return_value=mock_bot):
        send_telegram_async(chat_id="42", text="hello", parse_mode="HTML")

    mock_bot.send_message.assert_called_once()
    kwargs = mock_bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == "42"
    assert kwargs["text"] == "hello"
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.django_db
def test_send_telegram_async_retries_on_telegram_error():
    """TelegramError → self.retry(exc=...)."""
    from telegram.error import TelegramError

    mock_bot = MagicMock()
    mock_bot.send_message.side_effect = TelegramError("API down")

    with patch("core.integrations.telegram_bot._get_bot", return_value=mock_bot):
        # eager-режим: retry превратится в исключение
        with pytest.raises(Exception):
            send_telegram_async(chat_id="42", text="x")


# ─────────────────────────────────────────────────────────────────────
# TelegramNotificationService.send_message
# ─────────────────────────────────────────────────────────────────────


def test_send_message_returns_false_when_disabled(settings):
    """Без токена сервис помечает себя disabled и возвращает False."""
    settings.TELEGRAM_BOT_TOKEN = ""
    svc = TelegramNotificationService()
    assert svc.enabled is False
    assert svc.send_message("42", "x") is False


def test_send_message_returns_false_for_empty_chat(settings):
    """Пустой chat_id — False даже если включено."""
    settings.TELEGRAM_BOT_TOKEN = "abc"
    svc = TelegramNotificationService()
    assert svc.send_message("", "x") is False


@pytest.mark.django_db(transaction=True)
def test_send_message_enqueues_when_enabled(settings):
    """Включённый сервис кладёт задачу через _enqueue_telegram (on_commit → delay)."""
    settings.TELEGRAM_BOT_TOKEN = "abc"
    svc = TelegramNotificationService()

    with patch("core.integrations.telegram_bot.send_telegram_async.delay") as mock_delay:
        result = svc.send_message("42", "hi")

    assert result is True
    # on_commit вне atomic срабатывает сразу
    assert mock_delay.called


# ─────────────────────────────────────────────────────────────────────
# notify_* helpers (проверка respect of preferences)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_notify_new_message_skipped_without_chat_id(verified_user, settings):
    """telegram_chat_id пустой → False, ничего не шлём."""
    settings.TELEGRAM_BOT_TOKEN = "abc"
    verified_user.profile.telegram_chat_id = ""
    verified_user.profile.telegram_notifications = True
    verified_user.profile.save()

    svc = TelegramNotificationService()
    with patch("core.integrations.telegram_bot.send_telegram_async.delay") as mock_delay:
        assert svc.notify_new_message(verified_user, "sender") is False
    assert not mock_delay.called


@pytest.mark.django_db
def test_notify_new_message_skipped_when_pref_off(verified_user, settings):
    """telegram_notifications=False → False, ничего не шлём."""
    settings.TELEGRAM_BOT_TOKEN = "abc"
    verified_user.profile.telegram_chat_id = "42"
    verified_user.profile.telegram_notifications = False
    verified_user.profile.save()

    svc = TelegramNotificationService()
    with patch("core.integrations.telegram_bot.send_telegram_async.delay") as mock_delay:
        assert svc.notify_new_message(verified_user, "sender") is False
    assert not mock_delay.called


@pytest.mark.django_db(transaction=True)
def test_notify_new_message_enqueues_with_both(verified_user, settings):
    """chat_id + pref=True → задача в очереди + True."""
    settings.TELEGRAM_BOT_TOKEN = "abc"
    verified_user.profile.telegram_chat_id = "42"
    verified_user.profile.telegram_notifications = True
    verified_user.profile.save()

    svc = TelegramNotificationService()
    with patch("core.integrations.telegram_bot.send_telegram_async.delay") as mock_delay:
        assert svc.notify_new_message(verified_user, "alice") is True
    mock_delay.assert_called_once()
    text = mock_delay.call_args.args[1]
    assert "alice" in text


@pytest.mark.django_db(transaction=True)
def test_notify_price_change_uses_direction_label(verified_user, settings):
    """Подъём цены → 'повышена', снижение → 'снижена'."""
    settings.TELEGRAM_BOT_TOKEN = "abc"
    verified_user.profile.telegram_chat_id = "42"
    verified_user.profile.telegram_notifications = True
    verified_user.profile.save()

    svc = TelegramNotificationService()
    with patch("core.integrations.telegram_bot.send_telegram_async.delay") as mock_delay:
        svc.notify_price_change(verified_user, "Меч", 100, 80)
        svc.notify_price_change(verified_user, "Меч", 100, 150)

    assert mock_delay.call_count == 2
    first_text = mock_delay.call_args_list[0].args[1]
    second_text = mock_delay.call_args_list[1].args[1]
    assert "снижена" in first_text
    assert "повышена" in second_text
