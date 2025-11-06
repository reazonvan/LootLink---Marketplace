"""
Модели для системы модерации.
"""
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class UserBan(models.Model):
    """
    Бан пользователя.
    """
    BAN_TYPES = [
        ('temporary', 'Временный'),
        ('permanent', 'Постоянный'),
    ]
    
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('fraud', 'Мошенничество'),
        ('abuse', 'Оскорбления'),
        ('multiple_violations', 'Множественные нарушения'),
        ('other', 'Другое'),
    ]
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='bans',
        verbose_name='Пользователь'
    )
    ban_type = models.CharField(
        max_length=20,
        choices=BAN_TYPES,
        verbose_name='Тип бана'
    )
    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        verbose_name='Причина'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    moderator = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bans_issued',
        verbose_name='Модератор'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    # Временные бани
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Истекает'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    lifted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата снятия'
    )
    
    class Meta:
        verbose_name = 'Бан'
        verbose_name_plural = 'Баны'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f'Бан {self.user.username} - {self.get_reason_display()}'
    
    def is_expired(self):
        """Проверка истечения временного бана"""
        if self.ban_type == 'permanent':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
    
    def lift(self, moderator=None):
        """Снять бан"""
        self.is_active = False
        self.lifted_at = timezone.now()
        if moderator:
            self.moderator = moderator
        self.save()


class UserWarning(models.Model):
    """
    Предупреждения пользователю.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='warnings',
        verbose_name='Пользователь'
    )
    reason = models.TextField(
        verbose_name='Причина'
    )
    moderator = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='warnings_issued',
        verbose_name='Модератор'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    
    class Meta:
        verbose_name = 'Предупреждение'
        verbose_name_plural = 'Предупреждения'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Предупреждение для {self.user.username}'


class AutoModeration(models.Model):
    """
    Логи автоматической модерации.
    """
    ACTION_TYPES = [
        ('hide', 'Скрыто'),
        ('flag', 'Помечено'),
        ('warn', 'Предупреждение'),
        ('block', 'Заблокировано'),
    ]
    
    content_type = models.CharField(
        max_length=50,
        verbose_name='Тип контента',
        help_text='listing, message, review и т.д.'
    )
    content_id = models.PositiveIntegerField(
        verbose_name='ID контента'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='automod_actions',
        verbose_name='Пользователь'
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name='Действие'
    )
    reason = models.TextField(
        verbose_name='Причина'
    )
    matched_patterns = models.JSONField(
        default=list,
        verbose_name='Обнаруженные паттерны'
    )
    
    is_false_positive = models.BooleanField(
        default=False,
        verbose_name='Ложное срабатывание'
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='automod_reviewed',
        verbose_name='Проверил'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    
    class Meta:
        verbose_name = 'Автомодерация'
        verbose_name_plural = 'Автомодерация'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['content_type', 'content_id']),
        ]
    
    def __str__(self):
        return f'{self.get_action_display()} - {self.content_type} #{self.content_id}'


class ModerationQueue(models.Model):
    """
    Очередь модерации.
    """
    CONTENT_TYPES = [
        ('listing', 'Объявление'),
        ('review', 'Отзыв'),
        ('message', 'Сообщение'),
        ('profile', 'Профиль'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
        ('requires_changes', 'Требует изменений'),
    ]
    
    content_type = models.CharField(
        max_length=50,
        choices=CONTENT_TYPES,
        verbose_name='Тип контента'
    )
    content_id = models.PositiveIntegerField(
        verbose_name='ID контента'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='moderation_queue',
        verbose_name='Пользователь'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    priority = models.IntegerField(
        default=0,
        verbose_name='Приоритет',
        help_text='Чем выше число, тем выше приоритет'
    )
    moderator = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_items',
        verbose_name='Модератор'
    )
    moderator_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий модератора'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Рассмотрено'
    )
    
    class Meta:
        verbose_name = 'Очередь модерации'
        verbose_name_plural = 'Очередь модерации'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status', '-priority']),
            models.Index(fields=['content_type', 'content_id']),
        ]
    
    def __str__(self):
        return f'{self.get_content_type_display()} #{self.content_id}'

