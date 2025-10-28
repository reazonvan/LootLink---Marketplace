from django.db import models
from django.core.validators import MaxLengthValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import CustomUser
from listings.models import Listing


class Conversation(models.Model):
    """
    Модель беседы между двумя пользователями.
    """
    participant1 = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='conversations_as_participant1',
        verbose_name='Участник 1'
    )
    participant2 = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='conversations_as_participant2',
        verbose_name='Участник 2'
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations',
        verbose_name='Объявление'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Последнее сообщение'
    )
    
    class Meta:
        verbose_name = 'Беседа'
        verbose_name_plural = 'Беседы'
        ordering = ['-updated_at']
        # Уникальная пара участников для конкретного объявления
        unique_together = ['participant1', 'participant2', 'listing']
    
    def __str__(self):
        return f'Беседа: {self.participant1.username} ↔ {self.participant2.username}'
    
    def get_other_participant(self, user):
        """Возвращает собеседника."""
        if self.participant1 == user:
            return self.participant2
        return self.participant1
    
    def get_unread_count(self, user):
        """Возвращает количество непрочитанных сообщений для пользователя."""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def get_last_message(self):
        """Возвращает последнее сообщение в беседе."""
        return self.messages.first()


class Message(models.Model):
    """
    Модель сообщения в чате.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Беседа'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель'
    )
    content = models.TextField(
        max_length=5000,
        verbose_name='Содержимое'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки'
    )
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']  # Исправлено: старые сообщения первыми
    
    def __str__(self):
        return f'Сообщение от {self.sender.username} в {self.created_at}'


# Сигнал для отправки уведомления ТОЛЬКО получателю
@receiver(post_save, sender=Message)
def send_message_notification(sender, instance, created, **kwargs):
    """Отправляет уведомление и email получателю сообщения через NotificationService."""
    if created:
        # Определяем получателя (НЕ отправителя!)
        conversation = instance.conversation
        recipient = conversation.get_other_participant(instance.sender)
        
        # Используем централизованный NotificationService
        from core.services import NotificationService
        NotificationService.notify_new_message(instance, recipient)

