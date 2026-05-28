"""
Тесты для context processors.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from core.context_processors import wallet_balance_processor
from payments.models import Wallet

User = get_user_model()


class WalletBalanceProcessorTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_anonymous_user_returns_zero(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        result = wallet_balance_processor(request)
        self.assertEqual(result["wallet_balance"], 0)

    def test_authenticated_user_returns_balance(self):
        user = User.objects.create_user(username="alice", password="test123", email="a@t.com")
        Wallet.objects.create(user=user, balance=Decimal("750.50"), frozen_balance=0)
        request = self.factory.get("/")
        request.user = user
        result = wallet_balance_processor(request)
        self.assertEqual(result["wallet_balance"], Decimal("750.50"))

    def test_creates_wallet_if_missing(self):
        user = User.objects.create_user(username="bob", password="test123", email="b@t.com")
        request = self.factory.get("/")
        request.user = user
        result = wallet_balance_processor(request)
        self.assertEqual(result["wallet_balance"], Decimal("0"))
        self.assertTrue(Wallet.objects.filter(user=user).exists())
