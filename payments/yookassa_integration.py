"""
Интеграция с ЮKassa (YooMoney) для приема платежей.
Документация: https://yookassa.ru/developers/api
"""
from decimal import Decimal
import uuid
from django.conf import settings
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
    
    def handle_webhook(self, webhook_data):
        """
        Обработать webhook от ЮKassa.
        
        Args:
            webhook_data: Данные webhook
        
        Returns:
            bool: Успешность обработки
        """
        if not self.enabled:
            return False
        
        try:
            event = webhook_data.get('event')
            payment_data = webhook_data.get('object')
            
            if event == 'payment.succeeded':
                payment_id = payment_data['id']
                metadata = payment_data.get('metadata', {})
                transaction_id = metadata.get('transaction_id')
                
                if transaction_id:
                    # Обновляем транзакцию
                    transaction = Transaction.objects.get(id=transaction_id)
                    transaction.status = 'completed'
                    transaction.mark_completed()
                    
                    # Пополняем баланс
                    from .models import Wallet
                    wallet, _ = Wallet.objects.get_or_create(user=transaction.user)
                    wallet.balance += transaction.amount
                    wallet.save()
                    
                    logger.info(f'Платеж {payment_id} успешно обработан')
                    return True
            
            elif event == 'payment.canceled':
                payment_id = payment_data['id']
                metadata = payment_data.get('metadata', {})
                transaction_id = metadata.get('transaction_id')
                
                if transaction_id:
                    transaction = Transaction.objects.get(id=transaction_id)
                    transaction.status = 'cancelled'
                    transaction.save()
                    
                    logger.info(f'Платеж {payment_id} отменен')
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f'Ошибка обработки webhook: {str(e)}')
            return False


# Singleton instance
yookassa_service = YooKassaService()

