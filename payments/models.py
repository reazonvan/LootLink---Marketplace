from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import CustomUser
from listings.models import Listing
from transactions.models import PurchaseRequest


class Wallet(models.Model):
    """
    Кошелек пользователя для хранения средств.
    """

    user = models.OneToOneField(
        CustomUser, on_delete=models.PROTECT, related_name="wallet", verbose_name="Пользователь"
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="Баланс",
    )
    frozen_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="Замороженный баланс",
        help_text="Средства в эскроу",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Кошелек"
        verbose_name_plural = "Кошельки"
        # БД-уровневые проверки целостности финансов.
        # Защищают от багов в коде (отрицательный баланс, frozen > balance).
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name="wallet_balance_non_negative",
                violation_error_message="Баланс не может быть отрицательным",
            ),
            models.CheckConstraint(
                condition=models.Q(frozen_balance__gte=0)
                & models.Q(frozen_balance__lte=models.F("balance")),
                name="wallet_frozen_consistent",
                violation_error_message="Frozen balance должен быть в [0, balance]",
            ),
        ]

    def __str__(self):
        return f"Кошелек {self.user.username} - {self.balance} ₽"

    def get_available_balance(self):
        """Доступный баланс для вывода"""
        return self.balance - self.frozen_balance

    def freeze_amount(self, amount):
        """Заморозить средства для эскроу"""
        from django.db import transaction

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(id=self.id)
            if wallet.get_available_balance() < amount:
                raise ValueError("Недостаточно средств на балансе")
            wallet.frozen_balance += amount
            wallet.save(update_fields=["frozen_balance"])

    def unfreeze_amount(self, amount):
        """Разморозить средства"""
        from django.db import transaction

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(id=self.id)
            wallet.frozen_balance -= amount
            if wallet.frozen_balance < 0:
                wallet.frozen_balance = 0
            wallet.save(update_fields=["frozen_balance"])


class Transaction(models.Model):
    """
    История всех транзакций в системе.
    """

    TRANSACTION_TYPES = [
        ("deposit", "Пополнение"),
        ("withdrawal", "Вывод"),
        ("purchase", "Покупка"),
        ("sale", "Продажа"),
        ("refund", "Возврат"),
        ("escrow_freeze", "Заморозка (эскроу)"),
        ("escrow_release", "Разморозка (эскроу)"),
        ("commission", "Комиссия"),
        ("promo", "Промокод"),
    ]

    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("processing", "Обработка"),
        ("completed", "Завершена"),
        ("failed", "Ошибка"),
        ("cancelled", "Отменена"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Пользователь",
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPES, verbose_name="Тип транзакции"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    description = models.TextField(blank=True, verbose_name="Описание")

    # Связь с заказом (опционально)
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="Запрос на покупку",
    )

    # Данные платежной системы
    payment_system = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Платежная система",
        help_text="ЮKassa, Stripe и т.д.",
    )
    payment_id = models.CharField(max_length=255, blank=True, verbose_name="ID платежа в системе")
    payment_data = models.JSONField(default=dict, blank=True, verbose_name="Данные платежа")

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Дата создания"
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["payment_id"]),
            # Фильтр истории по типу транзакции (deposit/withdrawal/sale/...)
            models.Index(
                fields=["user", "transaction_type", "-created_at"], name="tx_user_type_idx"
            ),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.user.username} - {self.amount} ₽"

    def mark_completed(self):
        """Отметить транзакцию как завершенную"""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])


class Escrow(models.Model):
    """
    Эскроу-система для безопасных сделок.
    Средства замораживаются до завершения сделки.
    """

    STATUS_CHOICES = [
        ("created", "Создан"),
        ("funded", "Средства заморожены"),
        ("released", "Средства переведены продавцу"),
        ("refunded", "Возврат покупателю"),
        ("disputed", "Спор"),
    ]

    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name="escrow",
        verbose_name="Запрос на покупку",
    )
    buyer = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="escrow_as_buyer",
        verbose_name="Покупатель",
    )
    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="escrow_as_seller",
        verbose_name="Продавец",
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Сумма"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="created", verbose_name="Статус"
    )

    # Таймауты
    auto_release_days = models.PositiveIntegerField(
        default=3,
        verbose_name="Авто-освобождение (дней)",
        help_text="Через сколько дней автоматически передать средства продавцу",
    )
    release_deadline = models.DateTimeField(
        null=True, blank=True, verbose_name="Дедлайн освобождения"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    funded_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата заморозки средств")
    released_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата освобождения средств"
    )

    class Meta:
        verbose_name = "Эскроу"
        verbose_name_plural = "Эскроу"
        ordering = ["-created_at"]
        indexes = [
            # Cron auto_release_escrow ищет funded-эскроу с истёкшим deadline
            models.Index(fields=["status", "release_deadline"], name="escrow_status_deadline_idx"),
            models.Index(fields=["buyer", "-created_at"], name="escrow_buyer_idx"),
            models.Index(fields=["seller", "-created_at"], name="escrow_seller_idx"),
        ]

    def __str__(self):
        return f"Эскроу #{self.id} - {self.amount} ₽ ({self.get_status_display()})"

    def fund(self):
        """Заморозить средства покупателя.

        Использует select_for_update на самом эскроу для защиты от
        конкурентных вызовов fund() и double-проверки статуса.
        """
        from django.db import transaction

        with transaction.atomic():
            # Блокируем эскроу — защищаемся от двойного funding.
            escrow = Escrow.objects.select_for_update().get(pk=self.pk)
            if escrow.status != "created":
                raise ValueError("Эскроу уже профинансирован")

            # Замораживаем средства покупателя.
            # freeze_amount сам берёт select_for_update на Wallet.
            buyer_wallet = Wallet.objects.get(user=escrow.buyer)
            buyer_wallet.freeze_amount(escrow.amount)

            # Обновляем статус
            escrow.status = "funded"
            escrow.funded_at = timezone.now()
            escrow.release_deadline = timezone.now() + timezone.timedelta(
                days=escrow.auto_release_days
            )
            escrow.save(update_fields=["status", "funded_at", "release_deadline"])

            # Создаем транзакцию
            Transaction.objects.create(
                user=escrow.buyer,
                transaction_type="escrow_freeze",
                amount=escrow.amount,
                status="completed",
                description=f"Заморозка средств для сделки #{escrow.purchase_request_id}",
                purchase_request_id=escrow.purchase_request_id,
            )

            # Синхронизируем self
            self.status = escrow.status
            self.funded_at = escrow.funded_at
            self.release_deadline = escrow.release_deadline

    def release_to_seller(self):
        """Передать средства продавцу за вычетом комиссии платформы.

        Идемпотентно: повторный вызов на released-эскроу — no-op (логирует).
        Комиссия платформы (PLATFORM_COMMISSION_PERCENT) удерживается
        с продавца, фиксируется как Transaction типа 'commission'.
        """
        import logging

        from django.conf import settings as django_settings
        from django.db import transaction as db_transaction

        logger = logging.getLogger(__name__)

        with db_transaction.atomic():
            # Блокируем эскроу первым: double-check от race condition.
            escrow = Escrow.objects.select_for_update().get(pk=self.pk)
            if escrow.status == "released":
                logger.info("Escrow #%s already released — no-op", escrow.pk)
                return
            if escrow.status != "funded":
                raise ValueError(f"Эскроу не профинансирован (статус={escrow.status})")

            # Гарантируем существование seller wallet ДО блокировки.
            Wallet.objects.get_or_create(
                user_id=escrow.seller_id, defaults={"balance": 0, "frozen_balance": 0}
            )
            # Блокируем ОБА кошелька одним запросом с ORDER BY id (deadlock prevention)
            wallets = {
                w.user_id: w
                for w in Wallet.objects.select_for_update()
                .filter(user_id__in=[escrow.buyer_id, escrow.seller_id])
                .order_by("id")
            }
            buyer_wallet = wallets[escrow.buyer_id]
            seller_wallet = wallets[escrow.seller_id]

            # Комиссия платформы
            commission_percent = Decimal(
                str(getattr(django_settings, "PLATFORM_COMMISSION_PERCENT", "0"))
            )
            commission = (escrow.amount * commission_percent / Decimal("100")).quantize(
                Decimal("0.01")
            )
            seller_payout = escrow.amount - commission

            # Размораживаем и списываем с покупателя
            buyer_wallet.frozen_balance -= escrow.amount
            if buyer_wallet.frozen_balance < 0:
                buyer_wallet.frozen_balance = Decimal("0")
            buyer_wallet.balance -= escrow.amount
            buyer_wallet.save(update_fields=["balance", "frozen_balance"])

            seller_wallet.balance += seller_payout
            seller_wallet.save(update_fields=["balance"])

            # Обновляем статус
            escrow.status = "released"
            escrow.released_at = timezone.now()
            escrow.save(update_fields=["status", "released_at"])

            # Создаем транзакции
            Transaction.objects.create(
                user_id=escrow.buyer_id,
                transaction_type="purchase",
                amount=-escrow.amount,
                status="completed",
                description=f"Оплата за товар по сделке #{escrow.purchase_request_id}",
                purchase_request_id=escrow.purchase_request_id,
            )
            Transaction.objects.create(
                user_id=escrow.seller_id,
                transaction_type="sale",
                amount=seller_payout,
                status="completed",
                description=f"Продажа товара по сделке #{escrow.purchase_request_id}",
                purchase_request_id=escrow.purchase_request_id,
            )
            if commission > 0:
                Transaction.objects.create(
                    user_id=escrow.seller_id,
                    transaction_type="commission",
                    amount=-commission,
                    status="completed",
                    description=f"Комиссия платформы ({commission_percent}%)",
                    purchase_request_id=escrow.purchase_request_id,
                )

            # Синхронизируем self
            self.status = escrow.status
            self.released_at = escrow.released_at

    def refund_to_buyer(self, reason="", amount=None):
        """Вернуть средства покупателю.

        Если amount=None — полный возврат (escrow → refunded).
        Если amount задан и меньше escrow.amount — частичный возврат:
        часть возвращается покупателю, остаток освобождается продавцу.
        Идемпотентно по статусу.
        """
        import logging

        from django.conf import settings as django_settings
        from django.db import transaction as db_transaction

        logger = logging.getLogger(__name__)

        with db_transaction.atomic():
            escrow = Escrow.objects.select_for_update().get(pk=self.pk)
            if escrow.status in ("refunded", "released"):
                logger.info(
                    "Escrow #%s уже обработан (status=%s) — refund no-op",
                    escrow.pk,
                    escrow.status,
                )
                return
            if escrow.status != "funded":
                raise ValueError(f"Эскроу не профинансирован (статус={escrow.status})")

            full_amount = escrow.amount
            if amount is None:
                refund_amount = full_amount
            else:
                refund_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
                if refund_amount <= 0:
                    raise ValueError("Сумма возврата должна быть положительной")
                if refund_amount > full_amount:
                    raise ValueError(
                        f"Сумма возврата ({refund_amount}) больше эскроу ({full_amount})"
                    )

            seller_part = full_amount - refund_amount

            # Гарантируем seller wallet
            Wallet.objects.get_or_create(
                user_id=escrow.seller_id,
                defaults={"balance": 0, "frozen_balance": 0},
            )
            wallets = {
                w.user_id: w
                for w in Wallet.objects.select_for_update()
                .filter(user_id__in=[escrow.buyer_id, escrow.seller_id])
                .order_by("id")
            }
            buyer_wallet = wallets[escrow.buyer_id]
            seller_wallet = wallets[escrow.seller_id]

            # Размораживаем всю сумму у buyer
            buyer_wallet.frozen_balance -= full_amount
            if buyer_wallet.frozen_balance < 0:
                buyer_wallet.frozen_balance = Decimal("0")

            # Списываем seller_part с buyer и зачисляем seller
            if seller_part > 0:
                # Применяем комиссию платформы на часть, идущую продавцу
                commission_percent = Decimal(
                    str(getattr(django_settings, "PLATFORM_COMMISSION_PERCENT", "0"))
                )
                commission = (seller_part * commission_percent / Decimal("100")).quantize(
                    Decimal("0.01")
                )
                seller_payout = seller_part - commission

                buyer_wallet.balance -= seller_part
                seller_wallet.balance += seller_payout
                seller_wallet.save(update_fields=["balance"])

                Transaction.objects.create(
                    user_id=escrow.seller_id,
                    transaction_type="sale",
                    amount=seller_payout,
                    status="completed",
                    description=(
                        f"Частичная оплата по сделке #{escrow.purchase_request_id} " f"(спор)"
                    ),
                    purchase_request_id=escrow.purchase_request_id,
                )
                if commission > 0:
                    Transaction.objects.create(
                        user_id=escrow.seller_id,
                        transaction_type="commission",
                        amount=-commission,
                        status="completed",
                        description=f"Комиссия платформы ({commission_percent}%)",
                        purchase_request_id=escrow.purchase_request_id,
                    )

            buyer_wallet.save(update_fields=["balance", "frozen_balance"])

            escrow.status = "refunded" if refund_amount == full_amount else "released"
            escrow.released_at = timezone.now()
            escrow.save(update_fields=["status", "released_at"])

            # Транзакция возврата покупателю
            Transaction.objects.create(
                user_id=escrow.buyer_id,
                transaction_type="refund",
                amount=refund_amount,
                status="completed",
                description=f"Возврат средств. Причина: {reason}",
                purchase_request_id=escrow.purchase_request_id,
            )

            self.status = escrow.status
            self.released_at = escrow.released_at


class PromoCode(models.Model):
    """
    Промокоды для скидок.
    """

    DISCOUNT_TYPES = [
        ("fixed", "Фиксированная сумма"),
        ("percent", "Процент"),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name="Код")
    discount_type = models.CharField(
        max_length=20, choices=DISCOUNT_TYPES, default="percent", verbose_name="Тип скидки"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Значение скидки",
    )
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Минимальная сумма покупки",
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Максимум использований",
        help_text="Оставьте пустым для неограниченного",
    )
    uses_count = models.PositiveIntegerField(default=0, verbose_name="Использовано раз")
    valid_from = models.DateTimeField(verbose_name="Действителен с")
    valid_until = models.DateTimeField(verbose_name="Действителен до")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f'{self.code} - {self.discount_value}{"%" if self.discount_type == "percent" else "₽"}'
        )

    def is_valid(self):
        """Проверка действительности промокода"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        # Защита от некорректных конфигураций промокода
        if self.discount_type == "percent" and self.discount_value > 100:
            return False
        return True

    def calculate_discount(self, amount):
        """Рассчитать скидку для суммы"""
        if amount < self.min_purchase_amount:
            return Decimal("0.00")

        if self.discount_type == "fixed":
            return min(self.discount_value, amount)
        else:  # percent
            # Защита от ошибочно введённого процента >100
            pct = min(self.discount_value, Decimal("100"))
            return (amount * pct / 100).quantize(Decimal("0.01"))

    def apply(self):
        """Атомарно применить промокод. Гонка использования невозможна:
        UPDATE с условием uses_count < max_uses в одном SQL.
        Возвращает True, если применение прошло, False — если лимит достигнут.
        """
        from django.db.models import F

        # Если max_uses=NULL → лимита нет, просто инкрементим.
        if self.max_uses is None:
            updated = PromoCode.objects.filter(pk=self.pk).update(uses_count=F("uses_count") + 1)
        else:
            updated = PromoCode.objects.filter(pk=self.pk, uses_count__lt=self.max_uses).update(
                uses_count=F("uses_count") + 1
            )
        if updated:
            self.refresh_from_db(fields=["uses_count"])
            return True
        return False


class Withdrawal(models.Model):
    """
    Заявки на вывод средств.
    """

    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("processing", "Обработка"),
        ("completed", "Завершен"),
        ("rejected", "Отклонен"),
    ]

    PAYMENT_METHODS = [
        ("card", "Банковская карта"),
        ("yoomoney", "ЮMoney"),
        ("qiwi", "QIWI"),
        ("webmoney", "WebMoney"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="withdrawals",
        verbose_name="Пользователь",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(100)],
        verbose_name="Сумма",
        help_text="Минимум 100 ₽",
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, verbose_name="Способ вывода"
    )
    # ВАЖНО: payment_details содержит чувствительные данные (номера карт/кошельков).
    # Хранится в зашифрованном виде через Fernet (см. set_payment_details).
    # Для отображения в админке используется payment_details_masked.
    payment_details = models.CharField(
        max_length=512,
        verbose_name="Реквизиты (зашифровано)",
        help_text="Зашифрованные реквизиты получателя",
    )
    payment_details_masked = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Маскированные реквизиты",
        help_text="Безопасное представление для UI: **** 1234",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    admin_comment = models.TextField(blank=True, verbose_name="Комментарий администратора")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата обработки")

    class Meta:
        verbose_name = "Вывод средств"
        verbose_name_plural = "Выводы средств"
        ordering = ["-created_at"]
        indexes = [
            # Админ-очередь pending-заявок и история пользователя
            models.Index(fields=["status", "-created_at"], name="withdrawal_status_idx"),
            models.Index(fields=["user", "-created_at"], name="withdrawal_user_idx"),
        ]

    def __str__(self):
        return f"Вывод {self.amount} ₽ - {self.user.username} ({self.get_status_display()})"

    @staticmethod
    def _mask_details(raw_details: str, payment_method: str) -> str:
        """Создать безопасное маскированное представление реквизитов.

        Для карт: '**** **** **** 1234'.
        Для кошельков: первые 2 + '...' + последние 4 символа.
        """
        if not raw_details:
            return ""
        digits = "".join(c for c in raw_details if c.isdigit())
        if payment_method == "card" and len(digits) >= 4:
            return f"**** **** **** {digits[-4:]}"
        if len(raw_details) >= 6:
            return f"{raw_details[:2]}...{raw_details[-4:]}"
        return "***"

    def set_payment_details(self, raw_details: str) -> None:
        """Установить реквизиты в зашифрованном виде + сохранить маску.

        Симметричное шифрование Fernet, ключ из settings.PAYMENT_DETAILS_KEY.
        Если cryptography не установлена / ключ не задан — данные хранятся
        как есть (legacy fallback), но с предупреждением в логе.
        """
        import logging

        logger = logging.getLogger(__name__)

        self.payment_details_masked = self._mask_details(raw_details, self.payment_method)

        try:
            from django.conf import settings as django_settings

            from cryptography.fernet import Fernet

            key = getattr(django_settings, "PAYMENT_DETAILS_KEY", None)
            if not key:
                logger.error(
                    "PAYMENT_DETAILS_KEY не задан в settings — "
                    "payment_details хранится в открытом виде. PCI-DSS нарушение."
                )
                self.payment_details = raw_details[:512]
                return
            f = Fernet(key.encode() if isinstance(key, str) else key)
            self.payment_details = f.encrypt(raw_details.encode("utf-8")).decode("ascii")
        except ImportError:
            logger.error("cryptography не установлен — payment_details в открытом виде")
            self.payment_details = raw_details[:512]

    def get_payment_details(self) -> str:
        """Расшифровать реквизиты для админ-UI / выплаты.

        Возвращает '' если расшифровка не удалась.
        """
        if not self.payment_details:
            return ""
        try:
            from django.conf import settings as django_settings

            from cryptography.fernet import Fernet

            key = getattr(django_settings, "PAYMENT_DETAILS_KEY", None)
            if not key:
                # legacy plain-text
                return self.payment_details
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.decrypt(self.payment_details.encode("ascii")).decode("utf-8")
        except Exception:
            # legacy fallback: данные могли быть записаны до включения шифрования
            return self.payment_details


# Импортируем модели диспутов в конец для избежания circular imports
from .models_disputes import Dispute, DisputeEvidence, DisputeMessage
