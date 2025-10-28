from django.db import models
from accounts.models import CustomUser
from listings.models import Listing


class Report(models.Model):
    """
    Жалобы на объявления или пользователей.
    """
    REPORT_TYPE_CHOICES = [
        ('listing', 'На объявление'),
        ('user', 'На пользователя'),
    ]
    
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('fraud', 'Мошенничество'),
        ('inappropriate', 'Неприемлемый контент'),
        ('fake', 'Подделка'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('reviewed', 'Рассмотрена'),
        ('resolved', 'Решена'),
        ('rejected', 'Отклонена'),
    ]
    
    reporter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name='Автор жалобы'
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='Тип жалобы'
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name='Объявление'
    )
    reported_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports_received',
        verbose_name='Пользователь'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        verbose_name='Причина'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    admin_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий администратора'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата решения'
    )
    
    class Meta:
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.report_type == 'listing':
            return f'Жалоба на объявление: {self.listing.title}'
        return f'Жалоба на пользователя: {self.reported_user.username}'

