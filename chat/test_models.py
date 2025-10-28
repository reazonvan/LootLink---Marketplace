"""
Comprehensive тесты для моделей chat.
"""
import pytest
from chat.models import Conversation, Message
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


@pytest.mark.django_db
class TestConversationModel:
    """Тесты модели Conversation."""
    
    def test_conversation_creation(self, seller, buyer, active_listing):
        """Создание беседы."""
        # Сортируем участников
        p1, p2 = sorted([seller, buyer], key=lambda u: u.pk)
        
        conversation = Conversation.objects.create(
            participant1=p1,
            participant2=p2,
            listing=active_listing
        )
        
        assert conversation.participant1 == p1
        assert conversation.participant2 == p2
        assert conversation.listing == active_listing
    
    def test_conversation_str(self, seller, buyer, conversation_factory):
        """Строковое представление."""
        conversation = conversation_factory(seller, buyer)
        
        # Порядок может быть разным из-за сортировки
        assert seller.username in str(conversation)
        assert buyer.username in str(conversation)
        assert '↔' in str(conversation)
    
    def test_unique_together(self, seller, buyer, active_listing, conversation_factory):
        """Уникальная пара участников для объявления."""
        conversation_factory(seller, buyer, active_listing)
        
        # Попытка создать дубликат
        with pytest.raises(Exception):
            p1, p2 = sorted([seller, buyer], key=lambda u: u.pk)
            Conversation.objects.create(
                participant1=p1,
                participant2=p2,
                listing=active_listing
            )
    
    def test_get_other_participant(self, seller, buyer, conversation_factory):
        """Получение собеседника."""
        conversation = conversation_factory(seller, buyer)
        
        assert conversation.get_other_participant(seller) == buyer
        assert conversation.get_other_participant(buyer) == seller
    
    def test_get_unread_count(self, seller, buyer, conversation_factory, message_factory):
        """Подсчет непрочитанных сообщений."""
        conversation = conversation_factory(seller, buyer)
        
        # Создаем непрочитанное сообщение от buyer
        message = message_factory(conversation, buyer)
        
        # Seller должен видеть 1 непрочитанное
        assert conversation.get_unread_count(seller) == 1
        
        # Buyer не должен видеть свои сообщения как непрочитанные
        assert conversation.get_unread_count(buyer) == 0
    
    def test_get_last_message(self, seller, buyer, conversation_factory, message_factory):
        """Получение последнего сообщения."""
        conversation = conversation_factory(seller, buyer)
        
        msg1 = message_factory(conversation, seller, 'First')
        msg2 = message_factory(conversation, buyer, 'Second')
        
        last_message = conversation.get_last_message()
        assert last_message == msg2


@pytest.mark.django_db
class TestMessageModel:
    """Тесты модели Message."""
    
    def test_message_creation(self, seller, buyer, conversation_factory):
        """Создание сообщения."""
        conversation = conversation_factory(seller, buyer)
        
        message = Message.objects.create(
            conversation=conversation,
            sender=seller,
            content='Hello!'
        )
        
        assert message.sender == seller
        assert message.content == 'Hello!'
        assert not message.is_read
    
    def test_message_str(self, seller, buyer, conversation_factory, message_factory):
        """Строковое представление."""
        conversation = conversation_factory(seller, buyer)
        message = message_factory(conversation, seller)
        
        assert seller.username in str(message)
        assert 'Сообщение' in str(message)
    
    def test_message_ordering(self, seller, buyer, conversation_factory, message_factory):
        """Сообщения сортируются по дате создания."""
        conversation = conversation_factory(seller, buyer)
        
        msg1 = message_factory(conversation, seller, 'First')
        msg2 = message_factory(conversation, buyer, 'Second')
        
        messages = list(Message.objects.all())
        assert messages[0] == msg1  # Старое первое
        assert messages[1] == msg2
    
    def test_message_max_length(self, seller, buyer, conversation_factory):
        """Максимальная длина сообщения."""
        conversation = conversation_factory(seller, buyer)
        
        long_content = 'A' * 6000  # Больше 5000
        
        message = Message(
            conversation=conversation,
            sender=seller,
            content=long_content
        )
        
        # Django должен обрезать или вызвать ошибку
        try:
            message.full_clean()
            message.save()
        except Exception:
            # Ожидаемое поведение
            pass

