"""
Селекторы для `listings/` — слой чтения из БД.

Используют `select_related`/`prefetch_related` для оптимизации каталога.
В каталоге листингов критичны N+1-запросы — все запросы должны быть оптимизированы.

См. HackSoft styleguide: https://github.com/HackSoftware/Django-Styleguide#selectors

ВАЖНО: этот файл создан как скелет в рамках P3 рефакторинга.
"""

from typing import TYPE_CHECKING, Optional

from django.db.models import QuerySet

if TYPE_CHECKING:
    from accounts.models import CustomUser
    from listings.models import Game, Listing


def listing_list_active() -> "QuerySet[Listing]":
    """Активные объявления с подгруженным seller, game для каталога."""
    from listings.models import Listing

    return (
        Listing.objects.filter(status="active")
        .select_related("seller", "seller__profile", "game")
        .order_by("-created_at")
    )


def listing_list_by_seller(*, seller: "CustomUser") -> "QuerySet[Listing]":
    """Все объявления продавца, включая проданные."""
    from listings.models import Listing

    return Listing.objects.filter(seller=seller).select_related("game").order_by("-created_at")


def listing_get_by_pk(*, pk: int) -> "Optional[Listing]":
    """Получить объявление по pk с подгруженными связями."""
    from listings.models import Listing

    return Listing.objects.filter(pk=pk).select_related("seller", "seller__profile", "game").first()
