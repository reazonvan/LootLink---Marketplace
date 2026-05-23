"""
Бизнес-логика платёжного модуля (write/action операции).

HackSoft styleguide:
    - services.py — функции, которые что-то ИЗМЕНЯЮТ (DB writes, side-effects).
    - selectors.py — функции, которые ТОЛЬКО ЧИТАЮТ.
    - kwargs-only вызовы (def f(*, arg1, arg2)) — для читабельности и устойчивости
      к рефакторингу позиций аргументов.
    - Атомарность через @transaction.atomic + select_for_update().
    - Side-effects (Celery .delay) — через transaction.on_commit().
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Transaction, Wallet, Withdrawal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Доменные исключения
# ---------------------------------------------------------------------------


class InsufficientFundsError(ValidationError):
    """Недостаточно средств на балансе для выполнения операции."""

    def __init__(self, message: str = "Недостаточно средств на балансе.") -> None:
        super().__init__(message)


class WithdrawalStateError(ValidationError):
    """Невозможно изменить состояние Withdrawal."""


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


@transaction.atomic
def create_withdrawal(
    *,
    user,
    amount: Decimal,
    payment_method: str,
    payment_details: str,
) -> Withdrawal:
    """
    Создать заявку на вывод средств.

    Атомарно блокирует кошелёк (`select_for_update`), проверяет доступный
    баланс, переводит сумму в `frozen_balance` и создаёт заявку Withdrawal
    в статусе ``pending``.

    Args:
        user: Владелец кошелька (обязательно).
        amount: Сумма к выводу. Должна быть ``<= available_balance``.
        payment_method: Один из ``Withdrawal.PAYMENT_METHODS``.
        payment_details: Реквизиты получателя (карта/кошелёк).

    Raises:
        InsufficientFundsError: Если ``available_balance < amount``.
        Wallet.DoesNotExist: Если у пользователя нет кошелька.

    Returns:
        Withdrawal: Созданная заявка в статусе ``pending``.
    """
    # Гарантируем, что кошелёк существует — затем блокируем его.
    Wallet.objects.get_or_create(user=user)
    wallet = Wallet.objects.select_for_update().get(user=user)

    if wallet.get_available_balance() < amount:
        logger.warning(
            "Withdrawal rejected: insufficient funds user_id=%s amount=%s available=%s",
            user.pk,
            amount,
            wallet.get_available_balance(),
        )
        raise InsufficientFundsError()

    # Замораживаем средства, чтобы их нельзя было вывести/потратить дважды.
    wallet.frozen_balance += amount
    wallet.save(update_fields=["frozen_balance"])

    withdrawal = Withdrawal(
        user=user,
        amount=amount,
        payment_method=payment_method,
        status="pending",
    )
    # set_payment_details шифрует реквизиты и заполняет маску
    withdrawal.set_payment_details(payment_details)
    withdrawal.save()

    logger.info(
        "Withdrawal created id=%s user_id=%s amount=%s method=%s",
        withdrawal.pk,
        user.pk,
        amount,
        payment_method,
    )

    return withdrawal


@transaction.atomic
def reject_withdrawal(*, withdrawal_id: int, admin_comment: str = "") -> Withdrawal:
    """
    Отклонить заявку на вывод средств: размораживает frozen_balance.

    Используется админом. Идемпотентно: повторный вызов на rejected/completed
    возвращает текущее состояние без побочных эффектов.
    """
    w = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)

    if w.status in ("rejected", "completed"):
        logger.info("Withdrawal #%s уже в финальном статусе %s", w.pk, w.status)
        return w
    if w.status not in ("pending", "processing"):
        raise WithdrawalStateError(f"Невалидный статус для отклонения: {w.status}")

    # Размораживаем средства пользователя
    wallet = Wallet.objects.select_for_update().get(user_id=w.user_id)
    wallet.frozen_balance = max(Decimal("0"), wallet.frozen_balance - w.amount)
    wallet.save(update_fields=["frozen_balance"])

    w.status = "rejected"
    w.admin_comment = (admin_comment or "")[:500]
    from django.utils import timezone

    w.processed_at = timezone.now()
    w.save(update_fields=["status", "admin_comment", "processed_at"])

    logger.info("Withdrawal rejected id=%s user_id=%s amount=%s", w.pk, w.user_id, w.amount)
    return w


@transaction.atomic
def complete_withdrawal(*, withdrawal_id: int, admin_comment: str = "") -> Withdrawal:
    """
    Завершить вывод средств: списывает frozen_balance И balance.

    Используется админом после фактической отправки денег пользователю.
    Создаёт Transaction записью.
    """
    w = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)

    if w.status == "completed":
        logger.info("Withdrawal #%s уже completed", w.pk)
        return w
    if w.status not in ("pending", "processing"):
        raise WithdrawalStateError(f"Невалидный статус для завершения: {w.status}")

    wallet = Wallet.objects.select_for_update().get(user_id=w.user_id)
    if wallet.balance < w.amount:
        raise InsufficientFundsError(
            f"Баланс пользователя ({wallet.balance}) меньше суммы вывода ({w.amount})"
        )

    wallet.balance -= w.amount
    wallet.frozen_balance = max(Decimal("0"), wallet.frozen_balance - w.amount)
    wallet.save(update_fields=["balance", "frozen_balance"])

    w.status = "completed"
    w.admin_comment = (admin_comment or "")[:500]
    from django.utils import timezone

    w.processed_at = timezone.now()
    w.save(update_fields=["status", "admin_comment", "processed_at"])

    Transaction.objects.create(
        user_id=w.user_id,
        transaction_type="withdrawal",
        amount=-w.amount,
        status="completed",
        description=f"Вывод средств #{w.pk} ({w.get_payment_method_display()})",
    )

    logger.info("Withdrawal completed id=%s user_id=%s amount=%s", w.pk, w.user_id, w.amount)
    return w


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------


def create_deposit_payment(
    *,
    user,
    amount: Decimal,
    return_url: str,
    description: Optional[str] = None,
) -> dict:
    """
    Создать платёж на пополнение баланса через ЮKassa.

    Делегирует работу yookassa_service. Реальное зачисление средств
    происходит в webhook-обработчике после оплаты.

    Args:
        user: Пользователь, пополняющий баланс.
        amount: Сумма пополнения.
        return_url: URL возврата после оплаты.
        description: Описание платежа (по умолчанию формируется автоматически).

    Returns:
        dict: Результат вызова yookassa_service. При успехе содержит
              ``confirmation_url`` для редиректа.
    """
    from .yookassa_integration import yookassa_service

    if description is None:
        description = f"Пополнение баланса на {amount} ₽"

    result = yookassa_service.create_payment(
        user=user,
        amount=amount,
        description=description,
        return_url=return_url,
    )

    if result.get("success"):
        logger.info(
            "Deposit payment created user_id=%s amount=%s payment_id=%s",
            user.pk,
            amount,
            result.get("payment_id"),
        )
    else:
        logger.warning(
            "Deposit payment failed user_id=%s amount=%s error=%s",
            user.pk,
            amount,
            result.get("error"),
        )

    return result
