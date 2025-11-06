"""
Модели для системы споров и диспутов.
"""
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from .models import PurchaseRequest


class Dispute(models.Model):
    """
    Спор по сделке.
    """
    STATUS_CHOICES = [
        ('open', 'Открыт'),
        ('under_review', 'На рассмотрении'),
        ('resolved_buyer', 'Решен в пользу покупателя'),
        ('resolved_seller', 'Решен в пользу продавца'),
        ('resolved_partial', 'Частичное решение'),
        ('closed', 'Закрыт'),
    ]
    
    REASON_CHOICES = [
        ('not_delivered', 'Товар не доставлен'),
        ('wrong_item', 'Не тот товар'),
        ('damaged', 'Товар поврежден'),
        ('not_as_described', 'Не соответствует описанию'),
        ('scam', 'Мошенничество'),
        ('other', 'Другое'),
    ]
    
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='dispute',
        verbose_name='Сделка'
    )
    initiator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='disputes_initiated',
        verbose_name='Инициатор'
    )
    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        verbose_name='Причина'
    )
    description = models.TextField(
        verbose_name='Описание проблемы'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name='Статус'
    )
    
    # Модератор
    moderator = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disputes_moderated',
        verbose_name='Модератор'
    )
    moderator_decision = models.TextField(
        blank=True,
        verbose_name='Решение модератора'
    )
    
    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата решения'
    )
    
    class Meta:
        verbose_name = 'Спор'
        verbose_name_plural = 'Споры'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Спор #{self.id} - {self.get_status_display()}'
    
    def resolve(self, decision, moderator, moderator_comment=''):
        """
        Решить спор.
        
        Args:
            decision: 'buyer', 'seller', или 'partial'
            moderator: модератор, принявший решение
            moderator_comment: комментарий модератора
        """
        from payments.models import Escrow
        
        self.moderator = moderator
        self.moderator_decision = moderator_comment
        self.resolved_at = timezone.now()
        
        if decision == 'buyer':
            self.status = 'resolved_buyer'
            # Возврат средств покупателю
            try:
                escrow = Escrow.objects.get(purchase_request=self.purchase_request)
                escrow.refund_to_buyer(reason='Спор решен в пользу покупателя')
            except Escrow.DoesNotExist:
                pass
        elif decision == 'seller':
            self.status = 'resolved_seller'
            # Передача средств продавцу
            try:
                escrow = Escrow.objects.get(purchase_request=self.purchase_request)
                escrow.release_to_seller()
            except Escrow.DoesNotExist:
                pass
        else:  # partial
            self.status = 'resolved_partial'
            # Частичный возврат (нужно реализовать)
        
        self.save()
        
        # Создаем уведомления
        from core.services import NotificationService
        NotificationService.notify_dispute_resolved(self)


class DisputeMessage(models.Model):
    """
    Сообщения в споре.
    """
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Спор'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='dispute_messages',
        verbose_name='Отправитель'
    )
    message = models.TextField(
        verbose_name='Сообщение'
    )
    is_moderator_message = models.BooleanField(
        default=False,
        verbose_name='Сообщение модератора'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки'
    )
    
    class Meta:
        verbose_name = 'Сообщение в споре'
        verbose_name_plural = 'Сообщения в споре'
        ordering = ['created_at']
    
    def __str__(self):
        return f'Сообщение от {self.sender.username} в споре #{self.dispute.id}'


class DisputeEvidence(models.Model):
    """
    Доказательства по спору (скриншоты, файлы).
    """
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='evidence',
        verbose_name='Спор'
    )
    uploader = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='dispute_evidence',
        verbose_name='Загрузил'
    )
    file = models.FileField(
        upload_to='disputes/evidence/',
        verbose_name='Файл'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )
    
    class Meta:
        verbose_name = 'Доказательство'
        verbose_name_plural = 'Доказательства'
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f'Доказательство для спора #{self.dispute.id}'


class GuaranteeService(models.Model):
    """
    Гарант-сервис для крупных сделок.
    """
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='guarantee',
        verbose_name='Сделка'
    )
    guarantor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='guarantees_provided',
        verbose_name='Гарант'
    )
    fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        verbose_name='Комиссия (%)'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает'),
            ('active', 'Активен'),
            ('completed', 'Завершен'),
            ('cancelled', 'Отменен'),
        ],
        default='pending',
        verbose_name='Статус'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Заметки гаранта'
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
    
    class Meta:
        verbose_name = 'Гарант-сервис'
        verbose_name_plural = 'Гарант-сервис'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Гарант для сделки #{self.purchase_request.id}'

