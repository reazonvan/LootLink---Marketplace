"""Регресс-тесты дашборда аналитики продавца.

Покрывают ранее непокрытую и сломанную view ``accounts:analytics_dashboard``:

1. Страница падала с HTTP 500 (``NoReverseMatch``): шаблон ссылался на
   несуществующие имена ``export_sales_csv`` / ``export_listings_csv`` /
   ``export_reviews_csv``. Правильный маршрут — ``accounts:export_data?type=...``.
2. Данные графика теперь отдаются через безопасный ``json_script`` вместо
   небезопасного ``{{ ...|safe }}`` в инлайн-скрипте.
3. Для типа ``reviews`` во view добавлена недостающая ветка экспорта.
"""

from django.urls import reverse

import pytest


@pytest.mark.django_db
def test_analytics_dashboard_renders_with_json_script(authenticated_client):
    """Страница открывается (200) и данные графика — в json_script-теге."""
    resp = authenticated_client.get(reverse("accounts:analytics_dashboard"))

    assert resp.status_code == 200
    content = resp.content.decode()
    assert 'id="sales-chart-data"' in content
    assert "sales_by_day_json" not in content


@pytest.mark.django_db
@pytest.mark.parametrize("export_type", ["sales", "listings", "reviews", "purchases"])
def test_analytics_export_returns_csv(authenticated_client, export_type):
    """Каждый тип экспорта отдаёт CSV (200), а не падает NoReverseMatch."""
    resp = authenticated_client.get(reverse("accounts:export_data"), {"type": export_type})

    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
