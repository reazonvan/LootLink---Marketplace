"""
Тесты глобального поиска /search/.

Проверяем оба бэкенда — PostgreSQL FTS (prod) и SQLite icontains (dev).
search_views.global_search детектирует connection.vendor и переключает логику.
"""

from decimal import Decimal

from django.urls import reverse

import pytest


@pytest.mark.django_db
class TestGlobalSearch:
    """Тесты /search/ — текстовый поиск + фильтры."""

    def test_search_page_loads_empty(self, client):
        """Пустой запрос — страница грузится с пустым результатом."""
        response = client.get(reverse("listings:global_search"))
        assert response.status_code == 200
        assert "page_obj" in response.context

    def test_search_by_title(self, client, seller, game, listing_factory):
        """Поиск по тексту находит совпадения в title."""
        listing_factory(seller, title="Уникальный меч дракона")
        listing_factory(seller, title="Обычный щит")

        response = client.get(reverse("listings:global_search"), {"q": "дракон"})
        assert response.status_code == 200
        results = list(response.context["page_obj"])
        titles = [l.title for l in results]
        assert any("дракон" in t.lower() for t in titles)
        assert not any("щит" in t.lower() for t in titles)

    def test_search_by_description(self, client, seller, listing_factory):
        """Поиск находит совпадения в description."""
        listing_factory(
            seller,
            title="Артефакт",
            description="Очень редкий предмет с уникальной механикой.",
        )
        listing_factory(seller, title="Обычный", description="Простой предмет.")

        response = client.get(reverse("listings:global_search"), {"q": "редкий"})
        assert response.status_code == 200
        results = list(response.context["page_obj"])
        assert len(results) >= 1
        assert any("Артефакт" == l.title for l in results)

    def test_search_filter_by_game(self, client, seller, game, game_factory, listing_factory):
        """Фильтр по slug игры."""
        game2 = game_factory(name="Other")
        l1 = listing_factory(seller)
        from listings.models import Listing

        l2 = Listing.objects.create(
            seller=seller,
            game=game2,
            title="Другая игра",
            description="Описание для другой игры.",
            price=Decimal("100"),
            status="active",
        )

        response = client.get(reverse("listings:global_search"), {"game": game.slug})
        assert response.status_code == 200
        results = list(response.context["page_obj"])
        assert l1 in results
        assert l2 not in results

    def test_search_filter_by_price_range(self, client, seller, listing_factory):
        """Фильтр min/max price."""
        cheap = listing_factory(seller, price=Decimal("50"))
        mid = listing_factory(seller, price=Decimal("300"))
        expensive = listing_factory(seller, price=Decimal("1000"))

        response = client.get(
            reverse("listings:global_search"),
            {
                "min_price": "100",
                "max_price": "500",
            },
        )
        results = list(response.context["page_obj"])
        assert cheap not in results
        assert mid in results
        assert expensive not in results

    def test_search_invalid_price_does_not_500(self, client):
        """Кривое значение цены не должно ломать страницу."""
        response = client.get(
            reverse("listings:global_search"),
            {
                "min_price": "abc",
                "max_price": "<<<",
            },
        )
        assert response.status_code == 200

    def test_search_only_active_listings(self, client, seller, listing_factory):
        """В выдачу попадают только active листинги."""
        active = listing_factory(seller, title="Active item")
        sold = listing_factory(seller, title="Sold item", status="sold")

        response = client.get(reverse("listings:global_search"), {"q": "item"})
        results = list(response.context["page_obj"])
        assert active in results
        assert sold not in results

    def test_search_sort_price_asc(self, client, seller, listing_factory):
        """Сортировка по возрастанию цены."""
        l_high = listing_factory(seller, title="High", price=Decimal("500"))
        l_low = listing_factory(seller, title="Low", price=Decimal("50"))

        response = client.get(reverse("listings:global_search"), {"sort": "price_asc"})
        results = list(response.context["page_obj"])
        assert results.index(l_low) < results.index(l_high)

    def test_search_pagination(self, client, seller, listing_factory):
        """Пагинация работает (24 на страницу)."""
        for i in range(30):
            listing_factory(seller, title=f"Item {i}")

        page1 = client.get(reverse("listings:global_search"))
        page2 = client.get(reverse("listings:global_search"), {"page": 2})

        assert page1.status_code == 200
        assert page2.status_code == 200
        assert page1.context["page_obj"].number == 1
        assert page2.context["page_obj"].number == 2


@pytest.mark.django_db
class TestSearchSuggest:
    """Тесты /api/search/suggest/ — autocomplete API."""

    def test_empty_query_returns_empty(self, client):
        """Пустой запрос — пустые списки."""
        response = client.get(reverse("listings:search_suggest"))
        assert response.status_code == 200
        data = response.json()
        assert data == {"games": [], "listings": []}

    def test_short_query_returns_empty(self, client):
        """1 символ — пусто (минимум 2 символа)."""
        response = client.get(reverse("listings:search_suggest"), {"q": "a"})
        data = response.json()
        assert data == {"games": [], "listings": []}

    def test_suggest_finds_games(self, client, game_factory):
        """Находит совпадения в названиях игр."""
        game_factory(name="Counter-Strike", slug="counter-strike")
        game_factory(name="Apex Legends", slug="apex-legends")

        response = client.get(reverse("listings:search_suggest"), {"q": "counter"})
        data = response.json()
        names = [g["name"] for g in data["games"]]
        assert "Counter-Strike" in names
        assert "Apex Legends" not in names

    def test_suggest_finds_listings(self, client, seller, listing_factory):
        """Находит совпадения в названиях листингов."""
        listing_factory(seller, title="Уникальный меч дракона")
        listing_factory(seller, title="Обычный щит")

        response = client.get(reverse("listings:search_suggest"), {"q": "дракон"})
        data = response.json()
        titles = [l["title"] for l in data["listings"]]
        assert any("дракон" in t.lower() for t in titles)
        assert not any("щит" in t.lower() for t in titles)

    def test_suggest_excludes_inactive_listings(self, client, seller, listing_factory):
        """Sold/inactive листинги не попадают в подсказки."""
        listing_factory(seller, title="Active sword")
        listing_factory(seller, title="Sold sword", status="sold")

        response = client.get(reverse("listings:search_suggest"), {"q": "sword"})
        data = response.json()
        titles = [l["title"] for l in data["listings"]]
        assert "Active sword" in titles
        assert "Sold sword" not in titles

    def test_suggest_limits_results(self, client, seller, listing_factory):
        """Максимум 5 листингов и 5 игр."""
        for i in range(10):
            listing_factory(seller, title=f"Sword {i}")

        response = client.get(reverse("listings:search_suggest"), {"q": "sword"})
        data = response.json()
        assert len(data["listings"]) <= 5

    def test_suggest_serializes_decimal_price(self, client, seller, listing_factory):
        """Цена сериализуется как строка (Decimal не падает в JSON)."""
        listing_factory(seller, title="Item one", price=Decimal("123.45"))

        response = client.get(reverse("listings:search_suggest"), {"q": "item"})
        data = response.json()
        assert any(l.get("price") == "123.45" for l in data["listings"])
