"""
Модели для множественной загрузки изображений.
"""
from django.db import models
from django.core.validators import FileExtensionValidator
from core.validators import ListingImageValidator
from .models import Listing


class ListingImage(models.Model):
    """
    Изображение объявления (до 5 штук на объявление).
    """
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Объявление'
    )
    image = models.ImageField(
        upload_to='listings/gallery/',
        validators=[ListingImageValidator()],
        verbose_name='Изображение',
        help_text='Макс. 5 МБ. Форматы: JPG, PNG, WebP'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок',
        help_text='Порядок отображения (меньше = раньше)'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Главное изображение'
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Подпись'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )
    
    class Meta:
        verbose_name = 'Изображение объявления'
        verbose_name_plural = 'Изображения объявления'
        ordering = ['order', '-is_primary', 'created_at']
        indexes = [
            models.Index(fields=['listing', 'order']),
            models.Index(fields=['listing', 'is_primary']),
        ]
    
    def __str__(self):
        return f'Изображение {self.order} для {self.listing.title}'
    
    def save(self, *args, **kwargs):
        # Если помечено как главное, снимаем отметку с других
        if self.is_primary:
            ListingImage.objects.filter(
                listing=self.listing,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        
        super().save(*args, **kwargs)

