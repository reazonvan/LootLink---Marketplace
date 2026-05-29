"""Тесты core/automoderation.py — AutoModerator (regex-фильтрация).

Покрывают:
- check_text: clean/profanity/spam/scam + правильная severity
- moderate_listing: high → cancelled, medium → ModerationQueue
- moderate_message: high → blocked, medium → warned
"""

from decimal import Decimal

import pytest

from core.automoderation import AutoModerator, auto_moderator
from core.moderation_models import AutoModeration, ModerationQueue

# ─────────────────────────────────────────────────────────────────────
# check_text
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def mod():
    return AutoModerator()


def test_check_text_clean_returns_no_violations(mod):
    """Безобидный текст проходит без violations."""
    result = mod.check_text("Продам книгу про программирование, отличное состояние.")
    assert result["is_clean"] is True
    assert result["violations"] == []
    assert result["severity"] == "low"


def test_check_text_profanity_medium(mod):
    """Мат поднимает severity до medium."""
    result = mod.check_text("это полный бляха-муха")
    assert result["is_clean"] is False
    assert result["severity"] == "medium"
    types = [v["type"] for v in result["violations"]]
    assert "profanity" in types


def test_check_text_spam_long_phone(mod):
    """Длинный номер (10+ цифр) ловится как спам."""
    result = mod.check_text("звоните 89001234567")
    assert result["is_clean"] is False
    types = [v["type"] for v in result["violations"]]
    assert "spam" in types


def test_check_text_spam_short_url(mod):
    """Короткие ссылки (bit.ly) — это спам."""
    result = mod.check_text("Зайди сюда https://bit.ly/abc123")
    types = [v["type"] for v in result["violations"]]
    assert "spam" in types


def test_check_text_scam_high_severity(mod):
    """Scam-паттерны поднимают severity до high."""
    result = mod.check_text("предоплата обязательна без обмана")
    assert result["is_clean"] is False
    assert result["severity"] == "high"
    types = [v["type"] for v in result["violations"]]
    assert "scam" in types


# ─────────────────────────────────────────────────────────────────────
# moderate_listing
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_moderate_listing_clean_approves(seller, listing_factory):
    """Чистое объявление одобряется без побочных эффектов."""
    listing = listing_factory(seller, title="Хорошая книга", description="Отличное состояние")
    result = auto_moderator.moderate_listing(listing)
    assert result == "approved"
    listing.refresh_from_db()
    assert listing.status == "active"
    assert not AutoModeration.objects.filter(content_id=listing.id).exists()


@pytest.mark.django_db
def test_moderate_listing_scam_blocks_immediately(seller, listing_factory):
    """High severity (scam) → status=cancelled, лог пишется."""
    listing = listing_factory(
        seller,
        title="продам",
        description="предоплата обязательна без обмана",
    )

    result = auto_moderator.moderate_listing(listing)

    assert result == "blocked"
    listing.refresh_from_db()
    assert listing.status == "cancelled"
    assert AutoModeration.objects.filter(
        content_type="listing",
        content_id=listing.id,
        action="block",
    ).exists()


@pytest.mark.django_db
def test_moderate_listing_profanity_flags(seller, listing_factory):
    """Medium severity (профанити) → попадает в ModerationQueue."""
    listing = listing_factory(
        seller,
        title="блять, какая хуйня",
        description="нормально",
    )

    result = auto_moderator.moderate_listing(listing)

    assert result == "flagged"
    listing.refresh_from_db()
    # status НЕ меняется на medium
    assert listing.status == "active"
    assert ModerationQueue.objects.filter(
        content_type="listing",
        content_id=listing.id,
    ).exists()


# ─────────────────────────────────────────────────────────────────────
# moderate_message
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_moderate_message_clean_approves(buyer, seller, conversation_factory, message_factory):
    """Чистое сообщение одобряется."""
    conv = conversation_factory(buyer, seller)
    msg = message_factory(conv, buyer, content="Привет, ещё актуально?")
    assert auto_moderator.moderate_message(msg) == "approved"


@pytest.mark.django_db
def test_moderate_message_scam_blocks(buyer, seller, conversation_factory, message_factory):
    """High severity сообщение блокируется."""
    conv = conversation_factory(buyer, seller)
    msg = message_factory(
        conv,
        buyer,
        content="предоплата обязательна без обмана",
    )
    assert auto_moderator.moderate_message(msg) == "blocked"


@pytest.mark.django_db
def test_moderate_message_profanity_warns(buyer, seller, conversation_factory, message_factory):
    """Medium severity сообщение → warned (не блок)."""
    conv = conversation_factory(buyer, seller)
    msg = message_factory(conv, buyer, content="бляха ну и хуйня")
    result = auto_moderator.moderate_message(msg)
    assert result == "warned"
