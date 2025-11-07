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
        # Constraint: participant1.id всегда должен быть меньше participant2.id
        constraints = [
            models.CheckConstraint(
                check=models.Q(participant1_id__lt=models.F('participant2_id')),
                name='participant1_less_than_participant2',
                violation_error_message='participant1 должен быть меньше participant2 (сортировка по ID)'
            ),
        ]
    
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
        
        # Оптимизация: группируем уведомления от одного отправителя
        from core.models import Notification
        from django.utils import timezone
        from datetime import timedelta
        
        # Ищем непрочитанное уведомление о сообщении от этого же отправителя за последние 10 минут
        recent_time = timezone.now() - timedelta(minutes=10)
        existing_notification = Notification.objects.filter(
            user=recipient,
            notification_type='new_message',
            is_read=False,
            created_at__gte=recent_time,
            link=f'/chat/conversation/{conversation.pk}/'
        ).first()
        
        if existing_notification:
            # Обновляем существующее уведомление
            unread_count = conversation.get_unread_count(recipient)
            
            if unread_count > 1:
                existing_notification.title = f'{unread_count} новых сообщений от {instance.sender.username}'
                existing_notification.message = f'Последнее: {instance.content[:100]}'
            else:
                existing_notification.title = f'Новое сообщение от {instance.sender.username}'
                existing_notification.message = instance.content[:100]
            
            if len(instance.content) > 100:
                existing_notification.message += '...'
            
            existing_notification.created_at = timezone.now()  # Обновляем время
            existing_notification.save()
        else:
            # Создаем новое уведомление
            from core.services import NotificationService
            NotificationService.notify_new_message(instance, recipient)

