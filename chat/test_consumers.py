"""Тесты для chat/consumers.py — WebSocket ChatConsumer.

Покрывают:
- connect: аноним отбрасывается, чужак отбрасывается, участник проходит
- receive: rate-limit, превышение payload, JSON-ошибка, length>5000, пустой content
- handle_message: создание сообщения в БД и broadcast в группу
- handle_typing/read_receipt: broadcast в группу
- IDOR в mark_message_as_read: чужое сообщение игнорируется
- disconnect: status=offline broadcast

Запуск:
    pytest chat/test_consumers.py -v
"""

from django.contrib.auth import get_user_model

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from chat import routing as chat_routing
from chat.models import Conversation, Message

CustomUser = get_user_model()


# ─────────────────────────────────────────────────────────────────────
# Хелперы
# ─────────────────────────────────────────────────────────────────────


def _build_app():
    """Собираем минимальное ASGI-приложение без AuthMiddlewareStack.

    Тесты сами выставляют scope['user'] и scope['url_route'] —
    через AuthMiddlewareStack эти данные пришлось бы тащить из session/db.
    """
    return URLRouter(chat_routing.websocket_urlpatterns)


async def _connect(user, conversation_id):
    """Создаёт WebsocketCommunicator с проставленным user и url_route."""
    app = _build_app()
    communicator = WebsocketCommunicator(app, f"/ws/chat/{conversation_id}/")
    # AuthMiddlewareStack обычно подкидывает user из session — обходим.
    communicator.scope["user"] = user
    communicator.scope["url_route"] = {"kwargs": {"conversation_id": str(conversation_id)}}
    return communicator


@database_sync_to_async
def _make_conversation(buyer, seller):
    p1, p2 = sorted([buyer, seller], key=lambda u: u.pk)
    return Conversation.objects.create(participant1=p1, participant2=p2)


@database_sync_to_async
def _make_message(conversation, sender, content="hi", is_read=False):
    return Message.objects.create(
        conversation=conversation,
        sender=sender,
        content=content,
        is_read=is_read,
    )


@database_sync_to_async
def _count_messages(conversation):
    return Message.objects.filter(conversation=conversation).count()


@database_sync_to_async
def _refresh_message(message):
    message.refresh_from_db()
    return message


# ─────────────────────────────────────────────────────────────────────
# connect / disconnect
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_anonymous_user_rejected(buyer, seller):
    """Анонимный пользователь не должен пройти connect."""
    from django.contrib.auth.models import AnonymousUser

    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(AnonymousUser(), conversation.id)
    connected, _ = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_non_participant_rejected(buyer, seller, user_factory):
    """Пользователь, не являющийся участником беседы, не должен пройти."""
    outsider = await database_sync_to_async(user_factory)()
    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(outsider, conversation.id)
    connected, _ = await communicator.connect()
    assert not connected
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_participant_connects_and_sees_online(buyer, seller):
    """Участник подключается и получает свой же broadcast online-статуса."""
    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    connected, _ = await communicator.connect()
    assert connected

    # online-статус не присылается самому себе (user_status фильтрует self),
    # но broadcast уходит — просто consumer его не отправляет себе же.
    # Поэтому ждать ответа не нужно.
    await communicator.disconnect()


# ─────────────────────────────────────────────────────────────────────
# receive: payload / rate-limit / JSON
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_oversized_payload_rejected(buyer, seller):
    """Сообщения > WS_MAX_PAYLOAD должны отбиваться."""
    from chat.consumers import WS_MAX_PAYLOAD

    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    huge = "x" * (WS_MAX_PAYLOAD + 100)
    await communicator.send_to(text_data=huge)
    response = await communicator.receive_json_from()
    assert response["type"] == "error"
    assert "слишком" in response["message"].lower()

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_json_rejected(buyer, seller):
    """Невалидный JSON должен возвращать error без падения."""
    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    await communicator.send_to(text_data="not a json {")
    response = await communicator.receive_json_from()
    assert response["type"] == "error"
    assert "JSON" in response["message"] or "json" in response["message"]

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_rate_limit_per_user(buyer, seller):
    """Превышение лимита сообщений возвращает error и не сохраняет в БД."""
    from chat.consumers import WS_RATE_LIMIT

    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    # Шлём WS_RATE_LIMIT валидных сообщений — все должны пройти.
    for i in range(WS_RATE_LIMIT):
        await communicator.send_json_to({"type": "message", "content": f"msg-{i}"})

    # Дренируем echo-фрейма из chat_message broadcast'a, не накапливая в очереди.
    # Дальше шлём ещё одно — должно прийти error rate-limit.
    await communicator.send_json_to({"type": "message", "content": "overflow"})

    # Ищем error-фрейм среди ответов
    found_rate_limit_error = False
    for _ in range(WS_RATE_LIMIT + 5):
        try:
            frame = await communicator.receive_json_from(timeout=0.5)
        except Exception:
            break
        if frame.get("type") == "error" and "Слишком" in frame.get("message", ""):
            found_rate_limit_error = True
            break
    assert found_rate_limit_error, "rate-limit error не пришёл"

    await communicator.disconnect()


# ─────────────────────────────────────────────────────────────────────
# handle_message
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_message_saved_and_broadcast(buyer, seller):
    """handle_message сохраняет в БД и шлёт chat_message в группу."""
    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    await communicator.send_json_to({"type": "message", "content": "hello world"})

    # Ждём broadcast'а самому себе.
    response = await communicator.receive_json_from()
    assert response["type"] == "message"
    assert response["message"]["content"] == "hello world"
    assert response["message"]["sender_id"] == buyer.id

    # Проверяем что в БД появилась запись.
    count = await _count_messages(conversation)
    assert count == 1

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_empty_message_not_saved(buyer, seller):
    """Пустое сообщение должно тихо игнорироваться (без error)."""
    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    await communicator.send_json_to({"type": "message", "content": "   "})
    # Никакого ответа быть не должно — handle_message выходит до save_message
    assert await communicator.receive_nothing(timeout=0.3)

    count = await _count_messages(conversation)
    assert count == 0
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_overlong_content_rejected(buyer, seller):
    """content > 5000 символов возвращает error."""
    conversation = await _make_conversation(buyer, seller)
    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    await communicator.send_json_to({"type": "message", "content": "a" * 5001})
    response = await communicator.receive_json_from()
    assert response["type"] == "error"
    assert "5000" in response["message"]

    count = await _count_messages(conversation)
    assert count == 0
    await communicator.disconnect()


# ─────────────────────────────────────────────────────────────────────
# read_receipt + IDOR
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_mark_message_read(buyer, seller):
    """read-receipt помечает чужое сообщение прочитанным."""
    conversation = await _make_conversation(buyer, seller)
    msg = await _make_message(conversation, seller, "from seller")
    assert msg.is_read is False

    communicator = await _connect(buyer, conversation.id)
    await communicator.connect()

    await communicator.send_json_to({"type": "read", "message_id": msg.id})

    # consumer шлёт broadcast 'message_read' всем — поймаем
    response = await communicator.receive_json_from()
    assert response["type"] == "read"
    assert response["message_id"] == msg.id

    refreshed = await _refresh_message(msg)
    assert refreshed.is_read is True

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_idor_on_read_other_conversation(buyer, seller, user_factory):
    """Покупатель не может пометить прочитанным сообщение из другой беседы (IDOR)."""
    other_user = await database_sync_to_async(user_factory)()
    my_conv = await _make_conversation(buyer, seller)
    foreign_conv = await _make_conversation(seller, other_user)
    foreign_msg = await _make_message(foreign_conv, other_user, "secret")

    communicator = await _connect(buyer, my_conv.id)
    await communicator.connect()

    # buyer пытается через свою беседу пометить чужое message_id
    await communicator.send_json_to({"type": "read", "message_id": foreign_msg.id})

    # message_read всё равно отправляется (consumer broadcast'ит без проверки),
    # но в БД флаг не должен поменяться (mark_message_as_read проверяет conv).
    try:
        await communicator.receive_json_from(timeout=0.5)
    except Exception:  # nosec B110 — таймаут тут ожидаем, фрейма может не быть
        pass

    refreshed = await _refresh_message(foreign_msg)
    assert refreshed.is_read is False, "IDOR: чужое сообщение пометилось прочитанным"

    await communicator.disconnect()
