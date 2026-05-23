from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import CustomUser
from listings.models import Listing


class PurchaseRequest(models.Model):
    """
    Модель запроса на покупку (сделка).
    """

    STATUS_CHOICES = [
        ("pending", "Ожидает подтверждения"),
        ("accepted", "Принят"),
        ("rejected", "Отклонен"),
        ("completed", "Завершен"),
        ("cancelled", "Отменен"),
        ("disputed", "Спор"),
    ]

    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="purchase_requests",
        verbose_name="Объявление",
        help_text="PROTECT: листинг с покупками нельзя удалить — историю нужно сохранять.",
    )
    buyer = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="purchases", verbose_name="Покупатель"
    )
    seller = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="sales", verbose_name="Продавец"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Сумма сделки",
        help_text=(
            "Snapshot цены listing на момент создания запроса. "
            "Эскроу фондируется именно на эту сумму, чтобы продавец не "
            "поднял цену между created и accepted."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,  # Добавлено для производительности
        verbose_name="Статус",
    )
    message = models.TextField(blank=True, verbose_name="Сообщение покупателя")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата принятия")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отклонения")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отмены")

    class Meta:
        verbose_name = "Запрос на покупку"
        verbose_name_plural = "Запросы на покупку"
        ordering = ["-created_at"]
        constraints = [
            # Один активный запрос на покупку на пару listing+buyer
            # Отменённые/отклонённые не блокируют повторную покупку
            models.UniqueConstraint(
                fields=["listing", "buyer"],
                condition=models.Q(status__in=["pending", "accepted"]),
                name="unique_active_purchase_per_buyer",
            ),
        ]
        indexes = [
            models.Index(fields=["buyer", "status"]),
            models.Index(fields=["seller", "status"]),
            models.Index(fields=["seller", "-completed_at"]),
        ]

    def __str__(self):
        return f"{self.buyer.username} → {self.listing.title}"

    # Методы-обёртки сохранены ради обратной совместимости с тестами,
    # но реальная бизнес-логика живёт в transactions.services.
    # Прямые вызовы из views/admin должны идти через services.

    def accept(self):
        """DEPRECATED: используйте transactions.services.accept_purchase_request."""
        from .services import accept_purchase_request

        accept_purchase_request(request_id=self.pk, user=self.seller)
        # Подтягиваем актуальное состояние в self
        self.refresh_from_db()
        return self

    def reject(self):
        """DEPRECATED: используйте transactions.services.reject_purchase_request."""
        from .services import reject_purchase_request

        reject_purchase_request(request_id=self.pk, user=self.seller)
        self.refresh_from_db()
        return self

    def complete(self):
        """DEPRECATED: используйте services.confirm_received_purchase_request."""
        from django.db import transaction

        from .services import _finalize_completed_purchase_request

        with transaction.atomic():
            pr = PurchaseRequest.objects.select_for_update().get(pk=self.pk)
            if pr.status != "accepted":
                raise ValueError(f"Нельзя завершить сделку в статусе {pr.status}")
            _finalize_completed_purchase_request(pr)
            self.status = pr.status


class Review(models.Model):
    """
    Модель отзыва после завершения сделки.
    """

    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE, related_name="reviews", verbose_name="Сделка"
    )
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reviews_given",
        verbose_name="Автор отзыва",
    )
    reviewed_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reviews_received",
        verbose_name="Пользователь",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Оценка"
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        # Один пользователь может оставить только один отзыв на конкретную сделку
        unique_together = ["purchase_request", "reviewer"]
        indexes = [
            models.Index(fields=["reviewed_user", "-created_at"]),
            models.Index(fields=["reviewer", "-created_at"]),
        ]

    def __str__(self):
        return (
            f"Отзыв от {self.reviewer.username} для {self.reviewed_user.username} ({self.rating}/5)"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # P1-17: update_rating через on_commit — если транзакция откатится,
        # рейтинг не пересчитается зря. Безопасно вне atomic — выполнится сразу.
        from django.db import transaction

        reviewed_user_id = self.reviewed_user_id

        def _update_rating():
            try:
                from accounts.models import Profile

                profile = Profile.objects.filter(user_id=reviewed_user_id).first()
                if profile:
                    profile.update_rating()
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "update_rating failed for user_id=%s", reviewed_user_id
                )

        transaction.on_commit(_update_rating)
