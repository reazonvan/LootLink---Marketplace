"""Сигналы листингов: инвалидация кэша каталога при изменениях.

Кэш каталога (`games_catalog_ctx_v1`) и фрагменты шаблона живут 5 минут.
A3: на активном маркетплейсе листинги создаются/обновляются ежеминутно,
без debounce 5-минутный кэш фактически не работает. Решение:
- Game/Category изменения (редкие, важные) → инвалидация сразу.
- Listing изменения (частые) → debounce 60 секунд через lock-ключ.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Game, Listing

CATALOG_CACHE_KEYS = ("games_catalog_ctx_v1",)

TEMPLATE_FRAGMENT_KEYS = (
    "template.cache.catalog_alphabet_v1.d41d8cd98f00b204e9800998ecf8427e",
    "template.cache.catalog_games_v1.d41d8cd98f00b204e9800998ecf8427e",
    "template.cache.catalog_alphabet_v2.d41d8cd98f00b204e9800998ecf8427e",
    "template.cache.catalog_games_v2.d41d8cd98f00b204e9800998ecf8427e",
)

# A3: debounce — между инвалидациями каталога минимум 60 сек.
# Один lock-ключ → 100 параллельных Listing.save() сбросят кэш один раз.
LISTING_INVALIDATION_DEBOUNCE = 60
LISTING_INVALIDATION_LOCK_KEY = "catalog_invalidation_pending_v1"


def invalidate_catalog_cache() -> None:
    """Сбрасывает кэш каталога. Используется для Game/Category — без debounce."""
    cache.delete_many(CATALOG_CACHE_KEYS + TEMPLATE_FRAGMENT_KEYS)


def invalidate_catalog_cache_debounced() -> None:
    """Сбрасывает кэш каталога не чаще раза в LISTING_INVALIDATION_DEBOUNCE секунд.

    Используется для Listing.save/delete — высокочастотные события.
    add(...) возвращает True только если ключа не было; внутри окна — no-op.
    """
    if cache.add(LISTING_INVALIDATION_LOCK_KEY, "1", LISTING_INVALIDATION_DEBOUNCE):
        invalidate_catalog_cache()


@receiver(post_save, sender=Game)
@receiver(post_delete, sender=Game)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def _invalidate_on_taxonomy_change(sender, **kwargs) -> None:
    invalidate_catalog_cache()


@receiver(post_save, sender=Listing)
@receiver(post_delete, sender=Listing)
def _invalidate_on_listing_change(sender, instance, **kwargs) -> None:
    """A3: debounced — counts на каталоге могут отставать до 60 сек."""
    invalidate_catalog_cache_debounced()
