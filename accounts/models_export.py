"""
Модель для запросов на экспорт данных.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta


class DataExportRequest(models.Model):
    """
    Запрос на экспорт пользовательских данных (GDPR).
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'Обработка'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
    ]

    user = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='data_export_requests',
        verbose_name='Пользователь'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Путь к файлу'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Срок действия'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )

    class Meta:
        verbose_name = 'Запрос на экспорт данных'
        verbose_name_plural = 'Запросы на экспорт данных'
        ordering = ['-created_at']

    def __str__(self):
        return f'Экспорт для {self.user.username} - {self.get_status_display()}'

    def save(self, *args, **kwargs):
        # Устанавливаем срок действия при завершении
        if self.status == 'completed' and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
