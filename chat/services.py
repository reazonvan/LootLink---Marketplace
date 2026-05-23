"""
Сервисный слой `chat/`.

Здесь живёт бизнес-логика для бесед (Conversation) и сообщений (Message).

Naming: `conversation_<action>`, `message_<action>`.

См. HackSoft styleguide: https://github.com/HackSoftware/Django-Styleguide#services

ВАЖНО: этот файл создан как скелет в рамках P3 рефакторинга.
Постепенно перенесите сюда логику из `chat/views.py` и `chat/consumers.py`.
"""

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from accounts.models import CustomUser
    from chat.models import Conversation, Message
    from listings.models import Listing


@transaction.atomic
def conversation_get_or_create(
    *,
    user1: "CustomUser",
    user2: "CustomUser",
    listing: "Listing | None" = None,
) -> "Conversation":
    """
    Получить или создать беседу между двумя пользователями.

    Модель требует participant1_id < participant2_id (CheckConstraint).
    Поэтому сортируем по pk перед созданием.
    """
    from chat.models import Conversation

    p1, p2 = sorted([user1, user2], key=lambda u: u.pk)
    conversation, _created = Conversation.objects.get_or_create(
        participant1=p1,
        participant2=p2,
        listing=listing,
    )
    return conversation


def message_send(*, conversation: "Conversation", sender: "CustomUser", content: str) -> "Message":
    """
    Отправить сообщение в беседу.

    Триггерит сигнал post_save → отправляет уведомление через Channels (WebSocket).
    """
    from chat.models import Message

    return Message.objects.create(
        conversation=conversation,
        sender=sender,
        content=content,
    )
