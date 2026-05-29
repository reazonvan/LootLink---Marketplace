"""Тесты core/mixins.py — оптимизаторы N+1 querysets."""

import pytest

from core.mixins import (
    ConversationOptimizedMixin,
    ListingOptimizedMixin,
    OptimizedQueryMixin,
    PurchaseRequestOptimizedMixin,
    ReviewOptimizedMixin,
    optimize_conversation_queryset,
    optimize_listing_queryset,
    optimize_purchase_queryset,
    optimize_review_queryset,
)

# ─────────────────────────────────────────────────────────────────────
# OptimizedQueryMixin
# ─────────────────────────────────────────────────────────────────────


class _FakeParent:
    def __init__(self, queryset):
        self._qs = queryset

    def get_queryset(self):
        return self._qs


@pytest.mark.django_db
def test_optimized_query_mixin_applies_select_related(active_listing):
    """select_related_fields превращается в .select_related() на queryset."""
    from listings.models import Listing

    class V(OptimizedQueryMixin, _FakeParent):
        select_related_fields = ["seller", "game"]

    view = V(Listing.objects.all())
    qs = view.get_queryset()

    # Запрашиваем 1 листинг и проверяем — никакого N+1
    listing = qs.get(pk=active_listing.pk)
    # Если select_related сработал — оба поля уже загружены, .seller и .game
    # не вызовут extra query. Достаточно проверить, что get_queryset
    # возвращает Listing-QuerySet с настроенной optimization.
    assert listing.pk == active_listing.pk
    # query.select_related словарь содержит наши поля
    assert "seller" in qs.query.select_related
    assert "game" in qs.query.select_related


@pytest.mark.django_db
def test_optimized_query_mixin_applies_prefetch_related(active_listing):
    """prefetch_related_fields превращается в .prefetch_related()."""
    from listings.models import Listing

    class V(OptimizedQueryMixin, _FakeParent):
        prefetch_related_fields = ["favorites"]

    view = V(Listing.objects.all())
    qs = view.get_queryset()
    # _prefetch_related_lookups содержит наши поля
    assert "favorites" in qs._prefetch_related_lookups


# ─────────────────────────────────────────────────────────────────────
# Preset mixins
# ─────────────────────────────────────────────────────────────────────


def test_listing_optimized_mixin_has_seller_game_category():
    assert "seller" in ListingOptimizedMixin.select_related_fields
    assert "game" in ListingOptimizedMixin.select_related_fields
    assert "category" in ListingOptimizedMixin.select_related_fields


def test_purchase_request_optimized_mixin_has_chain_keys():
    fields = PurchaseRequestOptimizedMixin.select_related_fields
    assert "listing" in fields
    assert "listing__game" in fields
    assert "buyer" in fields
    assert "seller" in fields


def test_conversation_optimized_mixin_has_participants():
    fields = ConversationOptimizedMixin.select_related_fields
    assert "participant1" in fields
    assert "participant2" in fields
    assert "listing" in fields


def test_review_optimized_mixin_has_users():
    fields = ReviewOptimizedMixin.select_related_fields
    assert "reviewer" in fields
    assert "reviewed_user" in fields


# ─────────────────────────────────────────────────────────────────────
# optimize_*_queryset functions
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_optimize_listing_queryset_adds_select_related(active_listing):
    from listings.models import Listing

    qs = optimize_listing_queryset(Listing.objects.all())
    assert "seller" in qs.query.select_related
    assert "game" in qs.query.select_related


@pytest.mark.django_db
def test_optimize_purchase_queryset(buyer, seller, listing_factory, purchase_request_factory):
    from transactions.models import PurchaseRequest

    listing = listing_factory(seller)
    purchase_request_factory(listing, buyer)

    qs = optimize_purchase_queryset(PurchaseRequest.objects.all())
    assert "listing" in qs.query.select_related
    assert "buyer" in qs.query.select_related


@pytest.mark.django_db
def test_optimize_conversation_queryset(buyer, seller, conversation_factory):
    from chat.models import Conversation

    conversation_factory(buyer, seller)

    qs = optimize_conversation_queryset(Conversation.objects.all())
    assert "participant1" in qs.query.select_related
    assert "participant2" in qs.query.select_related


@pytest.mark.django_db
def test_optimize_review_queryset(buyer, seller, listing_factory, purchase_request_factory):
    from transactions.models import PurchaseRequest, Review

    listing = listing_factory(seller)
    pr = purchase_request_factory(listing, buyer, status="completed")
    Review.objects.create(
        purchase_request=pr,
        reviewer=buyer,
        reviewed_user=seller,
        rating=5,
        comment="x",
    )

    qs = optimize_review_queryset(Review.objects.all())
    assert "reviewer" in qs.query.select_related
    assert "reviewed_user" in qs.query.select_related
