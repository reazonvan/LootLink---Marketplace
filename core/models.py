from django.db import models
from accounts.models import CustomUser

# Импортируем audit модели
from .models_audit import SecurityAuditLog, DataChangeLog


class Notification(models.Model):
    """
    Модель уведомлений для пользователей.
    """
    NOTIFICATION_TYPES = [
        ('new_message', 'Новое сообщение'),
        ('purchase_request', 'Запрос на покупку'),
        ('request_accepted', 'Запрос принят'),
        ('request_rejected', 'Запрос отклонен'),
        ('deal_completed', 'Сделка завершена'),
        ('new_review', 'Новый отзыв'),
        ('system', 'Системное уведомление'),
    ]
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Пользователь'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        verbose_name='Тип уведомления'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок'
    )
    message = models.TextField(
        max_length=500,
        verbose_name='Сообщение'
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Ссылка',
        help_text='URL для перехода при клике'
    )
    
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Прочитано'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата создания'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата прочтения'
    )
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f'{self.title} для {self.user.username}'
    
    def mark_as_read(self):
        """Отметить уведомление как прочитанное."""
        from django.utils import timezone
        from django.core.cache import cache
        
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
            
            # Инвалидируем кэш количества уведомлений
            cache_key = f'unread_notif_count_{self.user.id}'
            cache.delete(cache_key)
    
    @classmethod
    def create_notification(cls, user, notification_type, title, message, link=''):
        """Создать новое уведомление."""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
    
    @classmethod
    def mark_all_as_read(cls, user):
        """Отметить все уведомления пользователя как прочитанные."""
        from django.utils import timezone
        from django.core.cache import cache
        
        cls.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Инвалидируем кэш количества уведомлений
        cache_key = f'unread_notif_count_{user.id}'
        cache.delete(cache_key)

