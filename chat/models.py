from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import CustomUser
from listings.models import Listing


class Conversation(models.Model):
    """
    Модель беседы между двумя пользователями.
    """

    participant1 = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="conversations_as_participant1",
        verbose_name="Участник 1",
    )
    participant2 = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="conversations_as_participant2",
        verbose_name="Участник 2",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
        verbose_name="Объявление",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее сообщение")

    class Meta:
        verbose_name = "Беседа"
        verbose_name_plural = "Беседы"
        ordering = ["-updated_at"]
        # Уникальная пара участников для конкретного объявления.
        # unique_together не работает с NULL (когда listing удалён),
        # поэтому два условных UniqueConstraint вместо одного.
        constraints = [
            models.UniqueConstraint(
                fields=["participant1", "participant2", "listing"],
                condition=models.Q(listing__isnull=False),
                name="unique_conversation_with_listing",
            ),
            models.UniqueConstraint(
                fields=["participant1", "participant2"],
                condition=models.Q(listing__isnull=True),
                name="unique_conversation_no_listing",
            ),
            # participant1.id всегда меньше participant2.id (сортировка пар)
            models.CheckConstraint(
                condition=models.Q(participant1_id__lt=models.F("participant2_id")),
                name="participant1_less_than_participant2",
                violation_error_message="participant1 должен быть меньше participant2 (сортировка по ID)",
            ),
        ]
        indexes = [
            # Список бесед пользователя (отсортирован по последнему сообщению)
            models.Index(fields=["participant1", "-updated_at"], name="conv_p1_updated_idx"),
            models.Index(fields=["participant2", "-updated_at"], name="conv_p2_updated_idx"),
        ]

    def __str__(self):
        return f"Беседа: {self.participant1.username} ↔ {self.participant2.username}"

    def get_other_participant(self, user):
        """Возвращает собеседника."""
        if self.participant1 == user:
            return self.participant2
        return self.participant1

    def get_unread_count(self, user):
        """Возвращает количество непрочитанных сообщений для пользователя."""
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    def get_last_message(self):
        """Возвращает последнее сообщение в беседе.

        Message.Meta.ordering = ['created_at'] (старые первыми), поэтому
        last() корректно возвращает самое свежее сообщение.
        """
        return self.messages.last()


class Message(models.Model):
    """
    Модель сообщения в чате.
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages", verbose_name="Беседа"
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Отправитель",
    )
    content = models.TextField(max_length=5000, verbose_name="Содержимое", blank=True, default="")
    image = models.ImageField(
        upload_to="chat_images/%Y/%m/", null=True, blank=True, verbose_name="Изображение"
    )
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["created_at"]  # старые сообщения первыми
        indexes = [
            # Главный индекс: окно чата (все сообщения беседы в порядке)
            models.Index(fields=["conversation", "-created_at"], name="msg_conv_created_idx"),
            # Подсчёт непрочитанных от других в беседе (badge)
            models.Index(fields=["conversation", "is_read", "sender"], name="msg_unread_idx"),
        ]

    def __str__(self):
        return f"Сообщение от {self.sender.username} в {self.created_at}"


# Сигнал для отправки уведомления ТОЛЬКО получателю
@receiver(post_save, sender=Message, dispatch_uid="chat.message_notify_recipient")
def send_message_notification(sender, instance, created, **kwargs):
    """Отправляет уведомление и email получателю сообщения через NotificationService."""
    if created:
        # Определяем получателя (НЕ отправителя!)
        conversation = instance.conversation
        recipient = conversation.get_other_participant(instance.sender)

        # Оптимизация: одно уведомление на беседу пока не прочитано
        import logging

        from django.db import transaction

        from core.models import Notification

        logger = logging.getLogger(__name__)

        # Используем атомарную транзакцию для предотвращения дубликатов
        with transaction.atomic():
            # Ищем или создаем уведомление атомарно
            from django.urls import NoReverseMatch, reverse

            try:
                conversation_link = reverse(
                    "chat:conversation_detail", kwargs={"pk": conversation.pk}
                )
            except NoReverseMatch:
                conversation_link = "/"

            notification, created = Notification.objects.get_or_create(
                user=recipient,
                notification_type="new_message",
                is_read=False,
                link=conversation_link,
                defaults={
                    "title": f"Новое сообщение от {instance.sender.username}",
                    "message": "У вас есть непрочитанные сообщения",
                },
            )

            if created:
                logger.info(
                    f"Создано новое уведомление для {recipient.username} от {instance.sender.username}"
                )
            else:
                logger.info(
                    f"Обновлено время уведомления для {recipient.username} от {instance.sender.username}"
                )
                from django.utils import timezone

                notification.created_at = timezone.now()
                notification.save(update_fields=["created_at"])
