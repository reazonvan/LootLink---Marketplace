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

from .models import Wallet, Withdrawal


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Доменные исключения
# ---------------------------------------------------------------------------

class InsufficientFundsError(ValidationError):
    """Недостаточно средств на балансе для выполнения операции."""

    def __init__(self, message: str = 'Недостаточно средств на балансе.') -> None:
        super().__init__(message)


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
            'Withdrawal rejected: insufficient funds user_id=%s amount=%s available=%s',
            user.pk, amount, wallet.get_available_balance(),
        )
        raise InsufficientFundsError()

    # Замораживаем средства, чтобы их нельзя было вывести/потратить дважды.
    wallet.frozen_balance += amount
    wallet.save(update_fields=['frozen_balance'])

    withdrawal = Withdrawal.objects.create(
        user=user,
        amount=amount,
        payment_method=payment_method,
        payment_details=payment_details,
        status='pending',
    )

    logger.info(
        'Withdrawal created id=%s user_id=%s amount=%s method=%s',
        withdrawal.pk, user.pk, amount, payment_method,
    )

    return withdrawal


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
        description = f'Пополнение баланса на {amount} ₽'

    result = yookassa_service.create_payment(
        user=user,
        amount=amount,
        description=description,
        return_url=return_url,
    )

    if result.get('success'):
        logger.info(
            'Deposit payment created user_id=%s amount=%s payment_id=%s',
            user.pk, amount, result.get('payment_id'),
        )
    else:
        logger.warning(
            'Deposit payment failed user_id=%s amount=%s error=%s',
            user.pk, amount, result.get('error'),
        )

    return result
