"""
Celery задачи для payments приложения.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


@shared_task(name='payments.auto_release_escrow')
def auto_release_escrow():
    """
    Автоматическое освобождение escrow по истечении срока.
    Запускается периодически (например, каждый час).
    """
    from .models import Escrow
    from core.models_audit import SecurityAuditLog
    
    now = timezone.now()
    
    # Находим все escrow с истекшим сроком
    expired_escrows = Escrow.objects.filter(
        status='funded',
        release_deadline__lte=now
    ).select_related('buyer', 'seller', 'purchase_request')
    
    released_count = 0
    errors_count = 0
    
    for escrow in expired_escrows:
        try:
            with transaction.atomic():
                # Освобождаем средства продавцу
                escrow.release_to_seller()
                
                # Логируем в аудит
                SecurityAuditLog.log(
                    action_type='escrow_release',
                    user=escrow.buyer,
                    description=f'Автоматическое освобождение escrow #{escrow.id} '
                               f'для сделки #{escrow.purchase_request.id}',
                    risk_level='low',
                    metadata={
                        'escrow_id': escrow.id,
                        'purchase_request_id': escrow.purchase_request.id,
                        'amount': str(escrow.amount),
                        'auto_release': True
                    }
                )
                
                released_count += 1
                logger.info(f'Auto-released escrow #{escrow.id} for amount {escrow.amount}')
                
        except Exception as e:
            errors_count += 1
            logger.error(f'Error auto-releasing escrow #{escrow.id}: {str(e)}')
            
            # Логируем ошибку в аудит
            SecurityAuditLog.log(
                action_type='suspicious_activity',
                user=escrow.buyer,
                description=f'Ошибка автоматического освобождения escrow #{escrow.id}: {str(e)}',
                risk_level='high',
                metadata={
                    'escrow_id': escrow.id,
                    'error': str(e)
                }
            )
    
    logger.info(
        f'Auto-release escrow task completed: '
        f'{released_count} released, {errors_count} errors'
    )
    
    return {
        'released': released_count,
        'errors': errors_count,
        'timestamp': now.isoformat()
    }


@shared_task(name='payments.check_pending_withdrawals')
def check_pending_withdrawals():
    """
    Проверка и уведомление о pending withdrawals.
    Отправляет уведомления администратору о необработанных выводах.
    """
    from .models import Withdrawal
    from datetime import timedelta
    
    # Находим выводы старше 24 часов в статусе pending
    threshold = timezone.now() - timedelta(hours=24)
    
    pending_withdrawals = Withdrawal.objects.filter(
        status='pending',
        created_at__lte=threshold
    ).select_related('user')
    
    if pending_withdrawals.exists():
        count = pending_withdrawals.count()
        total_amount = sum(w.amount for w in pending_withdrawals)
        
        logger.warning(
            f'Found {count} pending withdrawals older than 24 hours. '
            f'Total amount: {total_amount} RUB'
        )
        
        # Здесь можно отправить email администратору
        # send_mail_to_admin(...)
        
        return {
            'count': count,
            'total_amount': float(total_amount)
        }
    
    return {'count': 0, 'total_amount': 0}


@shared_task(name='payments.cleanup_old_transactions')
def cleanup_old_transactions():
    """
    Архивирование старых транзакций (старше 1 года).
    Для соответствия требованиям хранения данных.
    """
    from .models import Transaction
    from datetime import timedelta
    
    # Транзакции старше 1 года
    threshold = timezone.now() - timedelta(days=365)
    
    old_transactions = Transaction.objects.filter(
        created_at__lte=threshold,
        status='completed'
    )
    
    count = old_transactions.count()
    
    # В реальной системе здесь была бы логика архивирования
    # (экспорт в отдельную таблицу или файл)
    
    logger.info(f'Found {count} transactions older than 1 year for archiving')
    
    return {'count': count}

