"""
Celery задачи для payments приложения.

Phase 13: задачи помечены acks_late=True и идемпотентны.
Релиз эскроу защищён двойной проверкой статуса под select_for_update,
поэтому повторный запуск/retry не может задвоить перевод средств.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='payments.auto_release_escrow',
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def auto_release_escrow(self):
    """
    Автоматическое освобождение escrow по истечении срока.
    Запускается периодически (например, каждый час).

    Идемпотентность:
        - Каждый escrow обрабатывается в собственной транзакции с
          select_for_update(), что гарантирует эксклюзивный доступ.
        - Перед release_to_seller() выполняется double-check на
          status == 'funded'. Если статус уже изменён (другим воркером,
          параллельным release или предыдущим неудачным retry, который
          всё-таки закоммитил изменение), задача безопасно пропускает запись.
        - acks_late + retry даёт at-least-once семантику без задвоения денег.
    """
    from .models import Escrow
    from core.models_audit import SecurityAuditLog

    now = timezone.now()

    # Находим все escrow с истекшим сроком.
    # values_list('id') — чтобы не держать большие select_related в памяти
    # и брать select_for_update() уже в каждой отдельной транзакции.
    expired_ids = list(
        Escrow.objects.filter(
            status='funded',
            release_deadline__lte=now,
        ).values_list('id', flat=True)
    )

    released_count = 0
    skipped_count = 0
    errors_count = 0
    last_exception = None

    for escrow_id in expired_ids:
        try:
            with transaction.atomic():
                # Берём блокировку. Если параллельный воркер уже обработал —
                # после коммита статус будет уже не 'funded'.
                escrow = (
                    Escrow.objects
                    .select_for_update()
                    .select_related('buyer', 'seller', 'purchase_request')
                    .get(id=escrow_id)
                )

                # Double-check после блокировки: задача идемпотентна.
                if escrow.status != 'funded':
                    skipped_count += 1
                    logger.info(
                        f'Skipping escrow #{escrow.id}: status={escrow.status} '
                        f'(уже обработан другим воркером/retry)'
                    )
                    continue

                # Освобождаем средства продавцу. release_to_seller сам
                # использует свою atomic-блокировку кошельков, что корректно
                # вкладывается в текущую транзакцию (savepoint).
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
                        'auto_release': True,
                    },
                )

                released_count += 1
                logger.info(
                    f'Auto-released escrow #{escrow.id} for amount {escrow.amount}'
                )

        except Escrow.DoesNotExist:
            # Эскроу удалён между выборкой id и блокировкой — не критично.
            skipped_count += 1
            logger.warning(
                f'Escrow #{escrow_id} исчез между select и select_for_update'
            )
            continue

        except Exception as e:
            errors_count += 1
            last_exception = e
            logger.exception(
                f'Error auto-releasing escrow #{escrow_id}: {str(e)}'
            )

            # Аудит должен быть отдельной транзакцией: если упала основная,
            # запись о ней всё равно сохранится.
            try:
                with transaction.atomic():
                    SecurityAuditLog.log(
                        action_type='suspicious_activity',
                        user=None,
                        description=(
                            f'Ошибка автоматического освобождения '
                            f'escrow #{escrow_id}: {str(e)}'
                        ),
                        risk_level='high',
                        metadata={
                            'escrow_id': escrow_id,
                            'error': str(e),
                        },
                    )
            except Exception as log_err:  # pragma: no cover — защита от каскада
                logger.exception(f'Не удалось записать audit log: {log_err}')

    logger.info(
        f'Auto-release escrow task completed: '
        f'{released_count} released, {skipped_count} skipped, '
        f'{errors_count} errors'
    )

    # Если были ошибки — пробуем retry. Идемпотентность гарантирует, что
    # уже обработанные эскроу не будут перевыпущены повторно.
    if errors_count and last_exception is not None:
        try:
            raise self.retry(exc=last_exception)
        except self.MaxRetriesExceededError:
            logger.warning(
                'auto_release_escrow: исчерпан лимит retry, '
                f'errors_count={errors_count}'
            )

    return {
        'released': released_count,
        'skipped': skipped_count,
        'errors': errors_count,
        'timestamp': now.isoformat(),
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

