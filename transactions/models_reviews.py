"""
Расширенные модели для отзывов.
"""
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from .models import Review


class ReviewReply(models.Model):
    """
    Ответы на отзывы.
    """
    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name='reply',
        verbose_name='Отзыв'
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='review_replies',
        verbose_name='Автор ответа'
    )
    text = models.TextField(
        max_length=1000,
        verbose_name='Текст ответа'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    
    class Meta:
        verbose_name = 'Ответ на отзыв'
        verbose_name_plural = 'Ответы на отзывы'
    
    def __str__(self):
        return f'Ответ на отзыв #{self.review.id}'


class ReviewHelpful(models.Model):
    """
    Полезность отзыва (лайки).
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='helpful_votes',
        verbose_name='Отзыв'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='helpful_reviews',
        verbose_name='Пользователь'
    )
    is_helpful = models.BooleanField(
        default=True,
        verbose_name='Полезно'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата'
    )
    
    class Meta:
        verbose_name = 'Полезность отзыва'
        verbose_name_plural = 'Полезность отзывов'
        unique_together = [['review', 'user']]
    
    def __str__(self):
        return f'{"👍" if self.is_helpful else "👎"} от {self.user.username}'


class TopSeller(models.Model):
    """
    Кэш топ продавцов для быстрого доступа.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='top_seller_stats',
        verbose_name='Пользователь'
    )
    rank = models.PositiveIntegerField(
        verbose_name='Место в рейтинге'
    )
    total_sales = models.PositiveIntegerField(
        default=0,
        verbose_name='Всего продаж'
    )
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name='Средний рейтинг'
    )
    badge = models.CharField(
        max_length=50,
        choices=[
            ('diamond', '💎 Алмазный продавец'),
            ('gold', '🥇 Золотой продавец'),
            ('silver', '🥈 Серебряный продавец'),
            ('bronze', '🥉 Бронзовый продавец'),
        ],
        default='bronze',
        verbose_name='Бейдж'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено'
    )
    
    class Meta:
        verbose_name = 'Топ продавец'
        verbose_name_plural = 'Топ продавцы'
        ordering = ['rank']
    
    def __str__(self):
        return f'#{self.rank} - {self.user.username}'

