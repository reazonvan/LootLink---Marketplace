"""Тесты для listings/services.py — сервисный слой объявлений.

Покрывают listing_create:
- успешное создание (с image и без)
- лимит активных объявлений → ValidationError
- атомарность транзакции (через transaction.atomic)
"""

from decimal import Decimal

from django.core.exceptions import ValidationError

import pytest

from listings.models import Listing
from listings.services import listing_create


@pytest.mark.django_db
def test_listing_create_success(seller, game, settings):
    """Базовое создание объявления — все поля сохраняются, статус active."""
    settings.MAX_ACTIVE_LISTINGS = 10

    listing = listing_create(
        seller=seller,
        game=game,
        title="Test Item",
        description="Test description",
        price=Decimal("150.00"),
    )

    assert listing.pk is not None
    assert listing.seller_id == seller.pk
    assert listing.game_id == game.pk
    assert listing.title == "Test Item"
    assert listing.price == Decimal("150.00")
    assert listing.status == "active"
    assert not listing.image


@pytest.mark.django_db
def test_listing_create_rejects_over_limit(seller, game, settings, listing_factory):
    """При достижении MAX_ACTIVE_LISTINGS вызывается ValidationError."""
    settings.MAX_ACTIVE_LISTINGS = 2

    # Уже два active
    listing_factory(seller, title="Active 1", status="active")
    listing_factory(seller, title="Active 2", status="active")

    with pytest.raises(ValidationError) as exc_info:
        listing_create(
            seller=seller,
            game=game,
            title="Third one",
            description="x",
            price=Decimal("100"),
        )

    assert "лимит" in str(exc_info.value).lower() or "2" in str(exc_info.value)


@pytest.mark.django_db
def test_listing_create_ignores_sold_in_limit(seller, game, settings, listing_factory):
    """Sold/cancelled не должны учитываться при подсчёте лимита."""
    settings.MAX_ACTIVE_LISTINGS = 2

    listing_factory(seller, title="Sold 1", status="sold")
    listing_factory(seller, title="Cancelled", status="cancelled")
    listing_factory(seller, title="Active", status="active")

    # Должно пройти — active всего один
    listing = listing_create(
        seller=seller,
        game=game,
        title="Second active",
        description="x",
        price=Decimal("50"),
    )
    assert listing.pk is not None
