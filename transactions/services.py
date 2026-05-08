"""
Бизнес-логика модуля сделок (PurchaseRequest state machine).

HackSoft styleguide:
    - services.py — для всех write/state-change операций.
    - kwargs-only вызовы.
    - Все state-переходы атомарны + select_for_update().
    - Уведомления через NotificationService — после успешного коммита.
"""
from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from listings.models import Listing
from .models import PurchaseRequest


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Доменные исключения
# ---------------------------------------------------------------------------

class PurchaseRequestStateError(ValidationError):
    """Невозможно выполнить переход состояния PurchaseRequest."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notify(callable_):
    """
    Запустить уведомление после коммита текущей транзакции.

    Если транзакции нет (вне atomic) — выполнится сразу.
    """
    transaction.on_commit(callable_)


# ---------------------------------------------------------------------------
# Создание запроса
# ---------------------------------------------------------------------------

@transaction.atomic
def create_purchase_request(
    *,
    listing: Listing,
    buyer,
    message: str = '',
) -> PurchaseRequest:
    """
    Создать запрос на покупку.

    Проверяет:
        - покупатель != продавец;
        - объявление доступно (`is_available()`);
        - нет существующего активного запроса (pending/accepted) от этого покупателя.

    Raises:
        PurchaseRequestStateError: При нарушении любой из инвариант.
    """
    if listing.seller_id == buyer.pk:
        raise PurchaseRequestStateError('Нельзя купить собственное объявление.')

    if not listing.is_available():
        raise PurchaseRequestStateError('Это объявление больше не доступно.')

    existing = PurchaseRequest.objects.filter(
        listing=listing,
        buyer=buyer,
        status__in=['pending', 'accepted'],
    ).first()
    if existing is not None:
        raise PurchaseRequestStateError('У вас уже есть активный запрос на это объявление.')

    pr = PurchaseRequest.objects.create(
        listing=listing,
        buyer=buyer,
        seller=listing.seller,
        message=message,
        status='pending',
    )

    def _on_commit():
        from core.services import NotificationService
        NotificationService.notify_purchase_request(pr)

    _notify(_on_commit)

    logger.info(
        'PurchaseRequest created id=%s listing_id=%s buyer_id=%s',
        pr.pk, listing.pk, buyer.pk,
    )
    return pr


# ---------------------------------------------------------------------------
# State-переходы
# ---------------------------------------------------------------------------

@transaction.atomic
def accept_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Принять запрос на покупку (продавец).

    Переход: ``pending -> accepted``. Объявление переходит в ``reserved``.
    Выполняется под select_for_update — защита от двойного accept.
    """
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.seller_id != user.pk:
        raise PermissionDenied('Только продавец может принять запрос.')
    if pr.status != 'pending':
        raise PurchaseRequestStateError('Этот запрос уже обработан.')

    pr.status = 'accepted'
    pr.save(update_fields=['status'])

    pr.listing.status = 'reserved'
    pr.listing.save(update_fields=['status'])

    def _on_commit():
        from core.services import NotificationService
        NotificationService.notify_request_accepted(pr)

    _notify(_on_commit)

    logger.info('PurchaseRequest accepted id=%s seller_id=%s', pr.pk, user.pk)
    return pr


@transaction.atomic
def reject_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """Отклонить запрос на покупку (продавец). Переход: ``pending -> rejected``."""
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.seller_id != user.pk:
        raise PermissionDenied('Только продавец может отклонить запрос.')
    if pr.status != 'pending':
        raise PurchaseRequestStateError('Этот запрос уже обработан.')

    pr.status = 'rejected'
    pr.save(update_fields=['status'])

    def _on_commit():
        from core.services import NotificationService
        NotificationService.notify_request_rejected(pr)

    _notify(_on_commit)

    logger.info('PurchaseRequest rejected id=%s seller_id=%s', pr.pk, user.pk)
    return pr


@transaction.atomic
def complete_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Завершить сделку (продавец). Переход: ``accepted -> completed``.

    Делегирует обновление статистики профилей атомарной операции в
    ``PurchaseRequest.complete()``.
    """
    from django.db.models import F
    from django.utils import timezone
    from accounts.models import Profile

    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.seller_id != user.pk:
        raise PermissionDenied('Только продавец может завершить сделку.')
    if pr.status != 'accepted':
        raise PurchaseRequestStateError('Сделка должна быть сначала принята.')

    pr.status = 'completed'
    pr.completed_at = timezone.now()
    pr.save(update_fields=['status', 'completed_at'])

    pr.listing.status = 'sold'
    pr.listing.save(update_fields=['status'])

    Profile.objects.filter(user=pr.seller).update(total_sales=F('total_sales') + 1)
    Profile.objects.filter(user=pr.buyer).update(total_purchases=F('total_purchases') + 1)

    def _on_commit():
        from core.services import NotificationService
        NotificationService.notify_deal_completed(pr)

    _notify(_on_commit)

    logger.info('PurchaseRequest completed id=%s seller_id=%s', pr.pk, user.pk)
    return pr


@transaction.atomic
def cancel_purchase_request(*, request_id: int, user) -> PurchaseRequest:
    """
    Отменить запрос (покупатель).

    Допустимо в статусах ``pending``/``accepted``. Если объявление было
    зарезервировано (accepted) — возвращаем его в active.
    """
    pr = PurchaseRequest.objects.select_for_update().get(pk=request_id)

    if pr.buyer_id != user.pk:
        raise PermissionDenied('Только покупатель может отменить запрос.')
    if pr.status in ('completed', 'cancelled'):
        raise PurchaseRequestStateError('Этот запрос нельзя отменить.')

    pr.status = 'cancelled'
    pr.save(update_fields=['status'])

    if pr.listing.status == 'reserved':
        pr.listing.status = 'active'
        pr.listing.save(update_fields=['status'])

    logger.info('PurchaseRequest cancelled id=%s buyer_id=%s', pr.pk, user.pk)
    return pr
