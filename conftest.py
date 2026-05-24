"""
Корневые pytest-fixtures для всего проекта.

Предоставляет общие объекты для всех тестов:
- Пользователи (verified_user, unverified_user, seller, buyer)
- Клиенты (authenticated_client)
- Листинги (game, active_listing, sold_listing, listing_factory, game_factory)
- Чат (conversation_factory, message_factory)
- Транзакции (purchase_request_factory)
- Автоочистка cache (защита от rate-limit между тестами)

Username/email/phone всех фикстур специально не пересекаются с явными
значениями в accounts/tests.py (testuser / test@example.com / +7 (999) 123-45-67).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache

import pytest

CustomUser = get_user_model()


# ─────────────────────────────────────────────────────────────────────
# Инфраструктура
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_cache():
    """Очищаем cache перед каждым тестом — чтобы rate-limit не переносился."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _celery_eager(settings):
    """
    Celery в тестах работает синхронно (eager-режим), без брокера.
    Без этого .delay() пытается соединиться с Redis и тесты зависают.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


# ─────────────────────────────────────────────────────────────────────
# Пользователи
# ─────────────────────────────────────────────────────────────────────


def _make_user(username, *, email=None, phone=None, verified=True, password="testpass123"):
    """Создаёт пользователя с профилем. Профиль создаётся сигналом post_save."""
    user = CustomUser.objects.create_user(
        username=username,
        email=email or f"{username}@fixture.local",
        password=password,
    )
    # Profile создаётся сигналом; обновляем его поля
    profile = user.profile
    if phone:
        profile.phone = phone
    profile.is_verified = verified
    profile.save()
    return user


@pytest.fixture
def verified_user(db):
    """Основной пользователь, под которым логинится authenticated_client."""
    return _make_user("fixt_verified", phone="+70000000001", verified=True)


@pytest.fixture
def unverified_user(db):
    """Пользователь без верификации."""
    return _make_user("fixt_unverified", phone="+70000000002", verified=False)


@pytest.fixture
def seller(db):
    """Продавец. Отличается от verified_user."""
    return _make_user("fixt_seller", phone="+70000000003", verified=True)


@pytest.fixture
def buyer(db):
    """Покупатель. Отличается от seller и verified_user."""
    return _make_user("fixt_buyer", phone="+70000000004", verified=True)


@pytest.fixture
def user_factory(db):
    """
    Фабрика пользователей. Каждое обращение создаёт уникального пользователя.
    Username и email можно переопределить, остальное — дефолты с автоинкрементом
    телефона, чтобы не пересекаться с другими фикстурами.
    """
    counter = {"n": 0}

    def make(username=None, email=None, phone=None, verified=True, password="testpass123"):
        counter["n"] += 1
        username = username or f'fixt_factory_{counter["n"]}'
        email = email or f"{username}@fixture.local"
        phone = phone or f'+7100000{counter["n"]:04d}'
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        profile = user.profile
        profile.phone = phone
        profile.is_verified = verified
        profile.save()
        return user

    return make


# ─────────────────────────────────────────────────────────────────────
# Клиенты
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def authenticated_client(client, verified_user):
    """Django test client, залогинен под verified_user."""
    client.force_login(verified_user)
    return client


# ─────────────────────────────────────────────────────────────────────
# Игры и листинги
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def game(db):
    """Активная игра по умолчанию."""
    from listings.models import Game

    return Game.objects.create(name="Fixture Game", slug="fixture-game")


@pytest.fixture
def game_factory(db):
    """Фабрика игр. Каждое обращение создаёт уникальную игру."""
    from listings.models import Game

    counter = {"n": 0}

    def make(name=None, **kwargs):
        counter["n"] += 1
        name = name or f'Fixture Game {counter["n"]}'
        slug = kwargs.pop("slug", None) or f'fixture-game-{counter["n"]}'
        return Game.objects.create(name=name, slug=slug, **kwargs)

    return make


@pytest.fixture
def listing_factory(db, game):
    """
    Фабрика объявлений.
    Дефолтные значения: game=game fixture, status='active', price=100.
    """
    from listings.models import Listing

    counter = {"n": 0}

    def make(seller, **overrides):
        counter["n"] += 1
        defaults = {
            "seller": seller,
            "game": game,
            "title": f'Fixture Listing {counter["n"]}',
            "description": "Fixture description",
            "price": Decimal("100.00"),
            "status": "active",
        }
        defaults.update(overrides)
        return Listing.objects.create(**defaults)

    return make


@pytest.fixture
def active_listing(listing_factory, seller):
    """Активное объявление, принадлежит seller."""
    return listing_factory(seller, title="Active Fixture Listing")


@pytest.fixture
def sold_listing(listing_factory, seller):
    """Проданное объявление, принадлежит seller."""
    return listing_factory(seller, title="Sold Fixture Listing", status="sold")


# ─────────────────────────────────────────────────────────────────────
# Чат
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def conversation_factory(db):
    """
    Фабрика бесед.
    Сортирует участников по pk — модель требует participant1_id < participant2_id
    (CheckConstraint).
    """
    from chat.models import Conversation

    def make(user1, user2, listing=None):
        p1, p2 = sorted([user1, user2], key=lambda u: u.pk)
        return Conversation.objects.create(
            participant1=p1,
            participant2=p2,
            listing=listing,
        )

    return make


@pytest.fixture
def message_factory(db):
    """Фабрика сообщений чата."""
    from chat.models import Message

    def make(conversation, sender, content="Fixture message"):
        return Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
        )

    return make


# ─────────────────────────────────────────────────────────────────────
# Транзакции
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def purchase_request_factory(db):
    """
    Фабрика запросов на покупку.
    seller берётся из listing.seller.
    """
    from transactions.models import PurchaseRequest

    def make(listing, buyer, status="pending", message="Fixture purchase"):
        return PurchaseRequest.objects.create(
            listing=listing,
            buyer=buyer,
            seller=listing.seller,
            status=status,
            message=message,
        )

    return make
