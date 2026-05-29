"""Тесты для chat/selectors.py — слой чтения."""

import pytest

from chat.selectors import conversation_list_for_user, message_list_for_conversation


@pytest.mark.django_db
def test_conversation_list_for_user_includes_both_roles(
    buyer,
    seller,
    user_factory,
    conversation_factory,
):
    """Возвращает беседы где user — participant1 ИЛИ participant2."""
    third = user_factory()
    conv1 = conversation_factory(buyer, seller)
    conv2 = conversation_factory(buyer, third)
    # Беседа без buyer — не должна попасть
    foreign = conversation_factory(seller, third)

    pks = set(conversation_list_for_user(user=buyer).values_list("pk", flat=True))

    assert {conv1.pk, conv2.pk} <= pks
    assert foreign.pk not in pks


@pytest.mark.django_db
def test_conversation_list_orders_by_updated_at_desc(
    buyer,
    seller,
    user_factory,
    conversation_factory,
):
    """Сортировка по -updated_at."""
    import time

    third = user_factory()
    older = conversation_factory(buyer, seller)
    time.sleep(0.01)
    newer = conversation_factory(buyer, third)

    pks = list(conversation_list_for_user(user=buyer).values_list("pk", flat=True))

    assert pks.index(newer.pk) < pks.index(older.pk)


@pytest.mark.django_db
def test_message_list_for_conversation_limits_results(
    buyer,
    seller,
    conversation_factory,
    message_factory,
):
    """Возвращает не более limit последних сообщений."""
    conv = conversation_factory(buyer, seller)
    for i in range(60):
        message_factory(conv, buyer, content=f"msg-{i}")

    qs = message_list_for_conversation(conversation=conv, limit=20)
    assert len(list(qs)) == 20
