"""
Тесты для моделей payments: Wallet, Escrow, Transaction, PromoCode.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from listings.models import Game, Listing
from transactions.models import PurchaseRequest

from .models import Escrow, PromoCode, Transaction, Wallet, Withdrawal

User = get_user_model()


class WalletTestMixin:
    """Общие helpers для тестов payments."""

    def create_user(self, username="testuser", balance=Decimal("1000.00")):
        user = User.objects.create_user(
            username=username, password="testpass123", email=f"{username}@test.com"
        )
        wallet, _ = Wallet.objects.get_or_create(
            user=user, defaults={"balance": balance, "frozen_balance": 0}
        )
        if wallet.balance != balance:
            wallet.balance = balance
            wallet.save(update_fields=["balance"])
        return user, wallet

    def create_listing(self, seller, price=Decimal("500.00")):
        game = Game.objects.create(name=f"Game_{seller.pk}", slug=f"game-{seller.pk}")
        return Listing.objects.create(
            seller=seller,
            game=game,
            title="Test Listing",
            description="Test description",
            price=price,
            status="active",
        )


class WalletModelTest(WalletTestMixin, TestCase):

    def test_get_available_balance(self):
        _, wallet = self.create_user(balance=Decimal("1000.00"))
        wallet.frozen_balance = Decimal("300.00")
        wallet.save(update_fields=["frozen_balance"])
        self.assertEqual(wallet.get_available_balance(), Decimal("700.00"))

    def test_freeze_amount_success(self):
        _, wallet = self.create_user(balance=Decimal("1000.00"))
        wallet.freeze_amount(Decimal("400.00"))
        wallet.refresh_from_db()
        self.assertEqual(wallet.frozen_balance, Decimal("400.00"))
        self.assertEqual(wallet.balance, Decimal("1000.00"))

    def test_freeze_amount_insufficient(self):
        _, wallet = self.create_user(balance=Decimal("100.00"))
        with self.assertRaises(ValueError):
            wallet.freeze_amount(Decimal("200.00"))

    def test_unfreeze_amount(self):
        _, wallet = self.create_user(balance=Decimal("1000.00"))
        wallet.frozen_balance = Decimal("500.00")
        wallet.save(update_fields=["frozen_balance"])
        wallet.unfreeze_amount(Decimal("300.00"))
        wallet.refresh_from_db()
        self.assertEqual(wallet.frozen_balance, Decimal("200.00"))

    def test_unfreeze_does_not_go_negative(self):
        _, wallet = self.create_user(balance=Decimal("1000.00"))
        wallet.frozen_balance = Decimal("100.00")
        wallet.save(update_fields=["frozen_balance"])
        wallet.unfreeze_amount(Decimal("200.00"))
        wallet.refresh_from_db()
        self.assertEqual(wallet.frozen_balance, Decimal("0.00"))

    def test_str(self):
        user, wallet = self.create_user(username="alice", balance=Decimal("500.00"))
        self.assertIn("alice", str(wallet))
        self.assertIn("500", str(wallet))


class EscrowModelTest(WalletTestMixin, TestCase):

    def _create_escrow(self, buyer_balance=Decimal("1000.00"), amount=Decimal("500.00")):
        seller, _ = self.create_user("seller", balance=Decimal("0.00"))
        buyer, _ = self.create_user("buyer", balance=buyer_balance)
        listing = self.create_listing(seller, price=amount)
        pr = PurchaseRequest.objects.create(
            listing=listing,
            buyer=buyer,
            seller=seller,
            status="accepted",
        )
        escrow = Escrow.objects.create(
            purchase_request=pr,
            buyer=buyer,
            seller=seller,
            amount=amount,
        )
        return escrow, buyer, seller

    def test_fund_success(self):
        escrow, buyer, _ = self._create_escrow()
        escrow.fund()
        escrow.refresh_from_db()
        self.assertEqual(escrow.status, "funded")
        self.assertIsNotNone(escrow.funded_at)
        buyer_wallet = Wallet.objects.get(user=buyer)
        self.assertEqual(buyer_wallet.frozen_balance, Decimal("500.00"))

    def test_fund_creates_transaction(self):
        escrow, buyer, _ = self._create_escrow()
        escrow.fund()
        tx = Transaction.objects.filter(user=buyer, transaction_type="escrow_freeze")
        self.assertTrue(tx.exists())
        self.assertEqual(tx.first().amount, Decimal("500.00"))

    def test_fund_already_funded_raises(self):
        escrow, _, _ = self._create_escrow()
        escrow.fund()
        with self.assertRaises(ValueError):
            escrow.fund()

    def test_release_to_seller(self):
        escrow, buyer, seller = self._create_escrow()
        escrow.fund()
        escrow.release_to_seller()
        escrow.refresh_from_db()
        self.assertEqual(escrow.status, "released")
        buyer_wallet = Wallet.objects.get(user=buyer)
        seller_wallet = Wallet.objects.get(user=seller)
        self.assertEqual(buyer_wallet.balance, Decimal("500.00"))
        self.assertEqual(buyer_wallet.frozen_balance, Decimal("0.00"))
        self.assertEqual(seller_wallet.balance, Decimal("500.00"))

    def test_release_creates_two_transactions(self):
        escrow, buyer, seller = self._create_escrow()
        escrow.fund()
        escrow.release_to_seller()
        self.assertTrue(
            Transaction.objects.filter(user=buyer, transaction_type="purchase").exists()
        )
        self.assertTrue(Transaction.objects.filter(user=seller, transaction_type="sale").exists())

    def test_release_not_funded_raises(self):
        escrow, _, _ = self._create_escrow()
        with self.assertRaises(ValueError):
            escrow.release_to_seller()

    def test_refund_to_buyer(self):
        escrow, buyer, _ = self._create_escrow()
        escrow.fund()
        escrow.refund_to_buyer(reason="Test refund")
        escrow.refresh_from_db()
        self.assertEqual(escrow.status, "refunded")
        buyer_wallet = Wallet.objects.get(user=buyer)
        self.assertEqual(buyer_wallet.frozen_balance, Decimal("0.00"))
        self.assertEqual(buyer_wallet.balance, Decimal("1000.00"))

    def test_refund_creates_transaction(self):
        escrow, buyer, _ = self._create_escrow()
        escrow.fund()
        escrow.refund_to_buyer(reason="Dispute")
        tx = Transaction.objects.filter(user=buyer, transaction_type="refund")
        self.assertTrue(tx.exists())


class PromoCodeModelTest(TestCase):

    def _create_promo(self, **kwargs):
        defaults = {
            "code": "TEST10",
            "discount_type": "percent",
            "discount_value": Decimal("10.00"),
            "valid_from": timezone.now() - timezone.timedelta(days=1),
            "valid_until": timezone.now() + timezone.timedelta(days=30),
            "is_active": True,
        }
        defaults.update(kwargs)
        return PromoCode.objects.create(**defaults)

    def test_is_valid_active(self):
        promo = self._create_promo()
        self.assertTrue(promo.is_valid())

    def test_is_valid_inactive(self):
        promo = self._create_promo(is_active=False)
        self.assertFalse(promo.is_valid())

    def test_is_valid_expired(self):
        promo = self._create_promo(
            valid_until=timezone.now() - timezone.timedelta(days=1),
        )
        self.assertFalse(promo.is_valid())

    def test_is_valid_max_uses_reached(self):
        promo = self._create_promo(max_uses=5, uses_count=5)
        self.assertFalse(promo.is_valid())

    def test_calculate_discount_percent(self):
        promo = self._create_promo(discount_value=Decimal("15.00"))
        self.assertEqual(promo.calculate_discount(Decimal("200.00")), Decimal("30.00"))

    def test_calculate_discount_fixed(self):
        promo = self._create_promo(discount_type="fixed", discount_value=Decimal("50.00"))
        self.assertEqual(promo.calculate_discount(Decimal("200.00")), Decimal("50.00"))

    def test_calculate_discount_fixed_caps_at_amount(self):
        promo = self._create_promo(discount_type="fixed", discount_value=Decimal("500.00"))
        self.assertEqual(promo.calculate_discount(Decimal("200.00")), Decimal("200.00"))

    def test_calculate_discount_below_min(self):
        promo = self._create_promo(min_purchase_amount=Decimal("300.00"))
        self.assertEqual(promo.calculate_discount(Decimal("200.00")), Decimal("0.00"))

    def test_apply_increments_counter(self):
        promo = self._create_promo()
        promo.apply()
        promo.refresh_from_db()
        self.assertEqual(promo.uses_count, 1)


class TransactionModelTest(WalletTestMixin, TestCase):

    def test_mark_completed(self):
        user, _ = self.create_user()
        tx = Transaction.objects.create(
            user=user,
            transaction_type="deposit",
            amount=Decimal("100.00"),
            status="pending",
        )
        tx.mark_completed()
        tx.refresh_from_db()
        self.assertEqual(tx.status, "completed")
        self.assertIsNotNone(tx.completed_at)
