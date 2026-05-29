"""Тесты Celery-задач core/tasks.py.

Покрывают:
- send_email_async / send_bulk_emails_async — отправка через мок send_mail
- cleanup_old_data — удаление просроченных PasswordResetCode, EmailVerification,
  прочитанных Notification
- update_user_ratings — пересчёт Profile.rating из Review (SQLite fallback)
- cleanup_security_audit_logs — удаление старых записей SecurityAuditLog
- cleanup_login_attempts — удаление старых login_failed

Все задачи запускаются синхронно благодаря CELERY_TASK_ALWAYS_EAGER из conftest.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

import pytest

from accounts.models import CustomUser, EmailVerification, PasswordResetCode, Profile
from core.models import Notification
from core.models_audit import SecurityAuditLog
from core.tasks import (
    cleanup_login_attempts,
    cleanup_old_data,
    cleanup_security_audit_logs,
    send_bulk_emails_async,
    send_email_async,
    update_user_ratings,
)

# ─────────────────────────────────────────────────────────────────────
# send_email_async
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_send_email_async_calls_send_mail():
    """Базовая отправка письма — send_mail вызывается с правильными аргументами."""
    with patch("core.tasks.send_mail") as mock:
        result = send_email_async("subject", "body", "user@example.com")

    assert mock.called
    kwargs = mock.call_args.kwargs
    assert kwargs["subject"] == "subject"
    assert kwargs["message"] == "body"
    assert kwargs["recipient_list"] == ["user@example.com"]
    assert kwargs["fail_silently"] is False
    assert "user@example.com" in result


@pytest.mark.django_db
def test_send_email_async_retries_on_failure():
    """При исключении задача должна вызвать self.retry()."""
    # eager-режим в conftest: retry превратит запуск в исключение Retry.
    with patch("core.tasks.send_mail", side_effect=RuntimeError("smtp down")):
        with pytest.raises(Exception):
            send_email_async("subject", "body", "user@example.com")


# ─────────────────────────────────────────────────────────────────────
# send_bulk_emails_async
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_send_bulk_emails_async_success():
    """Бакетная отправка письма — один вызов send_mail со списком получателей."""
    with patch("core.tasks.send_mail") as mock:
        result = send_bulk_emails_async("hi", "body", ["a@b.com", "c@d.com"])

    mock.assert_called_once()
    assert mock.call_args.kwargs["recipient_list"] == ["a@b.com", "c@d.com"]
    assert "2" in result


@pytest.mark.django_db
def test_send_bulk_emails_async_swallows_error():
    """При сбое возвращает текстовую ошибку, не выбрасывает (без retry)."""
    with patch("core.tasks.send_mail", side_effect=RuntimeError("bounce")):
        result = send_bulk_emails_async("hi", "body", ["a@b.com"])

    assert "Ошибка" in result
    assert "bounce" in result


# ─────────────────────────────────────────────────────────────────────
# cleanup_old_data
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_cleanup_old_data_removes_only_stale_rows(verified_user):
    """Старые коды / verifications / notifications удаляются, свежие — остаются."""
    now = timezone.now()

    # Один свежий + один просроченный PasswordResetCode
    fresh_code = PasswordResetCode.objects.create(
        user=verified_user,
        code="111111",
        expires_at=now + timedelta(hours=1),
    )
    old_code = PasswordResetCode.objects.create(
        user=verified_user,
        code="222222",
        expires_at=now + timedelta(hours=1),
    )
    PasswordResetCode.objects.filter(pk=old_code.pk).update(
        created_at=now - timedelta(hours=25),
    )

    # EmailVerification: одно свежее не-верифицированное + одно старое не-верифицированное
    fresh_verif = EmailVerification.objects.create(
        user=verified_user,
        token="fresh-token",  # nosec B106 — фикстура для теста, не реальный секрет
        is_verified=False,
    )
    old_verif = EmailVerification.objects.create(
        user=CustomUser.objects.create_user("ev_user", "ev@x.com", "pw"),
        token="stale-token",  # nosec B106 — фикстура для теста
        is_verified=False,
    )
    EmailVerification.objects.filter(pk=old_verif.pk).update(
        created_at=now - timedelta(days=8),
    )

    # Notification: одно прочитанное старое + одно прочитанное свежее + одно непрочитанное старое
    old_read = Notification.objects.create(
        user=verified_user,
        notification_type="info",
        title="old",
        message="old",
        is_read=True,
    )
    Notification.objects.filter(pk=old_read.pk).update(
        created_at=now - timedelta(days=31),
    )
    fresh_read = Notification.objects.create(
        user=verified_user,
        notification_type="info",
        title="fresh",
        message="fresh",
        is_read=True,
    )
    old_unread = Notification.objects.create(
        user=verified_user,
        notification_type="info",
        title="old-unread",
        message="old-unread",
        is_read=False,
    )
    Notification.objects.filter(pk=old_unread.pk).update(
        created_at=now - timedelta(days=31),
    )

    result = cleanup_old_data()

    assert result["codes_deleted"] == 1
    assert result["verifications_deleted"] == 1
    assert result["notifications_deleted"] == 1

    assert PasswordResetCode.objects.filter(pk=fresh_code.pk).exists()
    assert not PasswordResetCode.objects.filter(pk=old_code.pk).exists()

    assert EmailVerification.objects.filter(pk=fresh_verif.pk).exists()
    assert not EmailVerification.objects.filter(pk=old_verif.pk).exists()

    assert Notification.objects.filter(pk=fresh_read.pk).exists()
    assert not Notification.objects.filter(pk=old_read.pk).exists()
    # Старое НЕпрочитанное — не трогаем, его удалит retention другой задачи
    assert Notification.objects.filter(pk=old_unread.pk).exists()


# ─────────────────────────────────────────────────────────────────────
# update_user_ratings (SQLite fallback — итеративный путь)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_update_user_ratings_recomputes_from_reviews(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """Рейтинги пересчитываются из reviewed-Review (SQLite-путь)."""
    from transactions.models import Review

    # Сбрасываем рейтинг продавца в заведомо неверное значение
    seller.profile.rating = Decimal("0")
    seller.profile.save()

    listing = listing_factory(seller, status="sold")
    pr = purchase_request_factory(listing, buyer, status="completed")

    Review.objects.create(
        purchase_request=pr,
        reviewer=buyer,
        reviewed_user=seller,
        rating=5,
        comment="great",
    )

    update_user_ratings()

    seller.profile.refresh_from_db()
    assert seller.profile.rating == Decimal("5.00")


# ─────────────────────────────────────────────────────────────────────
# cleanup_security_audit_logs
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_cleanup_security_audit_logs_deletes_only_old(verified_user):
    """Удаляются только записи старше threshold."""
    now = timezone.now()
    old = SecurityAuditLog.objects.create(
        user=verified_user,
        action_type="login_success",
        risk_level="low",
        description="old",
        ip_address="127.0.0.1",
    )
    SecurityAuditLog.objects.filter(pk=old.pk).update(
        created_at=now - timedelta(days=91),
    )
    fresh = SecurityAuditLog.objects.create(
        user=verified_user,
        action_type="login_success",
        risk_level="low",
        description="fresh",
        ip_address="127.0.0.1",
    )

    result = cleanup_security_audit_logs(days=90)

    assert "1" in result
    assert not SecurityAuditLog.objects.filter(pk=old.pk).exists()
    assert SecurityAuditLog.objects.filter(pk=fresh.pk).exists()


# ─────────────────────────────────────────────────────────────────────
# cleanup_login_attempts
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_cleanup_login_attempts_only_failed_old(verified_user):
    """Удаляются только login_failed старше threshold (но не другие action_type)."""
    now = timezone.now()

    # Старый login_failed — удалится
    old_fail = SecurityAuditLog.objects.create(
        user=verified_user,
        action_type="login_failed",
        risk_level="medium",
        description="old fail",
        ip_address="127.0.0.1",
    )
    SecurityAuditLog.objects.filter(pk=old_fail.pk).update(
        created_at=now - timedelta(days=31),
    )

    # Старый login_success — НЕ должен удалиться (не login_failed)
    old_success = SecurityAuditLog.objects.create(
        user=verified_user,
        action_type="login_success",
        risk_level="low",
        description="old success",
        ip_address="127.0.0.1",
    )
    SecurityAuditLog.objects.filter(pk=old_success.pk).update(
        created_at=now - timedelta(days=31),
    )

    # Свежий login_failed — не удалится (моложе порога)
    fresh_fail = SecurityAuditLog.objects.create(
        user=verified_user,
        action_type="login_failed",
        risk_level="medium",
        description="fresh fail",
        ip_address="127.0.0.1",
    )

    result = cleanup_login_attempts(days=30)

    assert "1" in result
    assert not SecurityAuditLog.objects.filter(pk=old_fail.pk).exists()
    assert SecurityAuditLog.objects.filter(pk=old_success.pk).exists()
    assert SecurityAuditLog.objects.filter(pk=fresh_fail.pk).exists()
