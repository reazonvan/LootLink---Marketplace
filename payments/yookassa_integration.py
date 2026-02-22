"""
Интеграция с ЮKassa (YooMoney) для приема платежей.
Документация: https://yookassa.ru/developers/api
"""
from decimal import Decimal
import uuid
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone
from .models import Transaction
import logging

logger = logging.getLogger(__name__)


class YooKassaService:
    """
    Сервис для работы с ЮKassa API.
    """
    
    def __init__(self):
        self.shop_id = getattr(settings, 'YOOKASSA_SHOP_ID', '')
        self.secret_key = getattr(settings, 'YOOKASSA_SECRET_KEY', '')
        self.enabled = bool(self.shop_id and self.secret_key)
        self.allowed_webhook_ips = {
            ip.strip() for ip in getattr(settings, 'YOOKASSA_WEBHOOK_ALLOWED_IPS', '').split(',') if ip.strip()
        }
        
        if self.enabled:
            try:
                from yookassa import Configuration, Payment
                Configuration.account_id = self.shop_id
                Configuration.secret_key = self.secret_key
                self.Payment = Payment
            except ImportError:
                logger.warning('yookassa library not installed. Install: pip install yookassa')
                self.enabled = False
    
    def create_payment(self, user, amount, description='Пополнение баланса', return_url=None):
        """
        Создать платеж в ЮKassa.
        
        Args:
            user: Пользователь
            amount: Сумма в рублях
            description: Описание платежа
            return_url: URL для возврата после оплаты
        
        Returns:
            dict: Данные платежа с confirmation_url
        """
        if not self.enabled:
            logger.error('YooKassa не настроена')
            return {'error': 'Платежная система временно недоступна'}
        
        try:
            # Создаем транзакцию в БД
            transaction = Transaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount,
                status='pending',
                description=description,
                payment_system='yookassa'
            )
            
            # Создаем платеж в ЮKassa
            idempotence_key = str(uuid.uuid4())
            
            payment_data = {
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url or settings.SITE_URL
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "transaction_id": transaction.id,
                    "user_id": user.id
                }
            }
            
            payment = self.Payment.create(payment_data, idempotence_key)
            
            # Сохраняем данные платежа
            transaction.payment_id = payment.id
            transaction.payment_data = {
                'status': payment.status,
                'paid': payment.paid,
                'created_at': str(payment.created_at)
            }
            transaction.save()
            
            return {
                'success': True,
                'payment_id': payment.id,
                'confirmation_url': payment.confirmation.confirmation_url,
                'transaction_id': transaction.id
            }
            
        except Exception as e:
            logger.error(f'Ошибка создания платежа: {str(e)}')
            return {'error': str(e)}
    
    def check_payment(self, payment_id):
        """
        Проверить статус платежа.
        
        Args:
            payment_id: ID платежа в ЮKassa
        
        Returns:
            dict: Статус платежа
        """
        if not self.enabled:
            return {'error': 'Платежная система временно недоступна'}
        
        try:
            payment = self.Payment.find_one(payment_id)
            
            return {
                'success': True,
                'status': payment.status,
                'paid': payment.paid,
                'amount': Decimal(payment.amount.value),
                'metadata': payment.metadata
            }
        except Exception as e:
            logger.error(f'Ошибка проверки платежа {payment_id}: {str(e)}')
            return {'error': str(e)}

    @staticmethod
    def _safe_get(data, key, default=None):
        """Безопасно получить значение по ключу из dict/SDK объекта."""
        if data is None:
            return default
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    def _extract_payment_fields(self, payment_obj):
        """Нормализовать поля платежа из webhook/API объекта."""
        payment_id = self._safe_get(payment_obj, 'id')
        status = self._safe_get(payment_obj, 'status')
        paid = self._safe_get(payment_obj, 'paid')
        metadata = self._safe_get(payment_obj, 'metadata', {}) or {}
        amount_obj = self._safe_get(payment_obj, 'amount')
        amount_value = self._safe_get(amount_obj, 'value')
        currency = self._safe_get(amount_obj, 'currency')

        return {
            'id': payment_id,
            'status': status,
            'paid': paid,
            'metadata': metadata,
            'amount_value': Decimal(str(amount_value)) if amount_value is not None else None,
            'currency': currency,
        }

    def _verify_webhook_payload(self, event, webhook_payment_data):
        """
        Проверить подлинность webhook путем сверки с API YooKassa.
        Это снижает риск подделки входящего payload.
        """
        webhook_fields = self._extract_payment_fields(webhook_payment_data)
        payment_id = webhook_fields['id']
        if not payment_id:
            logger.warning('Webhook отклонен: отсутствует payment_id')
            return False

        try:
            api_payment = self.Payment.find_one(payment_id)
        except Exception as e:
            logger.error(f'Webhook verification failed: cannot fetch payment {payment_id}: {e}')
            return False

        api_fields = self._extract_payment_fields(api_payment)

        # Базовая консистентность payload <-> API
        if webhook_fields['status'] and webhook_fields['status'] != api_fields['status']:
            logger.warning(
                f'Webhook отклонен: статус не совпал payload={webhook_fields["status"]} '
                f'api={api_fields["status"]} payment_id={payment_id}'
            )
            return False

        if webhook_fields['amount_value'] is not None and webhook_fields['amount_value'] != api_fields['amount_value']:
            logger.warning(
                f'Webhook отклонен: сумма не совпала payload={webhook_fields["amount_value"]} '
                f'api={api_fields["amount_value"]} payment_id={payment_id}'
            )
            return False

        if webhook_fields['currency'] and webhook_fields['currency'] != api_fields['currency']:
            logger.warning(
                f'Webhook отклонен: валюта не совпала payload={webhook_fields["currency"]} '
                f'api={api_fields["currency"]} payment_id={payment_id}'
            )
            return False

        # Логическая проверка события
        if event == 'payment.succeeded':
            if api_fields['status'] != 'succeeded' or not api_fields['paid']:
                logger.warning(f'Webhook отклонен: payment {payment_id} не в succeeded/paid')
                return False
        elif event == 'payment.canceled':
            if api_fields['status'] != 'canceled':
                logger.warning(f'Webhook отклонен: payment {payment_id} не в canceled')
                return False

        return True
    
    def handle_webhook(self, webhook_data, request_ip=None):
        """
        Обработать webhook от ЮKassa.
        
        Args:
            webhook_data: Данные webhook
            request_ip: IP отправителя webhook
        
        Returns:
            bool: Успешность обработки
        """
        if not self.enabled:
            return False

        if self.allowed_webhook_ips and request_ip and request_ip not in self.allowed_webhook_ips:
            logger.warning(f'Webhook отклонен: IP {request_ip} не входит в whitelist')
            return False
        
        try:
            event = webhook_data.get('event')
            payment_data = webhook_data.get('object')
            if not event or not payment_data:
                logger.warning('Webhook отклонен: отсутствует event/object')
                return False

            if not self._verify_webhook_payload(event, payment_data):
                return False

            payment_fields = self._extract_payment_fields(payment_data)
            payment_id = payment_fields['id']
            metadata = payment_fields['metadata'] or {}
            transaction_id = metadata.get('transaction_id')
            if not transaction_id:
                logger.warning(f'Webhook отклонен: transaction_id отсутствует в metadata payment_id={payment_id}')
                return False

            with db_transaction.atomic():
                tx = Transaction.objects.select_for_update().get(id=transaction_id)

                # Защита от несогласованных данных/подмены связи
                if tx.payment_id and tx.payment_id != payment_id:
                    logger.warning(
                        f'Webhook отклонен: payment_id mismatch transaction_id={tx.id} '
                        f'db={tx.payment_id} incoming={payment_id}'
                    )
                    return False

                tx.payment_id = payment_id
                tx.payment_data = {
                    **(tx.payment_data or {}),
                    'webhook_event': event,
                    'webhook_status': payment_fields['status'],
                    'webhook_received_at': timezone.now().isoformat(),
                }

                if event == 'payment.succeeded':
                    # Идемпотентность: уже зачисленную транзакцию повторно не обрабатываем
                    if tx.status == 'completed':
                        tx.save(update_fields=['payment_id', 'payment_data'])
                        logger.info(f'Webhook duplicate ignored for payment {payment_id}')
                        return True

                    tx.status = 'completed'
                    tx.completed_at = timezone.now()
                    tx.save(update_fields=['payment_id', 'payment_data', 'status', 'completed_at'])

                    from .models import Wallet
                    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=tx.user)
                    wallet.balance += tx.amount
                    wallet.save(update_fields=['balance', 'updated_at'])

                    logger.info(f'Платеж {payment_id} успешно обработан и зачислен')
                    return True

                if event == 'payment.canceled':
                    if tx.status == 'completed':
                        logger.warning(
                            f'Получен canceled для уже completed transaction_id={tx.id}, пропускаем'
                        )
                        tx.save(update_fields=['payment_id', 'payment_data'])
                        return True

                    tx.status = 'cancelled'
                    tx.save(update_fields=['payment_id', 'payment_data', 'status'])
                    logger.info(f'Платеж {payment_id} отменен')
                    return True

            logger.info(f'Webhook event {event} принят без бизнес-действий')
            return True
             
        except Exception as e:
            logger.error(f'Ошибка обработки webhook: {str(e)}')
            return False


# Singleton instance
yookassa_service = YooKassaService()

