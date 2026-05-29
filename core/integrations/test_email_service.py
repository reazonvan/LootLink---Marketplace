"""Тесты core/integrations/email_service.py — EmailService.

Покрывают:
- _send_email: console backend → False, SMTP success/auth/SMTPException → fallback,
  HTML alternative, anti-spam headers, reply_to
- send_password_reset_email / send_verification_email / send_no_account_email:
  правильная тема, получатель, тело
- test_email_configuration: возвращает диагностический dict
"""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from core.integrations.email_service import EmailService

# ─────────────────────────────────────────────────────────────────────
# _send_email — поведение бэкенда
# ─────────────────────────────────────────────────────────────────────


def test_send_email_returns_false_with_console_backend(settings, capsys):
    """Console-backend → возвращает False, печатает email в stdout."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

    result = EmailService._send_email(
        subject="hi",
        message="body",
        recipient_list=["u@x.com"],
        fail_silently=True,
    )

    assert result is False


def test_send_email_returns_true_on_smtp_success(settings):
    """При успешной отправке возвращает True."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.SUPPORT_EMAIL = "support@x.io"
    settings.DEFAULT_FROM_EMAIL = "no-reply@x.io"

    with patch(
        "core.integrations.email_service.EmailMultiAlternatives",
    ) as mock_cls:
        mock_email = MagicMock()
        mock_email.extra_headers = {}
        mock_cls.return_value = mock_email

        result = EmailService._send_email(
            subject="hi",
            message="body",
            recipient_list=["u@x.com"],
        )

    assert result is True
    mock_email.send.assert_called_once()


def test_send_email_attaches_html_alternative(settings):
    """html_message → attach_alternative('text/html')."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch(
        "core.integrations.email_service.EmailMultiAlternatives",
    ) as mock_cls:
        mock_email = MagicMock()
        mock_email.extra_headers = {}
        mock_cls.return_value = mock_email

        EmailService._send_email(
            subject="hi",
            message="text",
            html_message="<p>html</p>",
            recipient_list=["u@x.com"],
        )

    mock_email.attach_alternative.assert_called_once_with("<p>html</p>", "text/html")


def test_send_email_sets_anti_spam_headers(settings):
    """List-Unsubscribe и X-Mailer заголовки выставляются."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.SUPPORT_EMAIL = "support@x.io"

    with patch(
        "core.integrations.email_service.EmailMultiAlternatives",
    ) as mock_cls:
        mock_email = MagicMock()
        mock_email.extra_headers = {}
        mock_cls.return_value = mock_email

        EmailService._send_email(
            subject="hi",
            message="text",
            recipient_list=["u@x.com"],
        )

    assert "List-Unsubscribe" in mock_email.extra_headers
    assert "support@x.io" in mock_email.extra_headers["List-Unsubscribe"]
    assert mock_email.extra_headers["X-Mailer"] == "LootLink/1.0"


def test_send_email_swallows_auth_error_when_fail_silent(settings):
    """SMTPAuthenticationError при fail_silently=True → False, без raise."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch(
        "core.integrations.email_service.EmailMultiAlternatives",
    ) as mock_cls:
        mock_email = MagicMock()
        mock_email.extra_headers = {}
        mock_email.send.side_effect = smtplib.SMTPAuthenticationError(535, "bad")
        mock_cls.return_value = mock_email

        result = EmailService._send_email(
            subject="hi",
            message="text",
            recipient_list=["u@x.com"],
            fail_silently=True,
        )

    assert result is False


def test_send_email_raises_auth_error_when_not_silent(settings):
    """SMTPAuthenticationError при fail_silently=False → исключение наружу."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch(
        "core.integrations.email_service.EmailMultiAlternatives",
    ) as mock_cls:
        mock_email = MagicMock()
        mock_email.extra_headers = {}
        mock_email.send.side_effect = smtplib.SMTPAuthenticationError(535, "bad")
        mock_cls.return_value = mock_email

        with pytest.raises(smtplib.SMTPAuthenticationError):
            EmailService._send_email(
                subject="hi",
                message="text",
                recipient_list=["u@x.com"],
                fail_silently=False,
            )


def test_send_email_smtp_exception_tries_fallback(settings):
    """SMTPException → _try_alternative_providers (сейчас просто False)."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch(
        "core.integrations.email_service.EmailMultiAlternatives",
    ) as mock_cls:
        mock_email = MagicMock()
        mock_email.extra_headers = {}
        mock_email.send.side_effect = smtplib.SMTPException("conn lost")
        mock_cls.return_value = mock_email

        result = EmailService._send_email(
            subject="hi",
            message="text",
            recipient_list=["u@x.com"],
            fail_silently=True,
        )

    # Fallback пока не настроен — возвращает False
    assert result is False


# ─────────────────────────────────────────────────────────────────────
# send_password_reset_email
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_send_password_reset_email_sends_to_user(verified_user, settings):
    """Письмо уходит на user.email с правильной темой и кодом в теле."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch.object(EmailService, "_send_email", return_value=True) as mock_send:
        result = EmailService.send_password_reset_email(verified_user, "ABC12345")

    assert result is True
    kwargs = mock_send.call_args.kwargs
    assert kwargs["recipient_list"] == [verified_user.email]
    assert "сброс" in kwargs["subject"].lower() or "пароля" in kwargs["subject"].lower()
    # Код виден в plain-text и HTML
    assert "ABC12345" in kwargs["message"]
    assert "ABC12345" in kwargs["html_message"]


# ─────────────────────────────────────────────────────────────────────
# send_verification_email
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_send_verification_email_builds_url(verified_user, settings):
    """В тело письма попадает ссылка верификации с токеном."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.SITE_URL = "https://lootlink.test"
    settings.DEBUG = False

    with patch.object(EmailService, "_send_email", return_value=True) as mock_send:
        EmailService.send_verification_email(verified_user, "verify-token-xyz")

    kwargs = mock_send.call_args.kwargs
    # URL должен присутствовать в plain-text
    assert "verify-token-xyz" in kwargs["message"]
    assert "lootlink.test" in kwargs["message"]


# ─────────────────────────────────────────────────────────────────────
# send_no_account_email
# ─────────────────────────────────────────────────────────────────────


def test_send_no_account_email_uses_fail_silently(settings):
    """Письмо отсутствующему аккаунту шлётся в fail_silently=True (без раскрытия)."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    with patch.object(EmailService, "_send_email", return_value=True) as mock_send:
        EmailService.send_no_account_email("nobody@x.com")

    kwargs = mock_send.call_args.kwargs
    assert kwargs["fail_silently"] is True
    assert kwargs["recipient_list"] == ["nobody@x.com"]


# ─────────────────────────────────────────────────────────────────────
# test_email_configuration (smoke)
# ─────────────────────────────────────────────────────────────────────


def test_test_email_configuration_returns_diagnostics(settings):
    """test_email_configuration возвращает dict с настройками SMTP и результатом."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "smtp.x.io"
    settings.EMAIL_PORT = 587
    settings.EMAIL_USE_TLS = True
    settings.EMAIL_HOST_USER = "u@x.io"
    settings.DEFAULT_FROM_EMAIL = "u@x.io"

    with patch("core.integrations.email_service.send_mail", return_value=1):
        result = EmailService.test_email_configuration()

    assert result["backend"] == "django.core.mail.backends.smtp.EmailBackend"
    assert result["host"] == "smtp.x.io"
    assert result["port"] == 587
    assert result["use_tls"] is True
