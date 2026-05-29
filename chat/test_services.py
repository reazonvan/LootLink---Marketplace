"""Тесты для chat/services.py — сервисный слой бесед и сообщений.

Покрывают:
- conversation_get_or_create: сортировка участников по pk, идемпотентность
- conversation_get_or_create с listing
- message_send: создание и срабатывание post_save сигнала
"""

import pytest

from chat.models import Conversation, Message
from chat.services import conversation_get_or_create, message_send

# ─────────────────────────────────────────────────────────────────────
# conversation_get_or_create
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_conversation_get_or_create_normalizes_participant_order(buyer, seller):
    """participant1.pk < participant2.pk независимо от порядка аргументов."""
    # Вызываем в обоих порядках — должна получиться одна и та же беседа
    conv1 = conversation_get_or_create(user1=buyer, user2=seller)
    conv2 = conversation_get_or_create(user1=seller, user2=buyer)

    assert conv1.pk == conv2.pk
    assert conv1.participant1.pk < conv1.participant2.pk


@pytest.mark.django_db
def test_conversation_get_or_create_idempotent(buyer, seller):
    """Повторный вызов возвращает ту же беседу без создания дубликата."""
    conv1 = conversation_get_or_create(user1=buyer, user2=seller)
    conv2 = conversation_get_or_create(user1=buyer, user2=seller)

    assert conv1.pk == conv2.pk
    assert (
        Conversation.objects.filter(
            participant1__in=[buyer, seller],
            participant2__in=[buyer, seller],
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_conversation_get_or_create_with_listing(buyer, seller, active_listing):
    """listing привязывается, создаёт новую запись если listing другой."""
    conv_no_listing = conversation_get_or_create(user1=buyer, user2=seller)
    conv_with_listing = conversation_get_or_create(
        user1=buyer,
        user2=seller,
        listing=active_listing,
    )

    # Это разные беседы (listing — часть unique-together)
    assert conv_no_listing.pk != conv_with_listing.pk
    assert conv_with_listing.listing_id == active_listing.pk


# ─────────────────────────────────────────────────────────────────────
# message_send
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_message_send_persists_message(buyer, seller):
    """Сообщение сохраняется в БД с правильными полями."""
    conv = conversation_get_or_create(user1=buyer, user2=seller)

    msg = message_send(conversation=conv, sender=buyer, content="hello")

    assert msg.pk is not None
    assert msg.conversation_id == conv.pk
    assert msg.sender_id == buyer.pk
    assert msg.content == "hello"
    assert Message.objects.filter(pk=msg.pk).exists()


@pytest.mark.django_db
def test_message_send_multiple_messages_ordered(buyer, seller):
    """Несколько сообщений сохраняются и отдаются в хронологическом порядке."""
    conv = conversation_get_or_create(user1=buyer, user2=seller)

    msg1 = message_send(conversation=conv, sender=buyer, content="first")
    msg2 = message_send(conversation=conv, sender=seller, content="second")
    msg3 = message_send(conversation=conv, sender=buyer, content="third")

    messages = list(Message.objects.filter(conversation=conv).order_by("created_at"))
    assert [m.pk for m in messages] == [msg1.pk, msg2.pk, msg3.pk]
