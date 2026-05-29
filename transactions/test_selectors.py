"""Тесты transactions/selectors.py — read-слой запросов на покупку."""

import pytest

from transactions.models import PurchaseRequest, Review
from transactions.selectors import (
    can_user_leave_review,
    get_purchase_request_for_participant,
    user_purchase_requests,
)

# ─────────────────────────────────────────────────────────────────────
# user_purchase_requests
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_user_purchase_requests_buyer_role(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """role='buyer' возвращает только запросы где пользователь — покупатель."""
    listing = listing_factory(seller)
    my_pr = purchase_request_factory(listing, buyer)
    # PR где seller является seller (а не buyer) — не должен попасть
    qs = user_purchase_requests(user=buyer, role="buyer")

    pks = list(qs.values_list("pk", flat=True))
    assert my_pr.pk in pks


@pytest.mark.django_db
def test_user_purchase_requests_seller_role(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """role='seller' возвращает только продавцовские запросы."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer)

    qs = user_purchase_requests(user=seller, role="seller")
    assert pr.pk in list(qs.values_list("pk", flat=True))


@pytest.mark.django_db
def test_user_purchase_requests_filters_by_status(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """Фильтр status пропускает только записи в нужном состоянии."""
    listing = listing_factory(seller)
    pending = purchase_request_factory(listing, buyer, status="pending")
    completed = purchase_request_factory(listing, buyer, status="completed")

    pks_pending = list(
        user_purchase_requests(user=buyer, status="pending").values_list("pk", flat=True),
    )
    assert pending.pk in pks_pending
    assert completed.pk not in pks_pending


@pytest.mark.django_db
def test_user_purchase_requests_unsupported_role_raises():
    """Невалидная роль → ValueError."""
    with pytest.raises(ValueError, match="role"):
        user_purchase_requests(user=None, role="moderator")


# ─────────────────────────────────────────────────────────────────────
# get_purchase_request_for_participant
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_pr_for_participant_returns_buyer(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """buyer получает свой запрос."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer)

    result = get_purchase_request_for_participant(request_id=pr.pk, user=buyer)
    assert result.pk == pr.pk


@pytest.mark.django_db
def test_get_pr_for_participant_returns_seller(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """seller тоже видит запрос как участник."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer)

    result = get_purchase_request_for_participant(request_id=pr.pk, user=seller)
    assert result.pk == pr.pk


@pytest.mark.django_db
def test_get_pr_for_participant_raises_for_outsider(
    buyer,
    seller,
    user_factory,
    listing_factory,
    purchase_request_factory,
):
    """Посторонний → DoesNotExist (IDOR-защита на уровне селектора)."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer)
    outsider = user_factory()

    with pytest.raises(PurchaseRequest.DoesNotExist):
        get_purchase_request_for_participant(request_id=pr.pk, user=outsider)


# ─────────────────────────────────────────────────────────────────────
# can_user_leave_review
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_can_user_leave_review_false_when_not_completed(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """Неоконченная сделка → нельзя оставить отзыв."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer, status="pending")
    assert can_user_leave_review(purchase_request=pr, user=buyer) is False


@pytest.mark.django_db
def test_can_user_leave_review_true_for_completed(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """Completed + нет существующего отзыва → можно."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer, status="completed")
    assert can_user_leave_review(purchase_request=pr, user=buyer) is True


@pytest.mark.django_db
def test_can_user_leave_review_false_if_already_reviewed(
    buyer,
    seller,
    listing_factory,
    purchase_request_factory,
):
    """Если отзыв уже оставлен — нельзя."""
    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer, status="completed")
    Review.objects.create(
        purchase_request=pr,
        reviewer=buyer,
        reviewed_user=seller,
        rating=5,
        comment="ok",
    )
    assert can_user_leave_review(purchase_request=pr, user=buyer) is False
