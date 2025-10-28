"""
Unit тесты для приложения chat.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from listings.models import Game, Listing

User = get_user_model()


class ConversationModelTest(TestCase):
    """Тесты для модели Conversation."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        self.user1 = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='testpass123'
        )
        
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.listing = Listing.objects.create(
            seller=self.user2,
            game=self.game,
            title='Test Item',
            description='Test description',
            price=100.00
        )
    
    def test_conversation_creation(self):
        """Тест создания беседы."""
        conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2,
            listing=self.listing
        )
        
        self.assertEqual(conversation.participant1, self.user1)
        self.assertEqual(conversation.participant2, self.user2)
        self.assertEqual(conversation.listing, self.listing)
    
    def test_get_other_participant(self):
        """Тест получения собеседника."""
        conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2,
            listing=self.listing
        )
        
        self.assertEqual(conversation.get_other_participant(self.user1), self.user2)
        self.assertEqual(conversation.get_other_participant(self.user2), self.user1)
    
    def test_get_unread_count(self):
        """Тест подсчета непрочитанных сообщений."""
        conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2,
            listing=self.listing
        )
        
        # Создаем сообщения
        Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='Hello!',
            is_read=False
        )
        Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='How are you?',
            is_read=False
        )
        
        # Должно быть 2 непрочитанных для user1
        self.assertEqual(conversation.get_unread_count(self.user1), 2)
        # И 0 для user2 (он отправитель)
        self.assertEqual(conversation.get_unread_count(self.user2), 0)
    
    def test_unique_conversation_per_listing(self):
        """Тест уникальности беседы для пары участников и объявления."""
        Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2,
            listing=self.listing
        )
        
        # Попытка создать дубликат должна упасть
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Conversation.objects.create(
                participant1=self.user1,
                participant2=self.user2,
                listing=self.listing
            )


class MessageModelTest(TestCase):
    """Тесты для модели Message."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        
        self.conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
    
    def test_message_creation(self):
        """Тест создания сообщения."""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='Hello, world!'
        )
        
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'Hello, world!')
        self.assertFalse(message.is_read)
    
    def test_message_ordering(self):
        """Тест сортировки сообщений (старые первыми)."""
        msg1 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content='First'
        )
        msg2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            content='Second'
        )
        
        messages = list(Message.objects.all())
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)


class ChatViewsTest(TestCase):
    """Тесты для views приложения chat."""
    
    def setUp(self):
        """Подготовка тестовых данных."""
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        
        self.game = Game.objects.create(name='Test Game', slug='test-game')
        self.listing = Listing.objects.create(
            seller=self.user2,
            game=self.game,
            title='Test Item',
            description='Test',
            price=100.00
        )
    
    def test_conversations_list_requires_login(self):
        """Тест требования авторизации для списка бесед."""
        url = reverse('chat:conversations_list')
        response = self.client.get(url)
        
        # Должен быть редирект на страницу входа
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_conversations_list_authenticated(self):
        """Тест доступа к списку бесед для авторизованного пользователя."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('chat:conversations_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Сообщения')
    
    def test_start_conversation(self):
        """Тест начала беседы по объявлению."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('chat:conversation_start', kwargs={'listing_pk': self.listing.pk})
        response = self.client.get(url)
        
        # Должен быть редирект на созданную беседу
        self.assertEqual(response.status_code, 302)
        
        # Беседа должна быть создана
        self.assertTrue(Conversation.objects.filter(
            listing=self.listing
        ).exists())
    
    def test_cannot_start_conversation_with_self(self):
        """Тест запрета на начало беседы с самим собой."""
        self.client.login(username='user2', password='testpass123')
        url = reverse('chat:conversation_start', kwargs={'listing_pk': self.listing.pk})
        response = self.client.get(url)
        
        # Должен быть редирект обратно на объявление
        self.assertEqual(response.status_code, 302)
        
        # Беседа НЕ должна быть создана
        self.assertFalse(Conversation.objects.filter(
            participant1=self.user2,
            participant2=self.user2
        ).exists())
    
    def test_send_message(self):
        """Тест отправки сообщения."""
        self.client.login(username='user1', password='testpass123')
        
        # Создаем беседу
        conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2,
            listing=self.listing
        )
        
        url = reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        response = self.client.post(url, {
            'content': 'Test message'
        })
        
        # Должен быть редирект
        self.assertEqual(response.status_code, 302)
        
        # Сообщение должно быть создано
        self.assertTrue(Message.objects.filter(
            conversation=conversation,
            sender=self.user1,
            content='Test message'
        ).exists())
    
    def test_messages_marked_as_read(self):
        """Тест автоматической отметки сообщений как прочитанных."""
        self.client.login(username='user1', password='testpass123')
        
        # Создаем беседу и непрочитанное сообщение
        conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user2,
            content='Unread message',
            is_read=False
        )
        
        # Открываем беседу
        url = reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        self.client.get(url)
        
        # Сообщение должно стать прочитанным
        message.refresh_from_db()
        self.assertTrue(message.is_read)
    
    def test_cannot_access_other_users_conversation(self):
        """Тест запрета доступа к чужой беседе."""
        # Создаем беседу между user1 и user2
        conversation = Conversation.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        
        # Создаем третьего пользователя
        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='testpass123'
        )
        
        # Пытаемся получить доступ от user3
        self.client.login(username='user3', password='testpass123')
        url = reverse('chat:conversation_detail', kwargs={'pk': conversation.pk})
        response = self.client.get(url)
        
        # Должен быть редирект
        self.assertEqual(response.status_code, 302)
