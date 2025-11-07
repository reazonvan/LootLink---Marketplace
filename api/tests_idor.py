"""
Тесты для проверки IDOR (Insecure Direct Object References) защиты.
Проверяем что пользователи не могут получить доступ к чужим объектам.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from listings.models import Listing, Game
from transactions.models import Review, PurchaseRequest
from chat.models import Conversation, Message

User = get_user_model()


@pytest.fixture
def api_client():
    """API клиент для тестов."""
    return APIClient()


@pytest.fixture
def user1(db):
    """Первый пользователь."""
    return User.objects.create_user(
        username='user1',
        email='user1@test.com',
        password='testpass123'
    )


@pytest.fixture
def user2(db):
    """Второй пользователь."""
    return User.objects.create_user(
        username='user2',
        email='user2@test.com',
        password='testpass123'
    )


@pytest.fixture
def game(db):
    """Тестовая игра."""
    return Game.objects.create(name='Test Game', slug='test-game')


@pytest.fixture
def listing_user1(user1, game):
    """Объявление user1."""
    return Listing.objects.create(
        seller=user1,
        game=game,
        title='User1 Listing',
        description='Test listing',
        price=100.00,
        status='active'
    )


@pytest.fixture
def listing_user2(user2, game):
    """Объявление user2."""
    return Listing.objects.create(
        seller=user2,
        game=game,
        title='User2 Listing',
        description='Test listing',
        price=200.00,
        status='active'
    )


@pytest.mark.django_db
class TestListingIDOR:
    """Тесты IDOR для объявлений."""
    
    def test_user_cannot_edit_other_user_listing(self, api_client, user1, user2, listing_user2):
        """Пользователь не может редактировать чужое объявление."""
        api_client.force_authenticate(user=user1)
        
        response = api_client.patch(
            f'/api/listings/{listing_user2.id}/',
            {'title': 'Hacked Title'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Проверяем что объявление не изменилось
        listing_user2.refresh_from_db()
        assert listing_user2.title == 'User2 Listing'
    
    def test_user_cannot_delete_other_user_listing(self, api_client, user1, user2, listing_user2):
        """Пользователь не может удалить чужое объявление."""
        api_client.force_authenticate(user=user1)
        
        response = api_client.delete(f'/api/listings/{listing_user2.id}/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Listing.objects.filter(id=listing_user2.id).exists()
    
    def test_user_can_edit_own_listing(self, api_client, user1, listing_user1):
        """Пользователь может редактировать своё объявление."""
        api_client.force_authenticate(user=user1)
        
        response = api_client.patch(
            f'/api/listings/{listing_user1.id}/',
            {'title': 'Updated Title'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        listing_user1.refresh_from_db()
        assert listing_user1.title == 'Updated Title'
    
    def test_user_can_read_other_user_listing(self, api_client, user1, listing_user2):
        """Пользователь может читать чужие объявления (read-only)."""
        api_client.force_authenticate(user=user1)
        
        response = api_client.get(f'/api/listings/{listing_user2.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'User2 Listing'


@pytest.mark.django_db
class TestConversationIDOR:
    """Тесты IDOR для чатов."""
    
    def test_user_cannot_access_other_users_conversation(self, api_client, user1, user2, game):
        """Пользователь не может получить доступ к чужой беседе."""
        # Создаем третьего пользователя
        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='testpass123'
        )
        
        # Создаем беседу между user2 и user3
        listing = Listing.objects.create(
            seller=user3,
            game=game,
            title='Test',
            description='Test',
            price=100
        )
        
        conversation = Conversation.objects.create(
            participant1=user2 if user2.id < user3.id else user3,
            participant2=user3 if user2.id < user3.id else user2,
            listing=listing
        )
        
        # user1 пытается получить доступ к беседе user2-user3
        api_client.force_authenticate(user=user1)
        
        response = api_client.get(f'/api/conversations/{conversation.id}/')
        
        # Должен быть либо 404 (не в queryset), либо 403 (нет прав)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
    
    def test_participant_can_access_own_conversation(self, api_client, user1, user2, game):
        """Участник может получить доступ к своей беседе."""
        listing = Listing.objects.create(
            seller=user2,
            game=game,
            title='Test',
            description='Test',
            price=100
        )
        
        conversation = Conversation.objects.create(
            participant1=user1 if user1.id < user2.id else user2,
            participant2=user2 if user1.id < user2.id else user1,
            listing=listing
        )
        
        api_client.force_authenticate(user=user1)
        
        response = api_client.get(f'/api/conversations/{conversation.id}/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_user_cannot_send_message_to_other_conversation(self, api_client, user1, user2, game):
        """Пользователь не может отправить сообщение в чужую беседу."""
        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='testpass123'
        )
        
        listing = Listing.objects.create(
            seller=user3,
            game=game,
            title='Test',
            description='Test',
            price=100
        )
        
        conversation = Conversation.objects.create(
            participant1=user2 if user2.id < user3.id else user3,
            participant2=user3 if user2.id < user3.id else user2,
            listing=listing
        )
        
        api_client.force_authenticate(user=user1)
        
        response = api_client.post(
            f'/api/conversations/{conversation.id}/send_message/',
            {'content': 'Hacking attempt'},
            format='json'
        )
        
        # Должен быть 404 (не в queryset) или 403 (нет прав)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestReviewIDOR:
    """Тесты IDOR для отзывов."""
    
    def test_user_cannot_edit_other_user_review(self, api_client, user1, user2, game):
        """Пользователь не может редактировать чужой отзыв."""
        # Создаем сделку
        listing = Listing.objects.create(
            seller=user2,
            game=game,
            title='Test',
            description='Test',
            price=100
        )
        
        purchase = PurchaseRequest.objects.create(
            listing=listing,
            buyer=user1,
            seller=user2,
            status='completed'
        )
        
        # user2 оставляет отзыв user1
        review = Review.objects.create(
            purchase_request=purchase,
            reviewer=user2,
            reviewed_user=user1,
            rating=5,
            comment='Great buyer!'
        )
        
        # user1 пытается изменить отзыв
        api_client.force_authenticate(user=user1)
        
        response = api_client.patch(
            f'/api/reviews/{review.id}/',
            {'rating': 1, 'comment': 'Hacked'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Проверяем что отзыв не изменился
        review.refresh_from_db()
        assert review.rating == 5
        assert review.comment == 'Great buyer!'


print("✅ Тесты IDOR защиты созданы")

