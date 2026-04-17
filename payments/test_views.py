"""
Тесты для views модуля payments.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Wallet, Withdrawal

User = get_user_model()


class PaymentViewsTestMixin:
    """Общий setup для тестов views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='buyer', password='testpass123', email='buyer@test.com',
        )
        self.wallet, _ = Wallet.objects.get_or_create(
            user=self.user, defaults={'balance': Decimal('5000.00'), 'frozen_balance': 0},
        )
        self.client.login(username='buyer', password='testpass123')


class WalletDashboardTest(PaymentViewsTestMixin, TestCase):

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('payments:wallet_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders(self):
        response = self.client.get(reverse('payments:wallet_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '5')  # баланс


class DepositViewTest(PaymentViewsTestMixin, TestCase):

    def test_deposit_page_renders(self):
        response = self.client.get(reverse('payments:deposit'))
        self.assertEqual(response.status_code, 200)

    def test_deposit_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('payments:deposit'))
        self.assertEqual(response.status_code, 302)


class WithdrawalViewTest(PaymentViewsTestMixin, TestCase):

    def test_withdrawal_page_renders(self):
        response = self.client.get(reverse('payments:withdrawal_create'))
        self.assertEqual(response.status_code, 200)

    def test_withdrawal_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('payments:withdrawal_create'))
        self.assertEqual(response.status_code, 302)


class TransactionHistoryTest(PaymentViewsTestMixin, TestCase):

    def test_history_renders(self):
        response = self.client.get(reverse('payments:transaction_history'))
        self.assertEqual(response.status_code, 200)

    def test_history_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('payments:transaction_history'))
        self.assertEqual(response.status_code, 302)
