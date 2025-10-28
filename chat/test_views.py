"""
Comprehensive тесты для views приложения chat.
"""
import pytest
from django.urls import reverse
from chat.models import Conversation, Message


@pytest.mark.django_db
class TestConversationsList:
    """Тесты списка бесед."""
    
    def test_conversations_list_requires_login(self, client):
        """Список бесед требует авторизации."""
        response = client.get(reverse('chat:conversations_list'))
        assert response.status_code == 302
    
    def test_conversations_list_loads(self, authenticated_client):
        """Список бесед загружается."""
        response = authenticated_client.get(reverse('chat:conversations_list'))
        assert response.status_code == 200
    
    def test_conversations_list_shows_conversations(self, authenticated_client, verified_user, seller, conversation_factory):
        """Список показывает беседы пользователя."""
        conversation = conversation_factory(verified_user, seller)
        
        response = authenticated_client.get(reverse('chat:conversations_list'))
        
        assert response.status_code == 200
        content = response.content.decode()
        assert seller.username in content or verified_user.username in content


@pytest.mark.django_db
class TestConversationDetail:
    """Тесты детальной страницы беседы."""
    
    def test_conversation_detail_requires_login(self, client, seller, buyer, conversation_factory):
        """Детали беседы требуют авторизации."""
        conversation = conversation_factory(seller, buyer)
        
        response = client.get(
            reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        )
        assert response.status_code == 302
    
    def test_conversation_detail_loads(self, authenticated_client, verified_user, seller, conversation_factory):
        """Детали беседы загружаются."""
        conversation = conversation_factory(verified_user, seller)
        
        response = authenticated_client.get(
            reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        )
        assert response.status_code == 200
    
    def test_conversation_only_for_participants(self, authenticated_client, verified_user, seller, buyer, conversation_factory):
        """Доступ только для участников."""
        # Создаем беседу между seller и buyer (verified_user не участник)
        conversation = conversation_factory(seller, buyer)
        
        response = authenticated_client.get(
            reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        )
        
        # verified_user не участник, должен быть редирект
        if verified_user not in [conversation.participant1, conversation.participant2]:
            assert response.status_code == 302
    
    def test_send_message_success(self, authenticated_client, verified_user, seller, conversation_factory):
        """Успешная отправка сообщения."""
        conversation = conversation_factory(verified_user, seller)
        
        data = {
            'content': 'Test message'
        }
        response = authenticated_client.post(
            reverse('chat:conversation_detail', kwargs={'pk': conversation.pk}),
            data
        )
        
        assert Message.objects.filter(
            conversation=conversation,
            sender=verified_user,
            content='Test message'
        ).exists()
    
    def test_messages_marked_read(self, authenticated_client, verified_user, seller, conversation_factory, message_factory):
        """Сообщения отмечаются прочитанными."""
        conversation = conversation_factory(verified_user, seller)
        
        # Создаем непрочитанное сообщение от seller
        message = message_factory(conversation, seller)
        assert not message.is_read
        
        # verified_user открывает беседу
        response = authenticated_client.get(
            reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        )
        
        assert response.status_code == 200
        
        # Сообщение должно быть отмечено прочитанным
        message.refresh_from_db()
        assert message.is_read


@pytest.mark.django_db
class TestConversationStart:
    """Тесты начала беседы."""
    
    def test_start_conversation_requires_login(self, client, active_listing):
        """Начало беседы требует авторизации."""
        response = client.get(
            reverse('chat:conversation_start', kwargs={'listing_pk': active_listing.pk})
        )
        assert response.status_code == 302
    
    def test_cannot_start_with_self(self, authenticated_client, verified_user, listing_factory):
        """Нельзя начать беседу с собой."""
        listing = listing_factory(verified_user)
        
        response = authenticated_client.get(
            reverse('chat:conversation_start', kwargs={'listing_pk': listing.pk})
        )
        
        assert response.status_code == 302
        assert not Conversation.objects.filter(listing=listing).exists()
    
    def test_start_conversation_success(self, authenticated_client, verified_user, active_listing):
        """Успешное начало беседы."""
        response = authenticated_client.get(
            reverse('chat:conversation_start', kwargs={'listing_pk': active_listing.pk})
        )
        
        assert response.status_code == 302
        assert Conversation.objects.filter(
            listing=active_listing
        ).exists()
    
    def test_start_conversation_redirects_to_existing(self, authenticated_client, verified_user, active_listing, conversation_factory):
        """Редирект на существующую беседу."""
        existing = conversation_factory(verified_user, active_listing.seller, active_listing)
        
        response = authenticated_client.get(
            reverse('chat:conversation_start', kwargs={'listing_pk': active_listing.pk})
        )
        
        assert response.status_code == 302
        assert str(existing.pk) in response.url
        
        # Не должно быть создано новой беседы
        assert Conversation.objects.filter(listing=active_listing).count() == 1


@pytest.mark.django_db
class TestGetNewMessages:
    """Тесты API получения новых сообщений."""
    
    def test_get_new_messages_requires_login(self, client, seller, buyer, conversation_factory):
        """API требует авторизации."""
        conversation = conversation_factory(seller, buyer)
        
        response = client.get(
            reverse('chat:get_new_messages', kwargs={'conversation_pk': conversation.pk})
        )
        assert response.status_code == 302
    
    def test_get_new_messages_success(self, authenticated_client, verified_user, seller, conversation_factory, message_factory):
        """Успешное получение новых сообщений."""
        conversation = conversation_factory(verified_user, seller)
        msg = message_factory(conversation, seller, 'New message')
        
        response = authenticated_client.get(
            reverse('chat:get_new_messages', kwargs={'conversation_pk': conversation.pk}),
            {'after': 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'messages' in data
        assert len(data['messages']) > 0
    
    def test_get_new_messages_after_id(self, authenticated_client, verified_user, seller, conversation_factory, message_factory):
        """Получение сообщений после определенного ID."""
        conversation = conversation_factory(verified_user, seller)
        msg1 = message_factory(conversation, seller, 'Message 1')
        msg2 = message_factory(conversation, seller, 'Message 2')
        
        response = authenticated_client.get(
            reverse('chat:get_new_messages', kwargs={'conversation_pk': conversation.pk}),
            {'after': msg1.id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Должно вернуть только msg2
        assert len(data['messages']) == 1
        assert data['messages'][0]['content'] == 'Message 2'

