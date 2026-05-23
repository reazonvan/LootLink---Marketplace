"""
Модели для системы диспутов в escrow сделках.
"""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import CustomUser

from .models import Escrow


class Dispute(models.Model):
    """
    Диспут (спор) между покупателем и продавцом.
    Создается когда есть разногласия по escrow сделке.
    """

    STATUS_CHOICES = [
        ("open", "Открыт"),
        ("under_review", "На рассмотрении"),
        ("resolved_buyer", "Решен в пользу покупателя"),
        ("resolved_seller", "Решен в пользу продавца"),
        ("resolved_partial", "Частичное решение"),
        ("closed", "Закрыт"),
    ]

    REASON_CHOICES = [
        ("item_not_received", "Товар не получен"),
        ("item_not_as_described", "Товар не соответствует описанию"),
        ("seller_unresponsive", "Продавец не отвечает"),
        ("payment_issue", "Проблема с оплатой"),
        ("fraud_suspected", "Подозрение на мошенничество"),
        ("other", "Другое"),
    ]

    escrow = models.OneToOneField(
        Escrow, on_delete=models.CASCADE, related_name="dispute", verbose_name="Escrow сделка"
    )

    # Участники
    opened_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="disputes_opened",
        verbose_name="Открыт пользователем",
    )

    # Детали диспута
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, verbose_name="Причина")
    description = models.TextField(
        verbose_name="Описание проблемы", help_text="Детально опишите проблему"
    )

    # Статус и решение
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="open", db_index=True, verbose_name="Статус"
    )

    # Модерация
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_assigned",
        verbose_name="Назначен модератору",
        help_text="Модератор, который рассматривает диспут",
    )

    moderator_decision = models.TextField(blank=True, verbose_name="Решение модератора")

    # Финансовое решение
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Сумма возврата",
        help_text="Сумма для возврата покупателю (если применимо)",
    )

    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата решения")

    class Meta:
        verbose_name = "Диспут"
        verbose_name_plural = "Диспуты"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return f"Диспут #{self.id} - {self.get_status_display()}"

    def assign_to_moderator(self, moderator):
        """Назначить диспут модератору."""
        if not moderator.profile.is_moderator and not moderator.is_staff:
            raise ValueError("Только модераторы могут быть назначены на диспуты")

        self.assigned_to = moderator
        self.status = "under_review"
        self.save(update_fields=["assigned_to", "status", "updated_at"])

    RESOLVED_STATUSES = frozenset(
        {"resolved_buyer", "resolved_seller", "resolved_partial", "closed"}
    )

    def resolve_for_buyer(
        self, decision_text, full_refund=True, refund_amount=None, moderator=None
    ):
        """
        Решить диспут в пользу покупателя.

        Args:
            decision_text: Текст решения модератора
            full_refund: Полный возврат средств (True) или частичный
            refund_amount: Для частичного возврата — точная сумма возврата
            moderator: Модератор, принявший решение (для audit)
        """
        from decimal import Decimal

        from django.db import transaction

        from .models import Escrow

        with transaction.atomic():
            dispute = Dispute.objects.select_for_update().get(pk=self.pk)
            escrow = Escrow.objects.select_for_update().get(pk=dispute.escrow_id)

            if dispute.status in self.RESOLVED_STATUSES:
                raise ValueError("Диспут уже решен")

            if full_refund:
                escrow.refund_to_buyer(reason=decision_text, amount=None)
                dispute.refund_amount = escrow.amount
                dispute.status = "resolved_buyer"
            else:
                amt = refund_amount if refund_amount is not None else dispute.refund_amount
                if amt is None or Decimal(str(amt)) <= 0:
                    raise ValueError("Укажите сумму частичного возврата")
                escrow.refund_to_buyer(reason=decision_text, amount=amt)
                dispute.refund_amount = Decimal(str(amt))
                dispute.status = "resolved_partial"

            dispute.moderator_decision = decision_text
            dispute.resolved_at = timezone.now()
            dispute.save(
                update_fields=[
                    "refund_amount",
                    "status",
                    "moderator_decision",
                    "resolved_at",
                    "updated_at",
                ]
            )

            from core.models_audit import SecurityAuditLog

            SecurityAuditLog.log(
                action_type="escrow_refund",
                user=moderator,
                description=f"Диспут #{dispute.id} решен в пользу покупателя. {decision_text}",
                risk_level="medium",
                metadata={
                    "dispute_id": dispute.id,
                    "escrow_id": escrow.id,
                    "buyer_id": escrow.buyer_id,
                    "seller_id": escrow.seller_id,
                    "refund_amount": str(dispute.refund_amount),
                },
            )

            try:
                from core.services import NotificationService

                transaction.on_commit(lambda: NotificationService.notify_dispute_resolved(dispute))
            except Exception:
                pass

            self.status = dispute.status
            self.refund_amount = dispute.refund_amount
            self.resolved_at = dispute.resolved_at

    def resolve_for_seller(self, decision_text, moderator=None):
        """Решить диспут в пользу продавца."""
        from django.db import transaction

        from .models import Escrow

        with transaction.atomic():
            dispute = Dispute.objects.select_for_update().get(pk=self.pk)
            escrow = Escrow.objects.select_for_update().get(pk=dispute.escrow_id)

            if dispute.status in self.RESOLVED_STATUSES:
                raise ValueError("Диспут уже решен")

            escrow.release_to_seller()
            dispute.status = "resolved_seller"
            dispute.moderator_decision = decision_text
            dispute.resolved_at = timezone.now()
            dispute.save(
                update_fields=[
                    "status",
                    "moderator_decision",
                    "resolved_at",
                    "updated_at",
                ]
            )

            from core.models_audit import SecurityAuditLog

            SecurityAuditLog.log(
                action_type="escrow_release",
                user=moderator,
                description=f"Диспут #{dispute.id} решен в пользу продавца. {decision_text}",
                risk_level="medium",
                metadata={
                    "dispute_id": dispute.id,
                    "escrow_id": escrow.id,
                    "buyer_id": escrow.buyer_id,
                    "seller_id": escrow.seller_id,
                    "amount": str(escrow.amount),
                },
            )

            try:
                from core.services import NotificationService

                transaction.on_commit(lambda: NotificationService.notify_dispute_resolved(dispute))
            except Exception:
                pass

            self.status = dispute.status
            self.resolved_at = dispute.resolved_at


class DisputeMessage(models.Model):
    """
    Сообщения в диспуте между участниками и модератором.
    """

    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name="messages", verbose_name="Диспут"
    )

    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="payment_dispute_messages",
        verbose_name="Отправитель",
    )

    message = models.TextField(verbose_name="Сообщение")

    def _dispute_private_storage():
        from config.storage_backends import get_private_storage

        return get_private_storage()

    from core.validators import AttachmentValidator

    # Вложения (опционально). Хранятся в приватном storage —
    # доступ через защищённую view (см. transactions.views_disputes).
    attachment = models.FileField(
        upload_to="disputes/",
        storage=_dispute_private_storage,
        validators=[AttachmentValidator(max_size_mb=10)],
        blank=True,
        null=True,
        verbose_name="Вложение",
        help_text="Скриншот или другое доказательство. Приватный storage.",
    )

    is_moderator_message = models.BooleanField(default=False, verbose_name="Сообщение модератора")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Сообщение в диспуте"
        verbose_name_plural = "Сообщения в диспутах"
        ordering = ["created_at"]

    def __str__(self):
        return f"Сообщение от {self.sender.username} в диспуте #{self.dispute.id}"


class DisputeEvidence(models.Model):
    """
    Доказательства, прикрепленные к диспуту.
    """

    EVIDENCE_TYPES = [
        ("screenshot", "Скриншот"),
        ("chat_log", "Лог переписки"),
        ("video", "Видео"),
        ("other", "Другое"),
    ]

    dispute = models.ForeignKey(
        Dispute, on_delete=models.CASCADE, related_name="evidences", verbose_name="Диспут"
    )

    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="uploaded_evidences",
        verbose_name="Загружено пользователем",
    )

    evidence_type = models.CharField(
        max_length=20,
        choices=EVIDENCE_TYPES,
        default="screenshot",
        verbose_name="Тип доказательства",
    )

    def _evidence_private_storage():
        from config.storage_backends import get_private_storage

        return get_private_storage()

    from core.validators import AttachmentValidator

    file = models.FileField(
        upload_to="dispute_evidences/",
        storage=_evidence_private_storage,
        validators=[AttachmentValidator(max_size_mb=15)],
        verbose_name="Файл",
        help_text="Приватный storage; доступ только участникам спора и модератору.",
    )

    description = models.TextField(blank=True, verbose_name="Описание")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Доказательство"
        verbose_name_plural = "Доказательства"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_evidence_type_display()} для диспута #{self.dispute.id}"
