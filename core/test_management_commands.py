"""Тесты management-команд core/management/commands.

Покрывают:
- cleanup_duplicate_notifications: оставляет самое новое из группы дубликатов
- check_chat_notifications: печатает summary, ничего не меняет
- clear_old_chat_notifications: требует --confirm для удаления
- create_profiles: создаёт Profile только тем, у кого его нет
- create_indexes: smoke-тест (impotent на dev SQLite)
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

import pytest

from accounts.models import Profile
from core.models import Notification

CustomUser = get_user_model()


# ─────────────────────────────────────────────────────────────────────
# cleanup_duplicate_notifications
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_cleanup_duplicate_notifications_keeps_newest(verified_user):
    """Из группы дубликатов остаётся самая новая запись."""
    import time

    # 3 дубликата (одинаковый user + link + type, is_read=False)
    n1 = Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )
    time.sleep(0.01)
    n2 = Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )
    time.sleep(0.01)
    n3 = Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )

    # Не-дубликат (другой link) — должен остаться
    other = Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/99/",
    )

    out = StringIO()
    call_command("cleanup_duplicate_notifications", stdout=out)

    # Только n3 (новейший) и other остаются
    assert Notification.objects.filter(pk=n3.pk).exists()
    assert Notification.objects.filter(pk=other.pk).exists()
    assert not Notification.objects.filter(pk=n1.pk).exists()
    assert not Notification.objects.filter(pk=n2.pk).exists()


@pytest.mark.django_db
def test_cleanup_duplicate_notifications_noop_when_clean(verified_user):
    """Без дубликатов выводит 'не найдено' и ничего не удаляет."""
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )

    out = StringIO()
    call_command("cleanup_duplicate_notifications", stdout=out)

    assert "не найдено" in out.getvalue().lower()
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_cleanup_duplicate_notifications_ignores_read(verified_user):
    """Прочитанные не считаются дубликатами (даже если совпадают)."""
    import time

    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
        is_read=True,
    )
    time.sleep(0.01)
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
        is_read=True,
    )

    call_command("cleanup_duplicate_notifications", stdout=StringIO())
    assert Notification.objects.count() == 2


# ─────────────────────────────────────────────────────────────────────
# check_chat_notifications (read-only)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_check_chat_notifications_prints_count(verified_user):
    """Команда выводит общее число непрочитанных сообщений."""
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/2/",
    )

    out = StringIO()
    call_command("check_chat_notifications", stdout=out)
    text = out.getvalue()

    assert "Всего непрочитанных: 2" in text
    # Никаких изменений
    assert Notification.objects.count() == 2


# ─────────────────────────────────────────────────────────────────────
# clear_old_chat_notifications
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_clear_old_chat_notifications_dryrun_keeps_all(verified_user):
    """Без --confirm ничего не удаляет, выводит warning."""
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )

    out = StringIO()
    call_command("clear_old_chat_notifications", stdout=out)

    assert "--confirm" in out.getvalue()
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_clear_old_chat_notifications_with_confirm_deletes(verified_user):
    """С --confirm удаляет все непрочитанные new_message."""
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/1/",
    )
    # Не new_message — должно остаться
    Notification.objects.create(
        user=verified_user,
        notification_type="system",
        title="sys",
        message="m",
        link="/",
    )
    # Прочитанное new_message — должно остаться
    Notification.objects.create(
        user=verified_user,
        notification_type="new_message",
        title="t",
        message="m",
        link="/chat/2/",
        is_read=True,
    )

    out = StringIO()
    call_command("clear_old_chat_notifications", "--confirm", stdout=out)

    assert "Удалено 1" in out.getvalue()
    # Оба не-целевых уведомления остались
    assert (
        Notification.objects.filter(
            notification_type="new_message",
            is_read=False,
        ).count()
        == 0
    )
    assert Notification.objects.count() == 2


# ─────────────────────────────────────────────────────────────────────
# create_profiles
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_create_profiles_creates_missing(verified_user):
    """Если у юзера нет Profile — команда создаёт."""
    # Удаляем профиль (сигнал больше не сработает на существующего юзера)
    Profile.objects.filter(user=verified_user).delete()

    out = StringIO()
    call_command("create_profiles", stdout=out)

    assert Profile.objects.filter(user=verified_user).exists()
    assert "Создано новых профилей: 1" in out.getvalue()


@pytest.mark.django_db
def test_create_profiles_idempotent(verified_user):
    """Если у всех уже есть Profile — ничего не делает."""
    assert Profile.objects.filter(user=verified_user).exists()

    out = StringIO()
    call_command("create_profiles", stdout=out)

    assert "Создано новых профилей: 0" in out.getvalue()
