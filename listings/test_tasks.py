"""Тесты Celery-задач listings/tasks.py.

Покрывают warm_catalog_cache: расчёт контекста каталога и запись в кэш.
"""

from django.core.cache import cache

import pytest

from listings.models import Category, Game, Listing
from listings.tasks import warm_catalog_cache


@pytest.fixture(autouse=True)
def _flush_cache():
    """Каждому тесту — чистый кэш (signals из других тестов могут засорить)."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_warm_catalog_cache_populates_key():
    """После запуска задачи в кэше лежит games_catalog_ctx_v1."""
    Game.objects.create(name="Dota 2", slug="dota-2", is_active=True)

    result = warm_catalog_cache()

    assert "games" in result
    ctx = cache.get("games_catalog_ctx_v1")
    assert ctx is not None
    assert any(g.name == "Dota 2" for g in ctx["games"])


@pytest.mark.django_db
def test_warm_catalog_cache_counts_active_listings(seller):
    """total_listings суммирует только active-листинги."""
    game = Game.objects.create(name="CS2", slug="cs2", is_active=True)

    Listing.objects.create(
        seller=seller,
        game=game,
        title="A",
        description="d",
        price=100,
        status="active",
    )
    Listing.objects.create(
        seller=seller,
        game=game,
        title="B",
        description="d",
        price=200,
        status="active",
    )
    # sold не должен попасть в счётчик
    Listing.objects.create(
        seller=seller,
        game=game,
        title="C",
        description="d",
        price=300,
        status="sold",
    )

    warm_catalog_cache()

    ctx = cache.get("games_catalog_ctx_v1")
    assert ctx["total_listings"] == 2


@pytest.mark.django_db
def test_warm_catalog_cache_groups_alphabetically(seller):
    """alphabet_groups группирует игры по первой букве."""
    Game.objects.create(name="Apex Legends", slug="apex", is_active=True)
    Game.objects.create(name="Brawl Stars", slug="brawl", is_active=True)
    Game.objects.create(name="Borderlands", slug="borderlands", is_active=True)
    Game.objects.create(name="42 Game", slug="42-game", is_active=True)

    warm_catalog_cache()

    ctx = cache.get("games_catalog_ctx_v1")
    groups = ctx["alphabet_groups"]

    assert "A" in groups and len(groups["A"]) == 1
    assert "B" in groups and len(groups["B"]) == 2
    # Имя начинающееся с цифры → '0-9'
    assert "0-9" in groups
    assert groups["0-9"][0].name == "42 Game"


@pytest.mark.django_db
def test_warm_catalog_cache_skips_inactive_games(seller):
    """Неактивные игры не попадают в контекст."""
    Game.objects.create(name="Active", slug="active-g", is_active=True)
    Game.objects.create(name="Inactive", slug="inactive-g", is_active=False)

    warm_catalog_cache()

    ctx = cache.get("games_catalog_ctx_v1")
    names = {g.name for g in ctx["games"]}
    assert "Active" in names
    assert "Inactive" not in names


@pytest.mark.django_db
def test_warm_catalog_cache_returns_summary_string():
    """Задача возвращает текстовое summary с числом игр и категорий."""
    Game.objects.create(name="G1", slug="g1", is_active=True)
    Game.objects.create(name="G2", slug="g2", is_active=True)

    result = warm_catalog_cache()

    assert "2 games" in result
    assert "categories cached" in result
