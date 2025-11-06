"""
Модели для торговли: торг, резерв, история цен.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser
from .models import Listing
from decimal import Decimal


class PriceHistory(models.Model):
    """
    История изменения цен на объявления.
    """
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='Объявление'
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Старая цена'
    )
    new_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Новая цена'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата изменения'
    )
    
    class Meta:
        verbose_name = 'История цен'
        verbose_name_plural = 'История цен'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['listing', '-changed_at']),
        ]
    
    def __str__(self):
        return f'{self.listing.title}: {self.old_price} → {self.new_price} ₽'
    
    def get_change_percentage(self):
        """Процент изменения цены"""
        if self.old_price == 0:
            return 0
        change = ((self.new_price - self.old_price) / self.old_price) * 100
        return round(change, 2)


class PriceOffer(models.Model):
    """
    Предложение цены (торг).
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принято'),
        ('rejected', 'Отклонено'),
        ('countered', 'Встречное предложение'),
        ('expired', 'Истекло'),
    ]
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='price_offers',
        verbose_name='Объявление'
    )
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='price_offers_made',
        verbose_name='Покупатель'
    )
    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='price_offers_received',
        verbose_name='Продавец'
    )
    
    offered_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Предложенная цена'
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Исходная цена'
    )
    message = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='Сообщение',
        help_text='Почему такая цена?'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    # Встречное предложение
    counter_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Встречная цена'
    )
    counter_message = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='Сообщение продавца'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата ответа'
    )
    expires_at = models.DateTimeField(
        verbose_name='Действительно до'
    )
    
    class Meta:
        verbose_name = 'Предложение цены'
        verbose_name_plural = 'Предложения цен'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', 'status', '-created_at']),
            models.Index(fields=['listing', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.buyer.username} → {self.seller.username}: {self.offered_price} ₽'
    
    def get_discount_percentage(self):
        """Процент скидки от исходной цены"""
        if self.original_price == 0:
            return 0
        discount = ((self.original_price - self.offered_price) / self.original_price) * 100
        return round(discount, 2)
    
    def is_expired(self):
        """Проверка истечения срока"""
        return timezone.now() > self.expires_at
    
    def accept(self):
        """Принять предложение"""
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        # Обновляем цену объявления
        self.listing.price = self.offered_price
        self.listing.save()
        
        # Создаем запись в историю цен
        PriceHistory.objects.create(
            listing=self.listing,
            old_price=self.original_price,
            new_price=self.offered_price
        )
    
    def reject(self):
        """Отклонить предложение"""
        self.status = 'rejected'
        self.responded_at = timezone.now()
        self.save()
    
    def counter(self, counter_price, message=''):
        """Сделать встречное предложение"""
        self.status = 'countered'
        self.counter_price = counter_price
        self.counter_message = message
        self.responded_at = timezone.now()
        self.save()


class ListingReservation(models.Model):
    """
    Резервирование объявления покупателем.
    """
    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('expired', 'Истекло'),
        ('cancelled', 'Отменено'),
        ('completed', 'Завершено'),
    ]
    
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Объявление'
    )
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Покупатель'
    )
    
    duration_hours = models.PositiveIntegerField(
        default=24,
        verbose_name='Длительность (часы)',
        help_text='Сколько часов зарезервировать'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Статус'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    expires_at = models.DateTimeField(
        verbose_name='Истекает'
    )
    
    class Meta:
        verbose_name = 'Резервирование'
        verbose_name_plural = 'Резервирования'
        ordering = ['-created_at']
        # Один пользователь может иметь только одно активное резервирование на объявление
        unique_together = [['listing', 'buyer', 'status']]
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['listing', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f'Резерв: {self.buyer.username} → {self.listing.title}'
    
    def is_active(self):
        """Проверка активности резервирования"""
        return self.status == 'active' and timezone.now() < self.expires_at
    
    def cancel(self):
        """Отменить резервирование"""
        self.status = 'cancelled'
        self.save()
        
        # Освобождаем объявление если оно было зарезервировано
        if self.listing.status == 'reserved':
            self.listing.status = 'active'
            self.listing.save()
    
    def save(self, *args, **kwargs):
        """Автоматически устанавливаем expires_at"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=self.duration_hours)
        super().save(*args, **kwargs)

