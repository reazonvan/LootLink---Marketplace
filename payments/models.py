from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from accounts.models import CustomUser
from listings.models import Listing
from transactions.models import PurchaseRequest
from decimal import Decimal


class Wallet(models.Model):
    """
    Кошелек пользователя для хранения средств.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name='Пользователь'
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Баланс'
    )
    frozen_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Замороженный баланс',
        help_text='Средства в эскроу'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Кошелек'
        verbose_name_plural = 'Кошельки'
    
    def __str__(self):
        return f'Кошелек {self.user.username} - {self.balance} ₽'
    
    def get_available_balance(self):
        """Доступный баланс для вывода"""
        return self.balance - self.frozen_balance
    
    def freeze_amount(self, amount):
        """Заморозить средства для эскроу"""
        from django.db import transaction
        
        if self.get_available_balance() < amount:
            raise ValueError('Недостаточно средств на балансе')
        
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(id=self.id)
            wallet.frozen_balance += amount
            wallet.save(update_fields=['frozen_balance'])
    
    def unfreeze_amount(self, amount):
        """Разморозить средства"""
        from django.db import transaction
        
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(id=self.id)
            wallet.frozen_balance -= amount
            if wallet.frozen_balance < 0:
                wallet.frozen_balance = 0
            wallet.save(update_fields=['frozen_balance'])


class Transaction(models.Model):
    """
    История всех транзакций в системе.
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Пополнение'),
        ('withdrawal', 'Вывод'),
        ('purchase', 'Покупка'),
        ('sale', 'Продажа'),
        ('refund', 'Возврат'),
        ('escrow_freeze', 'Заморозка (эскроу)'),
        ('escrow_release', 'Разморозка (эскроу)'),
        ('commission', 'Комиссия'),
        ('promo', 'Промокод'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'Обработка'),
        ('completed', 'Завершена'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменена'),
    ]
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Пользователь'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='Тип транзакции'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    
    # Связь с заказом (опционально)
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Запрос на покупку'
    )
    
    # Данные платежной системы
    payment_system = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Платежная система',
        help_text='ЮKassa, Stripe и т.д.'
    )
    payment_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID платежа в системе'
    )
    payment_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Данные платежа'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата создания'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    
    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_id']),
        ]
    
    def __str__(self):
        return f'{self.get_transaction_type_display()} - {self.user.username} - {self.amount} ₽'
    
    def mark_completed(self):
        """Отметить транзакцию как завершенную"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])


class Escrow(models.Model):
    """
    Эскроу-система для безопасных сделок.
    Средства замораживаются до завершения сделки.
    """
    STATUS_CHOICES = [
        ('created', 'Создан'),
        ('funded', 'Средства заморожены'),
        ('released', 'Средства переведены продавцу'),
        ('refunded', 'Возврат покупателю'),
        ('disputed', 'Спор'),
    ]
    
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='escrow',
        verbose_name='Запрос на покупку'
    )
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='escrow_as_buyer',
        verbose_name='Покупатель'
    )
    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='escrow_as_seller',
        verbose_name='Продавец'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='created',
        verbose_name='Статус'
    )
    
    # Таймауты
    auto_release_days = models.PositiveIntegerField(
        default=3,
        verbose_name='Авто-освобождение (дней)',
        help_text='Через сколько дней автоматически передать средства продавцу'
    )
    release_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дедлайн освобождения'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    funded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата заморозки средств'
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата освобождения средств'
    )
    
    class Meta:
        verbose_name = 'Эскроу'
        verbose_name_plural = 'Эскроу'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Эскроу #{self.id} - {self.amount} ₽ ({self.get_status_display()})'
    
    def fund(self):
        """Заморозить средства покупателя"""
        from django.db import transaction
        
        if self.status != 'created':
            raise ValueError('Эскроу уже профинансирован')
        
        with transaction.atomic():
            # Замораживаем средства
            buyer_wallet = Wallet.objects.select_for_update().get(user=self.buyer)
            buyer_wallet.freeze_amount(self.amount)
            
            # Обновляем статус
            self.status = 'funded'
            self.funded_at = timezone.now()
            self.release_deadline = timezone.now() + timezone.timedelta(days=self.auto_release_days)
            self.save()
            
            # Создаем транзакцию
            Transaction.objects.create(
                user=self.buyer,
                transaction_type='escrow_freeze',
                amount=self.amount,
                status='completed',
                description=f'Заморозка средств для сделки #{self.purchase_request.id}',
                purchase_request=self.purchase_request
            )
    
    def release_to_seller(self):
        """Передать средства продавцу"""
        from django.db import transaction as db_transaction
        
        if self.status != 'funded':
            raise ValueError('Эскроу не профинансирован')
        
        with db_transaction.atomic():
            # Размораживаем у покупателя
            buyer_wallet = Wallet.objects.select_for_update().get(user=self.buyer)
            buyer_wallet.unfreeze_amount(self.amount)
            buyer_wallet.balance -= self.amount
            buyer_wallet.save(update_fields=['balance'])
            
            # Переводим продавцу
            seller_wallet, _ = Wallet.objects.select_for_update().get_or_create(user=self.seller)
            seller_wallet.balance += self.amount
            seller_wallet.save(update_fields=['balance'])
            
            # Обновляем статус
            self.status = 'released'
            self.released_at = timezone.now()
            self.save()
            
            # Создаем транзакции
            Transaction.objects.create(
                user=self.buyer,
                transaction_type='purchase',
                amount=-self.amount,
                status='completed',
                description=f'Оплата за товар #{self.purchase_request.listing.id}',
                purchase_request=self.purchase_request
            )
            Transaction.objects.create(
                user=self.seller,
                transaction_type='sale',
                amount=self.amount,
                status='completed',
                description=f'Продажа товара #{self.purchase_request.listing.id}',
                purchase_request=self.purchase_request
            )
    
    def refund_to_buyer(self, reason=''):
        """Вернуть средства покупателю"""
        from django.db import transaction as db_transaction
        
        if self.status != 'funded':
            raise ValueError('Эскроу не профинансирован')
        
        with db_transaction.atomic():
            # Размораживаем средства
            buyer_wallet = Wallet.objects.select_for_update().get(user=self.buyer)
            buyer_wallet.unfreeze_amount(self.amount)
            
            # Обновляем статус
            self.status = 'refunded'
            self.save()
            
            # Создаем транзакцию
            Transaction.objects.create(
                user=self.buyer,
                transaction_type='refund',
                amount=self.amount,
                status='completed',
                description=f'Возврат средств. Причина: {reason}',
                purchase_request=self.purchase_request
            )


class PromoCode(models.Model):
    """
    Промокоды для скидок.
    """
    DISCOUNT_TYPES = [
        ('fixed', 'Фиксированная сумма'),
        ('percent', 'Процент'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Код'
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPES,
        default='percent',
        verbose_name='Тип скидки'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Значение скидки'
    )
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Минимальная сумма покупки'
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Максимум использований',
        help_text='Оставьте пустым для неограниченного'
    )
    uses_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Использовано раз'
    )
    valid_from = models.DateTimeField(
        verbose_name='Действителен с'
    )
    valid_until = models.DateTimeField(
        verbose_name='Действителен до'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.code} - {self.discount_value}{"%" if self.discount_type == "percent" else "₽"}'
    
    def is_valid(self):
        """Проверка действительности промокода"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        return True
    
    def calculate_discount(self, amount):
        """Рассчитать скидку для суммы"""
        if amount < self.min_purchase_amount:
            return Decimal('0.00')
        
        if self.discount_type == 'fixed':
            return min(self.discount_value, amount)
        else:  # percent
            return (amount * self.discount_value / 100).quantize(Decimal('0.01'))
    
    def apply(self):
        """Применить промокод (увеличить счетчик)"""
        self.uses_count += 1
        self.save(update_fields=['uses_count'])


class Withdrawal(models.Model):
    """
    Заявки на вывод средств.
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'Обработка'),
        ('completed', 'Завершен'),
        ('rejected', 'Отклонен'),
    ]
    
    PAYMENT_METHODS = [
        ('card', 'Банковская карта'),
        ('yoomoney', 'ЮMoney'),
        ('qiwi', 'QIWI'),
        ('webmoney', 'WebMoney'),
    ]
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='withdrawals',
        verbose_name='Пользователь'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(100)],
        verbose_name='Сумма',
        help_text='Минимум 100 ₽'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name='Способ вывода'
    )
    payment_details = models.CharField(
        max_length=255,
        verbose_name='Реквизиты',
        help_text='Номер карты, кошелька и т.д.'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    admin_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий администратора'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата обработки'
    )
    
    class Meta:
        verbose_name = 'Вывод средств'
        verbose_name_plural = 'Выводы средств'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Вывод {self.amount} ₽ - {self.user.username} ({self.get_status_display()})'


# Импортируем модели диспутов в конец для избежания circular imports
from .models_disputes import Dispute, DisputeMessage, DisputeEvidence
