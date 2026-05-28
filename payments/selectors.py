"""
Запросы к БД payments-модуля (read/query операции).

HackSoft styleguide:
    - selectors.py — только чтение, без изменений в БД.
    - Все ``select_related``/``prefetch_related`` живут тут, чтобы не плодить
      одинаковые querysets по views.
    - Возвращаем queryset/list/одиночный объект — не render-объекты.
"""

from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet

from .models import Escrow, Transaction, Wallet, Withdrawal

# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------


def get_or_create_user_wallet(*, user) -> Wallet:
    """Получить или создать кошелёк пользователя (без блокировки)."""
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def user_wallet_with_lock(*, user) -> Wallet:
    """
    Получить кошелёк пользователя с блокировкой строки.

    ВНИМАНИЕ: вызывать только внутри ``transaction.atomic()``.
    """
    return Wallet.objects.select_for_update().get(user=user)


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


def user_transactions(
    *,
    user,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
) -> QuerySet[Transaction]:
    """
    История транзакций пользователя (без пагинации, без лимита).

    Возвращает queryset — view сам применяет paginator.
    """
    qs = (
        Transaction.objects.filter(user=user)
        .select_related("purchase_request__listing")
        .order_by("-created_at")
    )
    if transaction_type:
        qs = qs.filter(transaction_type=transaction_type)
    if status:
        qs = qs.filter(status=status)
    return qs


def user_recent_transactions(*, user, limit: int = 20) -> QuerySet[Transaction]:
    """Последние N транзакций пользователя (для дашборда кошелька)."""
    return Transaction.objects.filter(user=user).select_related("purchase_request")[:limit]


# ---------------------------------------------------------------------------
# Escrow
# ---------------------------------------------------------------------------


def user_active_escrows(*, user) -> QuerySet[Escrow]:
    """Активные эскроу пользователя (status=funded), где он покупатель."""
    return Escrow.objects.filter(buyer=user, status="funded").select_related(
        "seller", "purchase_request__listing"
    )


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


def user_pending_withdrawals(*, user) -> QuerySet[Withdrawal]:
    """Pending-заявки пользователя (для дашборда кошелька)."""
    return Withdrawal.objects.filter(user=user, status="pending")


def pending_withdrawals_admin() -> QuerySet[Withdrawal]:
    """Все pending-заявки на вывод — для админ-очереди."""
    return (
        Withdrawal.objects.filter(status="pending").select_related("user").order_by("-created_at")
    )
