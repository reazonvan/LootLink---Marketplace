"""
Тесты форм payments: DepositForm, PromoCodeForm, WithdrawalForm.
"""

from decimal import Decimal

from django.utils import timezone

import pytest

from payments.forms import DepositForm, PromoCodeForm, WithdrawalForm
from payments.models import PromoCode, Wallet

# ─────────────────────────────────────────────────────────────────────
# DepositForm
# ─────────────────────────────────────────────────────────────────────


class TestDepositForm:

    def test_choice_amount_valid(self):
        form = DepositForm(data={"amount": "500"})
        assert form.is_valid()
        assert form.cleaned_data["final_amount"] == Decimal("500")

    def test_custom_amount_valid(self):
        form = DepositForm(data={"custom_amount": "750.50"})
        assert form.is_valid()
        assert form.cleaned_data["final_amount"] == Decimal("750.50")

    def test_no_amount_fails(self):
        form = DepositForm(data={})
        assert not form.is_valid()
        # ValidationError на уровне формы
        assert form.errors

    def test_custom_below_min_invalid(self):
        form = DepositForm(data={"custom_amount": "5"})
        assert not form.is_valid()
        assert "custom_amount" in form.errors

    def test_custom_above_max_invalid(self):
        form = DepositForm(data={"custom_amount": "999999"})
        assert not form.is_valid()
        assert "custom_amount" in form.errors

    def test_custom_takes_precedence_over_choice(self):
        """Когда заполнены оба — берётся custom_amount."""
        form = DepositForm(data={"amount": "500", "custom_amount": "1234"})
        assert form.is_valid()
        assert form.cleaned_data["final_amount"] == Decimal("1234")


# ─────────────────────────────────────────────────────────────────────
# PromoCodeForm
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPromoCodeForm:

    def _create_promo(self, **kwargs):
        defaults = {
            "code": "WELCOME10",
            "discount_type": "percent",
            "discount_value": Decimal("10.00"),
            "valid_from": timezone.now() - timezone.timedelta(days=1),
            "valid_until": timezone.now() + timezone.timedelta(days=30),
            "is_active": True,
        }
        defaults.update(kwargs)
        return PromoCode.objects.create(**defaults)

    def test_unknown_code_invalid(self):
        form = PromoCodeForm(data={"code": "NOPE"})
        assert not form.is_valid()
        assert "code" in form.errors

    def test_expired_code_invalid(self):
        self._create_promo(
            code="OLD",
            valid_until=timezone.now() - timezone.timedelta(days=1),
        )
        form = PromoCodeForm(data={"code": "OLD"})
        assert not form.is_valid()

    def test_valid_code_attaches_promo(self):
        promo = self._create_promo()
        form = PromoCodeForm(data={"code": "welcome10"})  # с lower-case
        assert form.is_valid()
        # Код должен быть приведён к upper и совпасть с базой
        assert form.promo_code == promo
        assert form.cleaned_data["code"] == "WELCOME10"


# ─────────────────────────────────────────────────────────────────────
# WithdrawalForm
# ─────────────────────────────────────────────────────────────────────


def _set_wallet(user, balance, frozen=Decimal("0")):
    """Создать или обновить кошелёк с Decimal-балансом."""
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={"balance": balance, "frozen_balance": frozen},
    )
    wallet.balance = balance
    wallet.frozen_balance = frozen
    wallet.save(update_fields=["balance", "frozen_balance"])
    return wallet


@pytest.mark.django_db
class TestWithdrawalForm:

    def test_amount_below_min(self, verified_user):
        _set_wallet(verified_user, Decimal("5000.00"))
        form = WithdrawalForm(
            user=verified_user,
            data={
                "amount": "50",
                "payment_method": "card",
                "payment_details": "1111 2222 3333 4444",
            },
        )
        assert not form.is_valid()
        assert "amount" in form.errors

    def test_amount_exceeds_balance(self, verified_user):
        _set_wallet(verified_user, Decimal("500.00"))
        form = WithdrawalForm(
            user=verified_user,
            data={
                "amount": "1000",
                "payment_method": "card",
                "payment_details": "1111 2222 3333 4444",
            },
        )
        assert not form.is_valid()
        assert "amount" in form.errors

    def test_valid_withdrawal(self, verified_user):
        _set_wallet(verified_user, Decimal("5000.00"))
        form = WithdrawalForm(
            user=verified_user,
            data={
                "amount": "500",
                "payment_method": "card",
                "payment_details": "1111 2222 3333 4444",
            },
        )
        assert form.is_valid(), form.errors

    def test_form_without_user_skips_balance_check(self, verified_user):
        """Если user не передан, проверка баланса пропускается."""
        _set_wallet(verified_user, Decimal("100.00"))
        form = WithdrawalForm(
            user=None,
            data={
                "amount": "500",
                "payment_method": "yoomoney",
                "payment_details": "410011000000",
            },
        )
        # min=100 проходит, баланса не проверяется → валидно
        assert form.is_valid()

    def test_amount_with_frozen_balance(self, verified_user):
        """Учитывает frozen_balance — нельзя вывести замороженное."""
        _set_wallet(verified_user, Decimal("1000.00"), frozen=Decimal("800.00"))
        form = WithdrawalForm(
            user=verified_user,
            data={
                "amount": "500",
                "payment_method": "card",
                "payment_details": "1111 2222 3333 4444",
            },
        )
        # доступно только 200, заявка на 500 → отказ
        assert not form.is_valid()
        assert "amount" in form.errors
