"""
Модель для истории просмотров объявлений.
"""
from django.db import models
from django.utils import timezone


class ViewHistory(models.Model):
    """
    История просмотров объявлений пользователем.
    Хранит последние 50 просмотров для каждого пользователя.
    """
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='view_history',
        verbose_name='Пользователь'
    )
    listing = models.ForeignKey(
        'Listing',
        on_delete=models.CASCADE,
        related_name='views',
        verbose_name='Объявление'
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата просмотра'
    )

    class Meta:
        verbose_name = 'История просмотра'
        verbose_name_plural = 'История просмотров'
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['listing', '-viewed_at']),
        ]
        # Уникальность: один пользователь может просмотреть объявление только один раз
        # (при повторном просмотре обновляется время)
        unique_together = ['user', 'listing']

    def __str__(self):
        return f'{self.user.username} просмотрел {self.listing.title}'

    @classmethod
    def record_view(cls, user, listing):
        """
        Записывает просмотр объявления.
        Если запись уже существует - обновляет время.
        Ограничивает историю 50 последними просмотрами.
        """
        if not user.is_authenticated:
            return

        # Не записываем просмотр своих объявлений
        if listing.seller == user:
            return

        # Обновляем или создаем запись
        view, created = cls.objects.update_or_create(
            user=user,
            listing=listing,
            defaults={'viewed_at': timezone.now()}
        )

        # Ограничиваем историю 50 записями
        user_views = cls.objects.filter(user=user).order_by('-viewed_at')
        if user_views.count() > 50:
            # Удаляем старые записи
            old_views = user_views[50:]
            cls.objects.filter(id__in=[v.id for v in old_views]).delete()

        return view
