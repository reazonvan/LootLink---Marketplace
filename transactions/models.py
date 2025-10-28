from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser
from listings.models import Listing


class PurchaseRequest(models.Model):
    """
    Модель запроса на покупку (сделка).
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('accepted', 'Принят'),
        ('rejected', 'Отклонен'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='purchase_requests',
        verbose_name='Объявление'
    )
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='purchases',
        verbose_name='Покупатель'
    )
    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sales',
        verbose_name='Продавец'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,  # Добавлено для производительности
        verbose_name='Статус'
    )
    message = models.TextField(
        blank=True,
        verbose_name='Сообщение покупателя'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    
    class Meta:
        verbose_name = 'Запрос на покупку'
        verbose_name_plural = 'Запросы на покупку'
        ordering = ['-created_at']
        # Один покупатель может сделать только один запрос на конкретное объявление
        unique_together = ['listing', 'buyer']
    
    def __str__(self):
        return f'{self.buyer.username} → {self.listing.title}'
    
    def accept(self):
        """Принимает запрос на покупку."""
        self.status = 'accepted'
        self.listing.status = 'reserved'
        self.listing.save()
        self.save()
    
    def reject(self):
        """Отклоняет запрос на покупку."""
        self.status = 'rejected'
        self.save()
    
    def complete(self):
        """Завершает сделку."""
        from django.utils import timezone
        from django.db import transaction
        from django.db.models import F
        from accounts.models import Profile
        
        # Все операции в одной транзакции (исправление критической ошибки)
        with transaction.atomic():
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.listing.status = 'sold'
            self.listing.save()
            
            # Атомарное обновление статистики (исправление Race Condition)
            Profile.objects.filter(user=self.seller).update(
                total_sales=F('total_sales') + 1
            )
            Profile.objects.filter(user=self.buyer).update(
                total_purchases=F('total_purchases') + 1
            )
            
            self.save()


class Review(models.Model):
    """
    Модель отзыва после завершения сделки.
    """
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Сделка'
    )
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        verbose_name='Автор отзыва'
    )
    reviewed_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        verbose_name='Пользователь'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        # Один пользователь может оставить только один отзыв на конкретную сделку
        unique_together = ['purchase_request', 'reviewer']
    
    def __str__(self):
        return f'Отзыв от {self.reviewer.username} для {self.reviewed_user.username} ({self.rating}/5)'
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Обновляем рейтинг пользователя после сохранения отзыва
        self.reviewed_user.profile.update_rating()

