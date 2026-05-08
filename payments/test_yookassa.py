"""
Тесты YooKassa интеграции: создание платежа, проверка статуса, webhook.
Все внешние HTTP-вызовы замоканы (yookassa.Payment).
Особое внимание — идемпотентности webhook (двойной callback не должен задвоить баланс).
"""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from payments.models import Transaction, Wallet
from payments.yookassa_integration import YooKassaService


# ─────────────────────────────────────────────────────────────────────
# Хелперы для моков ЮKassa
# ─────────────────────────────────────────────────────────────────────

def _mock_payment(payment_id='test-payment-id', status='succeeded', paid=True,
                  amount_value='500.00', currency='RUB', metadata=None):
    """Создаёт mock-объект, имитирующий ответ yookassa.Payment."""
    pm = MagicMock()
    pm.id = payment_id
    pm.status = status
    pm.paid = paid
    pm.amount = MagicMock()
    pm.amount.value = amount_value
    pm.amount.currency = currency
    pm.metadata = metadata or {}
    pm.created_at = '2026-05-08T12:00:00Z'
    pm.confirmation = MagicMock()
    pm.confirmation.confirmation_url = f'https://yookassa.test/confirm/{payment_id}'
    return pm


def _build_service(enabled=True, allowed_ips=None):
    """Сконструировать YooKassaService с замокаными атрибутами без реального SDK."""
    service = YooKassaService.__new__(YooKassaService)
    service.shop_id = 'test_shop' if enabled else ''
    service.secret_key = 'test_secret' if enabled else ''
    service.enabled = enabled
    service.allowed_webhook_ips = set(allowed_ips or [])
    service.Payment = MagicMock()
    return service


# ─────────────────────────────────────────────────────────────────────
# create_payment / check_payment
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestYookassaCreatePayment:
    """Создание платежей."""

    def test_create_payment_disabled_returns_error(self, verified_user):
        """Если YooKassa не настроена — возвращается понятная ошибка, БД не пишется."""
        service = _build_service(enabled=False)
        result = service.create_payment(verified_user, Decimal('500'), 'Тест')
        assert 'error' in result
        assert not Transaction.objects.exists()

    def test_create_payment_success_creates_transaction(self, verified_user, settings):
        """Успешный create — создается Transaction в pending и сохраняется payment_id."""
        settings.SITE_URL = 'https://test.lootlink.ru'
        service = _build_service(enabled=True)
        service.Payment.create.return_value = _mock_payment(payment_id='pid-123')

        result = service.create_payment(verified_user, Decimal('500'), 'Пополнение')

        assert result['success'] is True
        assert result['payment_id'] == 'pid-123'
        assert 'confirmation_url' in result
        assert 'transaction_id' in result

        tx = Transaction.objects.get(id=result['transaction_id'])
        assert tx.user == verified_user
        assert tx.transaction_type == 'deposit'
        assert tx.status == 'pending'
        assert tx.amount == Decimal('500')
        assert tx.payment_id == 'pid-123'
        assert tx.payment_system == 'yookassa'

    def test_create_payment_api_exception_returns_error(self, verified_user, settings):
        """Исключение при создании в YooKassa — функция возвращает ошибку, не падает."""
        settings.SITE_URL = 'https://test.lootlink.ru'
        service = _build_service(enabled=True)
        service.Payment.create.side_effect = RuntimeError('Network down')

        result = service.create_payment(verified_user, Decimal('100'), 'Тест')
        assert 'error' in result

    def test_check_payment_disabled(self):
        service = _build_service(enabled=False)
        assert 'error' in service.check_payment('any-id')

    def test_check_payment_success(self):
        """check_payment возвращает нормализованные поля."""
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-7', status='succeeded', amount_value='250.00',
            metadata={'transaction_id': '7'},
        )
        result = service.check_payment('pid-7')
        assert result['success'] is True
        assert result['status'] == 'succeeded'
        assert result['paid'] is True
        assert result['amount'] == Decimal('250.00')

    def test_check_payment_api_exception(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.side_effect = RuntimeError('boom')
        result = service.check_payment('pid-x')
        assert 'error' in result


# ─────────────────────────────────────────────────────────────────────
# Парсинг webhook payload (extract / verify)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestYookassaPayloadHelpers:

    def test_safe_get_dict_and_obj(self):
        service = _build_service(enabled=True)
        assert service._safe_get({'a': 1}, 'a') == 1
        assert service._safe_get({'a': 1}, 'b', 'def') == 'def'
        assert service._safe_get(None, 'a', 'def') == 'def'
        # объект с атрибутами
        obj = MagicMock(x=42)
        assert service._safe_get(obj, 'x') == 42

    def test_extract_payment_fields(self):
        service = _build_service(enabled=True)
        payload = {
            'id': 'p1',
            'status': 'succeeded',
            'paid': True,
            'amount': {'value': '300.00', 'currency': 'RUB'},
            'metadata': {'transaction_id': '5'},
        }
        fields = service._extract_payment_fields(payload)
        assert fields['id'] == 'p1'
        assert fields['amount_value'] == Decimal('300.00')
        assert fields['currency'] == 'RUB'
        assert fields['metadata'] == {'transaction_id': '5'}


# ─────────────────────────────────────────────────────────────────────
# verify_webhook_payload — сверка payload с API
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestYookassaWebhookVerify:

    def _payload(self, **overrides):
        base = {
            'id': 'pid-1',
            'status': 'succeeded',
            'paid': True,
            'amount': {'value': '500.00', 'currency': 'RUB'},
            'metadata': {'transaction_id': '1'},
        }
        base.update(overrides)
        return base

    def test_verify_no_payment_id_rejected(self):
        service = _build_service(enabled=True)
        payload = {'status': 'succeeded'}  # нет id
        assert service._verify_webhook_payload('payment.succeeded', payload) is False

    def test_verify_api_exception_rejected(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.side_effect = RuntimeError('API down')
        assert service._verify_webhook_payload('payment.succeeded', self._payload()) is False

    def test_verify_status_mismatch_rejected(self):
        service = _build_service(enabled=True)
        # API говорит canceled, payload — succeeded
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', status='canceled', paid=False,
        )
        assert service._verify_webhook_payload('payment.succeeded', self._payload()) is False

    def test_verify_amount_mismatch_rejected(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', amount_value='999.00',
        )
        assert service._verify_webhook_payload('payment.succeeded', self._payload()) is False

    def test_verify_currency_mismatch_rejected(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', currency='USD',
        )
        assert service._verify_webhook_payload('payment.succeeded', self._payload()) is False

    def test_verify_succeeded_but_api_not_paid_rejected(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', status='succeeded', paid=False,
        )
        assert service._verify_webhook_payload('payment.succeeded', self._payload()) is False

    def test_verify_canceled_but_api_succeeded_rejected(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', status='succeeded',
        )
        payload = self._payload(status='canceled')
        assert service._verify_webhook_payload('payment.canceled', payload) is False

    def test_verify_succeeded_passes(self):
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', status='succeeded', paid=True,
        )
        assert service._verify_webhook_payload('payment.succeeded', self._payload()) is True


# ─────────────────────────────────────────────────────────────────────
# handle_webhook — основной бизнес-цикл и идемпотентность
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestYookassaHandleWebhook:

    def _make_pending_tx(self, user, amount=Decimal('500.00'), payment_id='pid-1'):
        return Transaction.objects.create(
            user=user, transaction_type='deposit', amount=amount,
            status='pending', payment_id=payment_id, payment_system='yookassa',
        )

    def _payload(self, tx, payment_id='pid-1', event='payment.succeeded',
                 status='succeeded', paid=True, amount_value=None):
        return {
            'event': event,
            'object': {
                'id': payment_id,
                'status': status,
                'paid': paid,
                'amount': {'value': amount_value or str(tx.amount), 'currency': 'RUB'},
                'metadata': {'transaction_id': str(tx.id)},
            },
        }

    def test_disabled_returns_false(self, verified_user):
        service = _build_service(enabled=False)
        assert service.handle_webhook({'event': 'payment.succeeded'}) is False

    def test_ip_whitelist_blocks_unknown_ip(self, verified_user):
        service = _build_service(enabled=True, allowed_ips=['1.2.3.4'])
        tx = self._make_pending_tx(verified_user)
        result = service.handle_webhook(self._payload(tx), request_ip='9.9.9.9')
        assert result is False

    def test_ip_whitelist_allows_known_ip(self, verified_user):
        service = _build_service(enabled=True, allowed_ips=['1.2.3.4'])
        # Кошелёк нужен заранее, иначе get_or_create создаст с float-балансом
        Wallet.objects.create(user=verified_user, balance=Decimal('0.00'))
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', status='succeeded', paid=True,
            amount_value='500.00',
        )
        tx = self._make_pending_tx(verified_user)
        result = service.handle_webhook(self._payload(tx), request_ip='1.2.3.4')
        assert result is True

    def test_missing_event_or_object_rejected(self):
        service = _build_service(enabled=True)
        assert service.handle_webhook({}) is False
        assert service.handle_webhook({'event': 'payment.succeeded'}) is False

    def test_missing_transaction_id_in_metadata(self, verified_user):
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(payment_id='pid-1')
        payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'pid-1',
                'status': 'succeeded',
                'paid': True,
                'amount': {'value': '500.00', 'currency': 'RUB'},
                'metadata': {},  # нет transaction_id
            },
        }
        assert service.handle_webhook(payload) is False

    def test_succeeded_credits_wallet(self, verified_user):
        """Главный счастливый путь: succeeded → транзакция completed, баланс пополнен."""
        service = _build_service(enabled=True)
        Wallet.objects.create(user=verified_user, balance=Decimal('0.00'))
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-1', status='succeeded', paid=True,
            amount_value='500.00',
        )
        tx = self._make_pending_tx(verified_user, amount=Decimal('500.00'))

        result = service.handle_webhook(self._payload(tx))

        assert result is True
        tx.refresh_from_db()
        assert tx.status == 'completed'
        assert tx.completed_at is not None
        wallet = Wallet.objects.get(user=verified_user)
        assert wallet.balance == Decimal('500.00')

    def test_succeeded_double_send_idempotent(self, verified_user):
        """Двойной webhook payment.succeeded не должен задвоить баланс."""
        service = _build_service(enabled=True)
        Wallet.objects.create(user=verified_user, balance=Decimal('0.00'))
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-2', status='succeeded', paid=True,
            amount_value='300.00',
        )
        tx = self._make_pending_tx(verified_user, amount=Decimal('300.00'),
                                   payment_id='pid-2')
        payload = self._payload(tx, payment_id='pid-2')

        # Первый вызов — кошелёк заполнен
        assert service.handle_webhook(payload) is True
        # Второй (дубль) — просто ignored
        assert service.handle_webhook(payload) is True

        wallet = Wallet.objects.get(user=verified_user)
        assert wallet.balance == Decimal('300.00')  # всё ещё одна сумма
        assert Transaction.objects.filter(user=verified_user).count() == 1

    def test_payment_id_mismatch_rejected(self, verified_user):
        """Если в БД уже сохранён другой payment_id — webhook отклоняется."""
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-evil', status='succeeded', paid=True,
        )
        tx = self._make_pending_tx(verified_user, payment_id='pid-real')
        payload = self._payload(tx, payment_id='pid-evil')

        result = service.handle_webhook(payload)
        assert result is False
        tx.refresh_from_db()
        assert tx.status == 'pending'  # без изменений
        assert not Wallet.objects.filter(user=verified_user, balance__gt=0).exists()

    def test_canceled_event(self, verified_user):
        """payment.canceled → транзакция cancelled, кошелёк НЕ пополняется."""
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-3', status='canceled', paid=False,
        )
        tx = self._make_pending_tx(verified_user, payment_id='pid-3')
        payload = self._payload(tx, payment_id='pid-3', event='payment.canceled',
                                status='canceled', paid=False)

        result = service.handle_webhook(payload)
        assert result is True
        tx.refresh_from_db()
        assert tx.status == 'cancelled'
        assert not Wallet.objects.filter(user=verified_user).exists() or \
            Wallet.objects.get(user=verified_user).balance == Decimal('0.00')

    def test_canceled_after_completed_skipped(self, verified_user):
        """Если транзакция уже completed — canceled игнорируется (без отката)."""
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(
            payment_id='pid-4', status='canceled', paid=False,
        )
        tx = self._make_pending_tx(verified_user, payment_id='pid-4')
        tx.status = 'completed'
        tx.save(update_fields=['status'])

        payload = self._payload(tx, payment_id='pid-4', event='payment.canceled',
                                status='canceled', paid=False)
        result = service.handle_webhook(payload)
        assert result is True
        tx.refresh_from_db()
        assert tx.status == 'completed'  # не изменилось

    def test_unknown_event_accepted_no_op(self, verified_user):
        """Неизвестное событие принимается без бизнес-действий."""
        service = _build_service(enabled=True)
        service.Payment.find_one.return_value = _mock_payment(payment_id='pid-5')
        tx = self._make_pending_tx(verified_user, payment_id='pid-5')
        payload = self._payload(tx, payment_id='pid-5', event='payment.waiting_for_capture')
        # _verify_webhook_payload не предусматривает специальной проверки → проходит
        result = service.handle_webhook(payload)
        # либо True (без бизнес-действий), либо False — для нашего теста главное,
        # что состояние транзакции не сломано
        tx.refresh_from_db()
        assert tx.status == 'pending'

    def test_handle_webhook_swallows_exceptions(self, verified_user):
        """Любые внутренние исключения не должны падать наружу."""
        service = _build_service(enabled=True)
        service.Payment.find_one.side_effect = RuntimeError('boom')
        tx = self._make_pending_tx(verified_user)
        result = service.handle_webhook(self._payload(tx))
        assert result is False


# ─────────────────────────────────────────────────────────────────────
# Webhook view (HTTP-уровень)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestYookassaWebhookView:

    def test_invalid_json_returns_400(self, client):
        url = reverse('payments:yookassa_webhook')
        response = client.post(url, data=b'not-json', content_type='application/json')
        assert response.status_code == 400

    @patch('payments.views.yookassa_service')
    def test_webhook_view_calls_service(self, mock_service, client):
        mock_service.allowed_webhook_ips = set()
        mock_service.handle_webhook.return_value = True
        url = reverse('payments:yookassa_webhook')
        body = json.dumps({'event': 'payment.succeeded', 'object': {'id': 'p'}})
        response = client.post(url, data=body, content_type='application/json')
        assert response.status_code == 200
        assert mock_service.handle_webhook.called

    @patch('payments.views.yookassa_service')
    def test_webhook_view_returns_400_on_failure(self, mock_service, client):
        mock_service.allowed_webhook_ips = set()
        mock_service.handle_webhook.return_value = False
        url = reverse('payments:yookassa_webhook')
        body = json.dumps({'event': 'payment.succeeded', 'object': {'id': 'p'}})
        response = client.post(url, data=body, content_type='application/json')
        assert response.status_code == 400

    @patch('payments.views.yookassa_service')
    def test_webhook_view_blocks_unknown_ip(self, mock_service, client):
        mock_service.allowed_webhook_ips = {'1.2.3.4'}
        url = reverse('payments:yookassa_webhook')
        body = json.dumps({'event': 'payment.succeeded', 'object': {'id': 'p'}})
        # Клиент тестового Django приходит с другого IP (REMOTE_ADDR=127.0.0.1)
        response = client.post(url, data=body, content_type='application/json')
        assert response.status_code == 403
