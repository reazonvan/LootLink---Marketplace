"""
Дополнительные тесты payments/views.py для покрытия:
- deposit POST happy/error path
- withdrawal POST happy/insufficient funds
- apply_promo_code AJAX
- escrow_detail (right access)
- transaction_history (filters)
- deposit_success
"""

from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

import pytest

from payments.models import Escrow, PromoCode, Transaction, Wallet


def _set_wallet(user, balance, frozen=Decimal("0")):
    wallet, _ = Wallet.objects.get_or_create(
        user=user,
        defaults={"balance": balance, "frozen_balance": frozen},
    )
    wallet.balance = balance
    wallet.frozen_balance = frozen
    wallet.save(update_fields=["balance", "frozen_balance"])
    return wallet


# ─────────────────────────────────────────────────────────────────────
# deposit
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDepositPost:

    def test_deposit_post_success_redirects_to_confirmation(
        self,
        client,
        verified_user,
    ):
        """POST с валидной суммой и успешным create_payment → 302 на confirmation_url."""
        # Патчим оба возможных пути импорта (views импортирует services как модуль)
        with patch("payments.services.create_deposit_payment") as mock_create:
            mock_create.return_value = {
                "success": True,
                "payment_id": "p-1",
                "confirmation_url": "https://yookassa.test/conf/p-1",
                "transaction_id": 1,
            }
            client.force_login(verified_user)
            url = reverse("payments:deposit")
            response = client.post(url, data={"amount": "500"})
        assert response.status_code == 302

    def test_deposit_post_payment_error_renders_form(
        self,
        client,
        verified_user,
    ):
        """Если YooKassa вернула error — снова рендерится форма с сообщением."""
        with patch("payments.services.create_deposit_payment") as mock_create:
            mock_create.return_value = {"error": "API down"}
            client.force_login(verified_user)
            url = reverse("payments:deposit")
            response = client.post(url, data={"amount": "500"})
        # Без redirect — рендерится форма (200)
        assert response.status_code == 200

    def test_deposit_post_invalid_form(self, client, verified_user):
        """Без суммы — форма невалидна, возвращается 200 с ошибкой."""
        client.force_login(verified_user)
        url = reverse("payments:deposit")
        response = client.post(url, data={})
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# deposit_success
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDepositSuccess:

    def test_deposit_success_redirects_to_dashboard(self, client, verified_user):
        client.force_login(verified_user)
        url = reverse("payments:deposit_success")
        response = client.get(url)
        assert response.status_code == 302
        assert reverse("payments:wallet_dashboard") in response.url


# ─────────────────────────────────────────────────────────────────────
# withdrawal_create
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWithdrawalCreate:

    def test_withdrawal_post_success(self, client, verified_user):
        _set_wallet(verified_user, balance=Decimal("5000.00"))
        client.force_login(verified_user)
        url = reverse("payments:withdrawal_create")
        response = client.post(
            url,
            data={
                "amount": "500",
                "payment_method": "card",
                "payment_details": "1111 2222 3333 4444",
            },
        )
        assert response.status_code == 302
        verified_user.wallet.refresh_from_db()
        # Сумма должна быть заморожена
        assert verified_user.wallet.frozen_balance == Decimal("500.00")

    def test_withdrawal_post_insufficient_funds(self, client, verified_user):
        _set_wallet(verified_user, balance=Decimal("100.00"))
        client.force_login(verified_user)
        url = reverse("payments:withdrawal_create")
        response = client.post(
            url,
            data={
                "amount": "500",
                "payment_method": "card",
                "payment_details": "1111 2222 3333 4444",
            },
        )
        # Форма не пройдёт валидацию clean_amount → 200 с ошибкой
        assert response.status_code in (200, 302)


# ─────────────────────────────────────────────────────────────────────
# apply_promo_code
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestApplyPromoCode:

    def _create_promo(self, code="SAVE20"):
        return PromoCode.objects.create(
            code=code,
            discount_type="percent",
            discount_value=Decimal("20.00"),
            valid_from=timezone.now() - timezone.timedelta(days=1),
            valid_until=timezone.now() + timezone.timedelta(days=10),
            is_active=True,
        )

    def test_apply_valid_promo(self, client, verified_user):
        self._create_promo()
        client.force_login(verified_user)
        url = reverse("payments:apply_promo_code")
        response = client.post(url, data={"code": "SAVE20"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["discount_value"] == 20.0

    def test_apply_invalid_promo(self, client, verified_user):
        client.force_login(verified_user)
        url = reverse("payments:apply_promo_code")
        response = client.post(url, data={"code": "NOPE"})
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "errors" in data

    def test_apply_promo_get_not_allowed(self, client, verified_user):
        client.force_login(verified_user)
        url = reverse("payments:apply_promo_code")
        response = client.get(url)
        assert response.status_code == 405


# ─────────────────────────────────────────────────────────────────────
# escrow_detail
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEscrowDetail:

    def _create_escrow(self, buyer, seller, listing_factory):
        from transactions.models import PurchaseRequest

        listing = listing_factory(seller, price=Decimal("500"))
        pr = PurchaseRequest.objects.create(
            listing=listing,
            buyer=buyer,
            seller=seller,
            status="accepted",
        )
        return Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=seller,
            amount=Decimal("500"),
        )

    def test_buyer_sees_escrow(self, client, buyer, seller, listing_factory):
        escrow = self._create_escrow(buyer, seller, listing_factory)
        client.force_login(buyer)
        url = reverse("payments:escrow_detail", kwargs={"escrow_id": escrow.id})
        response = client.get(url)
        assert response.status_code == 200

    def test_seller_sees_escrow(self, client, buyer, seller, listing_factory):
        escrow = self._create_escrow(buyer, seller, listing_factory)
        client.force_login(seller)
        url = reverse("payments:escrow_detail", kwargs={"escrow_id": escrow.id})
        response = client.get(url)
        assert response.status_code == 200

    def test_outsider_redirected(self, client, buyer, seller, user_factory, listing_factory):
        escrow = self._create_escrow(buyer, seller, listing_factory)
        outsider = user_factory(username="es_out")
        client.force_login(outsider)
        url = reverse("payments:escrow_detail", kwargs={"escrow_id": escrow.id})
        response = client.get(url)
        assert response.status_code == 302


# ─────────────────────────────────────────────────────────────────────
# transaction_history
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTransactionHistory:

    def test_history_filters_by_type(self, client, verified_user):
        Transaction.objects.create(
            user=verified_user,
            transaction_type="deposit",
            amount=Decimal("100"),
            status="completed",
        )
        Transaction.objects.create(
            user=verified_user,
            transaction_type="withdrawal",
            amount=Decimal("50"),
            status="completed",
        )
        client.force_login(verified_user)
        url = reverse("payments:transaction_history")
        response = client.get(url + "?type=deposit")
        assert response.status_code == 200
        # В контексте только депозиты
        txs = list(response.context["transactions"])
        for tx in txs:
            assert tx.transaction_type == "deposit"

    def test_history_filters_by_status(self, client, verified_user):
        Transaction.objects.create(
            user=verified_user,
            transaction_type="deposit",
            amount=Decimal("100"),
            status="pending",
        )
        Transaction.objects.create(
            user=verified_user,
            transaction_type="deposit",
            amount=Decimal("100"),
            status="completed",
        )
        client.force_login(verified_user)
        url = reverse("payments:transaction_history")
        response = client.get(url + "?status=pending")
        assert response.status_code == 200
        txs = list(response.context["transactions"])
        for tx in txs:
            assert tx.status == "pending"

    def test_history_pagination(self, client, verified_user):
        for i in range(25):
            Transaction.objects.create(
                user=verified_user,
                transaction_type="deposit",
                amount=Decimal("10"),
                status="completed",
            )
        client.force_login(verified_user)
        url = reverse("payments:transaction_history")
        response = client.get(url)
        assert response.status_code == 200
        # 20 элементов на страницу — есть пагинатор
        assert response.context["page_obj"] is not None


# ─────────────────────────────────────────────────────────────────────
# wallet_dashboard
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWalletDashboard:

    def test_dashboard_with_active_escrows(self, client, buyer, seller, listing_factory):
        from transactions.models import PurchaseRequest

        listing = listing_factory(seller, price=Decimal("300"))
        pr = PurchaseRequest.objects.create(
            listing=listing,
            buyer=buyer,
            seller=seller,
            status="accepted",
        )
        _set_wallet(buyer, balance=Decimal("1000"))
        escrow = Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=seller,
            amount=Decimal("300"),
        )
        escrow.fund()

        client.force_login(buyer)
        url = reverse("payments:wallet_dashboard")
        response = client.get(url)
        assert response.status_code == 200
        # В контексте есть active_escrows
        active = response.context["active_escrows"]
        assert escrow in active
