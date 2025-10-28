from django.db import models
from accounts.models import CustomUser
from .models import Listing


class Favorite(models.Model):
    """
    Избранные объявления пользователя.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Объявление'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    
    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ['user', 'listing']
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} → {self.listing.title}'

