"""
Дополнительные модели для уведомлений.
"""
from django.db import models
from accounts.models import CustomUser


class NotificationSettings(models.Model):
    """
    Настройки уведомлений пользователя.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='Пользователь'
    )
    
    # Email уведомления
    email_new_message = models.BooleanField(
        default=True,
        verbose_name='Email при новом сообщении'
    )
    email_purchase_request = models.BooleanField(
        default=True,
        verbose_name='Email при запросе на покупку'
    )
    email_price_offer = models.BooleanField(
        default=True,
        verbose_name='Email при предложении цены'
    )
    email_review = models.BooleanField(
        default=True,
        verbose_name='Email при новом отзыве'
    )
    
    # Push уведомления
    push_enabled = models.BooleanField(
        default=False,
        verbose_name='Push уведомления включены'
    )
    push_subscription = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Push subscription данные'
    )
    
    # Telegram уведомления
    telegram_enabled = models.BooleanField(
        default=False,
        verbose_name='Telegram уведомления'
    )
    telegram_chat_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Telegram Chat ID'
    )
    
    # Частота сводок
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('realtime', 'Мгновенно'),
            ('hourly', 'Раз в час'),
            ('daily', 'Раз в день'),
            ('never', 'Никогда'),
        ],
        default='realtime',
        verbose_name='Частота сводок'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Настройки уведомлений'
        verbose_name_plural = 'Настройки уведомлений'
    
    def __str__(self):
        return f'Настройки {self.user.username}'


class PushSubscription(models.Model):
    """
    Push subscription для Web Push.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        verbose_name='Пользователь'
    )
    subscription_info = models.JSONField(
        verbose_name='Subscription Info'
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='User Agent'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    last_used = models.DateTimeField(
        auto_now=True,
        verbose_name='Последнее использование'
    )
    
    class Meta:
        verbose_name = 'Push подписка'
        verbose_name_plural = 'Push подписки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Push для {self.user.username}'

