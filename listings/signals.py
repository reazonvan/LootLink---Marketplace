"""
Сигналы листингов: инвалидация кэша каталога при изменениях
Game/Category/Listing.

Кэш каталога (`games_catalog_ctx_v1`) и фрагменты шаблона
(`catalog_alphabet_v1`, `catalog_games_v1`) живут 5 минут.
Любая правка структурных данных — сбрасывает кэш сразу.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Game, Listing

CATALOG_CACHE_KEYS = ("games_catalog_ctx_v1",)

# Префиксы фрагментов template-cache (`{% cache %}` префиксует ключи как
# `template.cache.<name>.<args_hash>`). Без аргументов хэш одинаковый,
# поэтому удаляем по полному ключу.
TEMPLATE_FRAGMENT_KEYS = (
    # v1 ключи — оставлены на переходный период (старые поды могли успеть
    # положить их перед деплоем). Истекут сами через 5 мин.
    "template.cache.catalog_alphabet_v1.d41d8cd98f00b204e9800998ecf8427e",
    "template.cache.catalog_games_v1.d41d8cd98f00b204e9800998ecf8427e",
    # v2 — текущая версия (после удаления категорий из inline-render).
    "template.cache.catalog_alphabet_v2.d41d8cd98f00b204e9800998ecf8427e",
    "template.cache.catalog_games_v2.d41d8cd98f00b204e9800998ecf8427e",
)


def invalidate_catalog_cache() -> None:
    cache.delete_many(CATALOG_CACHE_KEYS + TEMPLATE_FRAGMENT_KEYS)


@receiver(post_save, sender=Game, dispatch_uid="listings.taxonomy_save_game")
@receiver(post_delete, sender=Game, dispatch_uid="listings.taxonomy_delete_game")
@receiver(post_save, sender=Category, dispatch_uid="listings.taxonomy_save_category")
@receiver(post_delete, sender=Category, dispatch_uid="listings.taxonomy_delete_category")
def _invalidate_on_taxonomy_change(sender, **kwargs) -> None:
    invalidate_catalog_cache()


@receiver(post_save, sender=Listing, dispatch_uid="listings.listing_save")
@receiver(post_delete, sender=Listing, dispatch_uid="listings.listing_delete")
def _invalidate_on_listing_change(sender, instance, **kwargs) -> None:
    # listings_count и min_price на каталоге зависят от состояния листингов.
    invalidate_catalog_cache()
