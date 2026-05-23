"""
Селекторы для `chat/` — слой чтения.

См. HackSoft styleguide: https://github.com/HackSoftware/Django-Styleguide#selectors
"""

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

if TYPE_CHECKING:
    from accounts.models import CustomUser
    from chat.models import Conversation, Message


def conversation_list_for_user(*, user: "CustomUser") -> "QuerySet[Conversation]":
    """Список бесед пользователя с подгруженными участниками и listing."""
    from chat.models import Conversation

    return (
        Conversation.objects.filter(Q(participant1=user) | Q(participant2=user))
        .select_related("participant1", "participant2", "listing")
        .order_by("-updated_at")
    )


def message_list_for_conversation(
    *, conversation: "Conversation", limit: int = 50
) -> "QuerySet[Message]":
    """Последние сообщения в беседе с подгруженным sender."""
    from chat.models import Message

    return (
        Message.objects.filter(conversation=conversation)
        .select_related("sender")
        .order_by("-created_at")[:limit]
    )
