"""
Расширенные модели для избранного.
"""
from django.db import models
from accounts.models import CustomUser
from .models import Listing


class FavoriteFolder(models.Model):
    """
    Папки для организации избранного.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorite_folders',
        verbose_name='Пользователь'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Название папки'
    )
    icon = models.CharField(
        max_length=50,
        default='bi-folder',
        verbose_name='Иконка',
        help_text='Bootstrap Icons класс'
    )
    color = models.CharField(
        max_length=20,
        default='primary',
        verbose_name='Цвет'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Папка избранного'
        verbose_name_plural = 'Папки избранного'
        ordering = ['order', 'name']
        unique_together = [['user', 'name']]
    
    def __str__(self):
        return f'{self.user.username} - {self.name}'


class PriceAlert(models.Model):
    """
    Оповещения о изменении цены в избранном.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='price_alerts',
        verbose_name='Пользователь'
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='price_alerts',
        verbose_name='Объявление'
    )
    target_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Целевая цена',
        help_text='Уведомить когда цена станет равной или ниже'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Сработало'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    
    class Meta:
        verbose_name = 'Оповещение о цене'
        verbose_name_plural = 'Оповещения о ценах'
        ordering = ['-created_at']
        unique_together = [['user', 'listing']]
    
    def __str__(self):
        return f'{self.user.username} - {self.listing.title} ≤ {self.target_price} ₽'
    
    def check_and_trigger(self, current_price):
        """Проверить и сработать если цена достигнута"""
        if self.is_active and current_price <= self.target_price:
            self.is_active = False
            self.triggered_at = timezone.now()
            self.save()
            
            # Отправляем уведомление
            from core.services import NotificationService
            NotificationService.notify_price_alert(self)
            return True
        return False


class ListingComparison(models.Model):
    """
    Сравнение товаров из избранного.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='comparisons',
        verbose_name='Пользователь'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название сравнения'
    )
    listings = models.ManyToManyField(
        Listing,
        related_name='in_comparisons',
        verbose_name='Объявления'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    
    class Meta:
        verbose_name = 'Сравнение'
        verbose_name_plural = 'Сравнения'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} - {self.listings.count()} товаров'
