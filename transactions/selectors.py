"""
Запросы к БД transactions-модуля (read/query операции).

HackSoft styleguide:
    - selectors.py — только чтение БД, никаких side-effects.
    - select_related/prefetch_related — внутри селекторов, не во views.
"""
from __future__ import annotations

from typing import Optional

from django.db.models import QuerySet

from .models import PurchaseRequest, Review


# ---------------------------------------------------------------------------
# PurchaseRequest
# ---------------------------------------------------------------------------

def user_purchase_requests(
    *,
    user,
    role: str = 'buyer',
    status: Optional[str] = None,
) -> QuerySet[PurchaseRequest]:
    """
    Запросы на покупку, где ``user`` участвует как покупатель/продавец.

    Args:
        user: Пользователь.
        role: ``'buyer'`` или ``'seller'``.
        status: Фильтр по статусу (опционально).
    """
    if role not in ('buyer', 'seller'):
        raise ValueError(f'Unsupported role: {role!r}')

    qs = (
        PurchaseRequest.objects
        .filter(**{role: user})
        .select_related('listing', 'buyer', 'seller')
        .order_by('-created_at')
    )
    if status:
        qs = qs.filter(status=status)
    return qs


def get_purchase_request_for_participant(
    *,
    request_id: int,
    user,
) -> PurchaseRequest:
    """
    Получить запрос на покупку, где ``user`` — buyer или seller.

    Raises:
        PurchaseRequest.DoesNotExist: Если запроса нет или user не участник.
    """
    return (
        PurchaseRequest.objects
        .select_related('listing', 'buyer', 'seller')
        .filter(pk=request_id)
        .filter(buyer=user) | (
            PurchaseRequest.objects
            .select_related('listing', 'buyer', 'seller')
            .filter(pk=request_id, seller=user)
        )
    ).get()


def can_user_leave_review(*, purchase_request: PurchaseRequest, user) -> bool:
    """
    Может ли пользователь оставить отзыв по сделке.

    Условия: сделка завершена и пользователь ещё не оставлял отзыв.
    """
    if purchase_request.status != 'completed':
        return False
    return not Review.objects.filter(
        purchase_request=purchase_request,
        reviewer=user,
    ).exists()
