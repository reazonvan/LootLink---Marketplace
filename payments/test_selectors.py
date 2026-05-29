"""Тесты payments/selectors.py — read-слой кошельков/транзакций/эскроу."""

from decimal import Decimal

import pytest

from payments.models import Escrow, Transaction, Wallet, Withdrawal
from payments.selectors import (
    get_or_create_user_wallet,
    pending_withdrawals_admin,
    user_active_escrows,
    user_pending_withdrawals,
    user_recent_transactions,
    user_transactions,
)

# ─────────────────────────────────────────────────────────────────────
# Wallet
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_or_create_user_wallet_creates_if_missing(verified_user):
    """Первый вызов создаёт кошелёк."""
    Wallet.objects.filter(user=verified_user).delete()

    wallet = get_or_create_user_wallet(user=verified_user)
    assert wallet.pk is not None
    assert wallet.user_id == verified_user.pk
    assert Wallet.objects.filter(user=verified_user).count() == 1


@pytest.mark.django_db
def test_get_or_create_user_wallet_idempotent(verified_user):
    """Повторный вызов возвращает тот же кошелёк."""
    Wallet.objects.filter(user=verified_user).delete()

    w1 = get_or_create_user_wallet(user=verified_user)
    w2 = get_or_create_user_wallet(user=verified_user)
    assert w1.pk == w2.pk


# ─────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_user_transactions_default_order(verified_user):
    """Транзакции выдаются от свежих к старым."""
    import time

    Transaction.objects.create(
        user=verified_user,
        transaction_type="deposit",
        amount=Decimal("100"),
        status="completed",
        description="old",
    )
    time.sleep(0.01)
    newer = Transaction.objects.create(
        user=verified_user,
        transaction_type="deposit",
        amount=Decimal("200"),
        status="completed",
        description="new",
    )

    pks = list(user_transactions(user=verified_user).values_list("pk", flat=True))
    assert pks[0] == newer.pk


@pytest.mark.django_db
def test_user_transactions_filters_by_type(verified_user):
    """Фильтр transaction_type работает."""
    dep = Transaction.objects.create(
        user=verified_user,
        transaction_type="deposit",
        amount=Decimal("100"),
        status="completed",
        description="d",
    )
    wd = Transaction.objects.create(
        user=verified_user,
        transaction_type="withdrawal",
        amount=Decimal("50"),
        status="completed",
        description="w",
    )

    pks = list(
        user_transactions(user=verified_user, transaction_type="deposit").values_list(
            "pk", flat=True
        ),
    )
    assert dep.pk in pks
    assert wd.pk not in pks


@pytest.mark.django_db
def test_user_transactions_filters_by_status(verified_user):
    """Фильтр status работает."""
    ok = Transaction.objects.create(
        user=verified_user,
        transaction_type="deposit",
        amount=Decimal("100"),
        status="completed",
        description="ok",
    )
    pending = Transaction.objects.create(
        user=verified_user,
        transaction_type="deposit",
        amount=Decimal("100"),
        status="pending",
        description="p",
    )

    pks = list(
        user_transactions(user=verified_user, status="pending").values_list("pk", flat=True),
    )
    assert pending.pk in pks
    assert ok.pk not in pks


@pytest.mark.django_db
def test_user_recent_transactions_respects_limit(verified_user):
    """limit=5 возвращает не более 5 записей."""
    for i in range(10):
        Transaction.objects.create(
            user=verified_user,
            transaction_type="deposit",
            amount=Decimal("10"),
            status="completed",
            description=f"t{i}",
        )

    rows = list(user_recent_transactions(user=verified_user, limit=5))
    assert len(rows) == 5


# ─────────────────────────────────────────────────────────────────────
# Escrow
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_user_active_escrows_only_funded_for_buyer(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """user_active_escrows возвращает только status='funded' где user — buyer."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer)

    funded = Escrow.objects.create(
        purchase_request=pr,
        buyer=buyer,
        seller=seller,
        amount=Decimal("100"),
        status="funded",
    )

    pr2 = purchase_request_factory(listing_factory(seller), buyer)
    Escrow.objects.create(
        purchase_request=pr2,
        buyer=buyer,
        seller=seller,
        amount=Decimal("50"),
        status="released",
    )

    pks = set(user_active_escrows(user=buyer).values_list("pk", flat=True))
    assert funded.pk in pks
    # released — не active
    assert all(e.status == "funded" for e in user_active_escrows(user=buyer))


# ─────────────────────────────────────────────────────────────────────
# Withdrawal
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_user_pending_withdrawals_only_pending(verified_user):
    """Возвращаются только pending заявки конкретного пользователя."""
    pending = Withdrawal.objects.create(
        user=verified_user,
        amount=Decimal("100"),
        payment_method="card",
        status="pending",
    )
    Withdrawal.objects.create(
        user=verified_user,
        amount=Decimal("50"),
        payment_method="card",
        status="completed",
    )

    pks = list(user_pending_withdrawals(user=verified_user).values_list("pk", flat=True))
    assert pks == [pending.pk]


@pytest.mark.django_db
def test_pending_withdrawals_admin_returns_all_pending(verified_user, user_factory):
    """Админский селектор отдаёт pending от всех пользователей."""
    other = user_factory()

    w1 = Withdrawal.objects.create(
        user=verified_user,
        amount=Decimal("100"),
        payment_method="card",
        status="pending",
    )
    w2 = Withdrawal.objects.create(
        user=other,
        amount=Decimal("200"),
        payment_method="card",
        status="pending",
    )
    Withdrawal.objects.create(
        user=verified_user,
        amount=Decimal("50"),
        payment_method="card",
        status="completed",
    )

    pks = set(pending_withdrawals_admin().values_list("pk", flat=True))
    assert {w1.pk, w2.pk} <= pks
