"""Тесты для listings/selectors.py — слой чтения каталога."""

import pytest

from listings.selectors import listing_get_by_pk, listing_list_active, listing_list_by_seller


@pytest.mark.django_db
def test_listing_list_active_filters_status(seller, listing_factory):
    """Возвращает только status="active", не sold/cancelled."""
    active = listing_factory(seller, title="A", status="active")
    sold = listing_factory(seller, title="S", status="sold")
    cancelled = listing_factory(seller, title="C", status="cancelled")

    pks = set(listing_list_active().values_list("pk", flat=True))

    assert active.pk in pks
    assert sold.pk not in pks
    assert cancelled.pk not in pks


@pytest.mark.django_db
def test_listing_list_active_orders_newest_first(seller, listing_factory):
    """Сортировка -created_at."""
    import time

    older = listing_factory(seller, title="old", status="active")
    time.sleep(0.01)
    newer = listing_factory(seller, title="new", status="active")

    pks = list(listing_list_active().values_list("pk", flat=True))
    assert pks.index(newer.pk) < pks.index(older.pk)


@pytest.mark.django_db
def test_listing_list_by_seller_includes_all_statuses(
    seller,
    buyer,
    listing_factory,
):
    """Все объявления продавца (любой статус), но только его."""
    s_active = listing_factory(seller, title="s-active", status="active")
    s_sold = listing_factory(seller, title="s-sold", status="sold")
    foreign = listing_factory(buyer, title="b-active", status="active")

    pks = set(listing_list_by_seller(seller=seller).values_list("pk", flat=True))

    assert {s_active.pk, s_sold.pk} <= pks
    assert foreign.pk not in pks


@pytest.mark.django_db
def test_listing_get_by_pk_returns_object(active_listing):
    """Существующий pk возвращает объект с подгруженными связями."""
    result = listing_get_by_pk(pk=active_listing.pk)
    assert result is not None
    assert result.pk == active_listing.pk


@pytest.mark.django_db
def test_listing_get_by_pk_returns_none_for_missing():
    """Несуществующий pk → None, без исключения."""
    assert listing_get_by_pk(pk=999999) is None
