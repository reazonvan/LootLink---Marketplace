"""Тесты core/seo_utils.py — генерация OG и Schema.org разметки."""

from decimal import Decimal

import pytest

from core.seo_utils import get_og_tags, get_organization_schema, get_product_schema

# ─────────────────────────────────────────────────────────────────────
# get_og_tags
# ─────────────────────────────────────────────────────────────────────


def test_get_og_tags_minimal():
    """Только title и description — без image и url."""
    tags = get_og_tags("Title", "Description")
    assert tags["og:type"] == "website"
    assert tags["og:title"] == "Title"
    assert tags["og:description"] == "Description"
    assert "og:image" not in tags
    assert "og:url" not in tags
    # Twitter Card всегда summary_large_image
    assert tags["twitter:card"] == "summary_large_image"


def test_get_og_tags_with_image_adds_dimensions():
    """С image заполняется og:image + size 1200x630 + twitter:image."""
    tags = get_og_tags("T", "D", image="https://x.io/a.jpg")
    assert tags["og:image"] == "https://x.io/a.jpg"
    assert tags["og:image:width"] == "1200"
    assert tags["og:image:height"] == "630"
    assert tags["twitter:image"] == "https://x.io/a.jpg"


def test_get_og_tags_with_url():
    """С url заполняется og:url."""
    tags = get_og_tags("T", "D", url="https://x.io/page")
    assert tags["og:url"] == "https://x.io/page"


# ─────────────────────────────────────────────────────────────────────
# get_product_schema
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_product_schema_basic(active_listing):
    """Базовая разметка Product без image/рейтинга."""
    active_listing.seller.profile.rating = Decimal("0")
    active_listing.seller.profile.save()

    schema = get_product_schema(active_listing)
    assert schema["@type"] == "Product"
    assert schema["name"] == active_listing.title
    assert schema["offers"]["price"] == str(active_listing.price)
    assert schema["offers"]["priceCurrency"] == "RUB"
    assert schema["offers"]["availability"] == "https://schema.org/InStock"
    assert "image" not in schema
    assert "aggregateRating" not in schema


@pytest.mark.django_db
def test_get_product_schema_inactive_out_of_stock(listing_factory, seller):
    """status='sold' → availability=OutOfStock."""
    seller.profile.rating = Decimal("0")
    seller.profile.save()
    listing = listing_factory(seller, status="sold")

    schema = get_product_schema(listing)
    assert schema["offers"]["availability"] == "https://schema.org/OutOfStock"


@pytest.mark.django_db
def test_get_product_schema_with_rating(active_listing):
    """rating>0 заполняет aggregateRating."""
    active_listing.seller.profile.rating = Decimal("4.5")
    active_listing.seller.profile.total_sales = 12
    active_listing.seller.profile.save()

    schema = get_product_schema(active_listing)
    assert "aggregateRating" in schema
    assert schema["aggregateRating"]["ratingValue"] == "4.5"
    assert schema["aggregateRating"]["ratingCount"] == "12"


# ─────────────────────────────────────────────────────────────────────
# get_organization_schema
# ─────────────────────────────────────────────────────────────────────


def test_get_organization_schema_constant():
    """Возвращает фиксированную разметку организации."""
    schema = get_organization_schema()
    assert schema["@type"] == "Organization"
    assert schema["name"] == "LootLink"
    assert "url" in schema
    assert schema["contactPoint"]["@type"] == "ContactPoint"
