"""
WebSocket consumers для real-time чата.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для чата между двумя пользователями.
    """
    
    async def connect(self):
        """Подключение к WebSocket"""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        
        # Проверка аутентификации
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Проверка прав доступа к беседе
        has_access = await self.check_conversation_access()
        if not has_access:
            await self.close()
            return
        
        # Присоединяемся к группе комнаты
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем статус "онлайн"
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )
        
        logger.info(f'User {self.user.username} connected to conversation {self.conversation_id}')
    
    async def disconnect(self, close_code):
        """Отключение от WebSocket"""
        if hasattr(self, 'room_group_name'):
            # Отправляем статус "оффлайн"
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status': 'offline'
                }
            )
            
            # Покидаем группу
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(f'User {self.user.username} disconnected from conversation {self.conversation_id}')
    
    async def receive(self, text_data):
        """Получение сообщения от клиента"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read':
                await self.handle_read_receipt(data)
        
        except Exception as e:
            logger.error(f'Error receiving message: {str(e)}')
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Ошибка обработки сообщения'
            }))
    
    async def handle_message(self, data):
        """Обработка текстового сообщения"""
        content = data.get('content', '').strip()
        
        if not content or len(content) > 5000:
            return
        
        # Сохраняем сообщение в БД
        message = await self.save_message(content)
        
        if message:
            # Отправляем всем участникам беседы
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message['id'],
                        'content': message['content'],
                        'sender_id': message['sender_id'],
                        'sender_username': message['sender_username'],
                        'sender_avatar_url': message['sender_avatar_url'],
                        'created_at': message['created_at'],
                        'is_read': message['is_read']
                    }
                }
            )
    
    async def handle_typing(self, data):
        """Обработка индикатора печати"""
        is_typing = data.get('is_typing', False)
        
        # Отправляем статус печати другому пользователю
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )
    
    async def handle_read_receipt(self, data):
        """Обработка отметки о прочтении"""
        message_id = data.get('message_id')
        
        if message_id:
            await self.mark_message_as_read(message_id)
            
            # Уведомляем о прочтении
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'reader_id': self.user.id
                }
            )
    
    # Обработчики событий из channel layer
    
    async def chat_message(self, event):
        """Отправка сообщения клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        """Отправка индикатора печати"""
        # Не отправляем самому себе
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_status(self, event):
        """Отправка статуса пользователя"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'status',
                'username': event['username'],
                'status': event['status']
            }))
    
    async def message_read(self, event):
        """Уведомление о прочтении сообщения"""
        await self.send(text_data=json.dumps({
            'type': 'read',
            'message_id': event['message_id']
        }))
    
    # Database operations
    
    @database_sync_to_async
    def check_conversation_access(self):
        """Проверка доступа к беседе"""
        from .models import Conversation
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participant1 == self.user or conversation.participant2 == self.user
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        """Сохранение сообщения в БД"""
        from .models import Conversation, Message
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content
            )
            
            # Обновляем время последнего сообщения
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            
            # Получаем URL аватарки отправителя
            avatar_url = None
            if hasattr(message.sender, 'profile') and message.sender.profile.avatar:
                avatar_url = message.sender.profile.avatar.url
            
            return {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender.id,
                'sender_username': message.sender.username,
                'sender_avatar_url': avatar_url,
                'created_at': message.created_at.isoformat(),
                'is_read': message.is_read
            }
        except Exception as e:
            logger.error(f'Error saving message: {str(e)}')
            return None
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Отметка сообщения как прочитанного"""
        from .models import Message
        try:
            message = Message.objects.get(id=message_id)
            if message.sender != self.user and not message.is_read:
                message.is_read = True
                message.save(update_fields=['is_read'])
                return True
        except Message.DoesNotExist:
            pass
        return False

