"""
Периодические Celery-задачи листингов.
"""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def warm_catalog_cache() -> str:
    """
    Прогревает кэш каталога: рассчитывает контекст и кладёт в Redis,
    чтобы первый пользовательский запрос шёл по тёплому кэшу.

    Запускается каждые ~4 минуты Celery Beat'ом (TTL контекста = 5 минут).
    """
    from collections import OrderedDict

    from django.core.cache import cache
    from django.db.models import Count, Min, Prefetch, Q

    from listings.models import Category, Game

    categories_qs = Category.objects.filter(
        is_active=True
    ).annotate(
        listings_count=Count('listings', filter=Q(listings__status='active')),
        min_price=Min('listings__price', filter=Q(listings__status='active')),
    ).order_by('order', 'name')

    games = list(Game.objects.filter(is_active=True).prefetch_related(
        Prefetch('categories', queryset=categories_qs, to_attr='active_categories')
    ).annotate(
        listings_count=Count('listings', filter=Q(listings__status='active'))
    ).order_by('name'))

    total_listings = sum(g.listings_count or 0 for g in games)
    total_categories = sum(len(g.active_categories) for g in games)

    alphabet_groups: OrderedDict[str, list] = OrderedDict()
    for game in games:
        first_char = game.name[0].upper() if game.name else '#'
        if first_char.isdigit():
            first_char = '0-9'
        alphabet_groups.setdefault(first_char, []).append(game)

    context = {
        'games': games,
        'total_listings': total_listings,
        'total_categories': total_categories,
        'alphabet_groups': alphabet_groups,
        'alphabet_letters': list(alphabet_groups.keys()),
    }
    cache.set('games_catalog_ctx_v1', context, 600)  # 10 минут — ровно с запасом

    msg = f'warm_catalog_cache: {len(games)} games, {total_categories} categories cached'
    logger.info(msg)
    return msg
