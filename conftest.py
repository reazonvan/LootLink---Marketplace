"""
Pytest конфигурация и фикстуры для всего проекта.
"""
import pytest
from django.contrib.auth import get_user_model
from listings.models import Game, Listing
from transactions.models import PurchaseRequest, Review
from chat.models import Conversation, Message
from decimal import Decimal

CustomUser = get_user_model()


@pytest.fixture
def user_factory(db):
    """Фабрика для создания пользователей."""
    def create_user(username='testuser', email='test@example.com', password='testpass123', verified=False):
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        if verified:
            user.profile.is_verified = True
            user.profile.save()
        return user
    return create_user


@pytest.fixture
def verified_user(user_factory):
    """Верифицированный пользователь."""
    return user_factory(username='verified', email='verified@example.com', verified=True)


@pytest.fixture
def unverified_user(user_factory):
    """Неверифицированный пользователь."""
    return user_factory(username='unverified', email='unverified@example.com', verified=False)


@pytest.fixture
def seller(user_factory):
    """Продавец."""
    return user_factory(username='seller', email='seller@example.com', verified=True)


@pytest.fixture
def buyer(user_factory):
    """Покупатель."""
    return user_factory(username='buyer', email='buyer@example.com', verified=True)


@pytest.fixture
def game(db):
    """Игра для тестов."""
    return Game.objects.create(
        name='Test Game',
        description='Test game for testing'
    )


@pytest.fixture
def game_factory(db):
    """Фабрика для создания игр."""
    def create_game(name='Test Game', slug=None):
        return Game.objects.create(
            name=name,
            slug=slug,
            description=f'Description for {name}'
        )
    return create_game


@pytest.fixture
def listing_factory(db, game):
    """Фабрика для создания объявлений."""
    def create_listing(seller, title='Test Listing', price='100.00', status='active'):
        return Listing.objects.create(
            seller=seller,
            game=game,
            title=title,
            description=f'Description for {title}',
            price=Decimal(price),
            status=status
        )
    return create_listing


@pytest.fixture
def active_listing(seller, listing_factory):
    """Активное объявление."""
    return listing_factory(seller=seller, title='Active Listing', status='active')


@pytest.fixture
def sold_listing(seller, listing_factory):
    """Проданное объявление."""
    return listing_factory(seller=seller, title='Sold Listing', status='sold')


@pytest.fixture
def purchase_request_factory(db):
    """Фабрика для создания запросов на покупку."""
    def create_purchase_request(listing, buyer, status='pending'):
        return PurchaseRequest.objects.create(
            listing=listing,
            buyer=buyer,
            seller=listing.seller,
            status=status,
            message='Test purchase request'
        )
    return create_purchase_request


@pytest.fixture
def conversation_factory(db):
    """Фабрика для создания бесед."""
    def create_conversation(participant1, participant2, listing=None):
        # Сортируем участников для консистентности
        p1, p2 = sorted([participant1, participant2], key=lambda u: u.pk)
        return Conversation.objects.create(
            participant1=p1,
            participant2=p2,
            listing=listing
        )
    return create_conversation


@pytest.fixture
def message_factory(db):
    """Фабрика для создания сообщений."""
    def create_message(conversation, sender, content='Test message'):
        return Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content
        )
    return create_message


@pytest.fixture
def authenticated_client(client, verified_user):
    """Аутентифицированный клиент."""
    client.force_login(verified_user)
    return client


@pytest.fixture
def admin_user(user_factory):
    """Администратор."""
    user = user_factory(username='admin', email='admin@example.com', verified=True)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def admin_client(client, admin_user):
    """Клиент с правами администратора."""
    client.force_login(admin_user)
    return client

