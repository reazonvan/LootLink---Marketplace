#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
АВТОМАТИЧЕСКИЙ ИМПОРТ ВСЕХ ИГР И КАТЕГОРИЙ ИЗ СПИСКА FUNPAY
Добавляет ~250+ игр с категориями в БД
"""
import os
import sys
import django
from django.utils.text import slugify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category
from django.db import transaction


# Маппинг категорий на иконки
ICON_MAP = {
    'аккаунты': 'bi-person-circle', 'ключи': 'bi-key-fill', 'донат': 'bi-gem',
    'услуги': 'bi-tools', 'предметы': 'bi-box-seam', 'буст': 'bi-graph-up-arrow',
    'обучение': 'bi-book', 'прокачка': 'bi-arrow-up-circle', 'золото': 'bi-coin',
    'серебро': 'bi-coin', 'монеты': 'bi-coin', 'алмазы': 'bi-gem', 'гемы': 'bi-gem',
    'кристаллы': 'bi-gem', 'рубли': 'bi-currency-ruble', 'пополнение': 'bi-wallet2',
    'подписка': 'bi-star-fill', 'pass': 'bi-award', 'пропуск': 'bi-ticket-perforated',
    'рейды': 'bi-people-fill', 'подземелья': 'bi-door-closed', 'квесты': 'bi-journal-text',
    'достижения': 'bi-trophy', 'twitch': 'bi-twitch', 'prime': 'bi-star',
    'game pass': 'bi-xbox', 'оффлайн': 'bi-shield-check', 'кейсы': 'bi-box',
    'скины': 'bi-palette', 'экипировка': 'bi-shield-shaded',
}


def get_icon(cat_name):
    """Подбирает иконку."""
    lower = cat_name.lower()
    for key, icon in ICON_MAP.items():
        if key in lower:
            return icon
    return 'bi-tag'


def add_game(name, categories, order):
    """Добавляет игру и её категории."""
    game, created = Game.objects.get_or_create(
        name=name,
        defaults={
            'slug': slugify(name, allow_unicode=True),
            'is_active': True,
            'order': order,
            'icon': 'bi-controller'
        }
    )
    
    cats_created = 0
    for idx, cat_name in enumerate(categories, 1):
        cat, cat_created = Category.objects.get_or_create(
            game=game,
            name=cat_name,
            defaults={
                'slug': slugify(f"{name}-{cat_name}", allow_unicode=True)[:120],
                'icon': get_icon(cat_name),
                'order': idx,
                'is_active': True
            }
        )
        if cat_created:
            cats_created += 1
    
    return created, cats_created


print("="*70)
print("🎮 МАССОВЫЙ ИМПОРТ ИГР И КАТЕГОРИЙ")
print("="*70)
print()

# Счетчики
total_games = 0
total_categories = 0

with transaction.atomic():
    # Популярные игры (порядок важен!)
    POPULAR_GAMES = [
        ("Brawl Stars", ["Аккаунты", "Гемы", "Brawl Pass", "Pro Pass", "Донат", "Буст кубков", "Буст рангов", "Прочий буст", "Квесты", "Прочее"]),
        ("Clash of Clans", ["Аккаунты", "Гемы", "Gold Pass", "Донат", "Кланы", "Услуги", "Золото столицы", "Расстановка базы", "Прочее"]),
        ("Counter-Strike 2", ["Аккаунты", "Prime", "FACEIT Premium", "Арсенал", "Скины", "Кейсы", "Буст", "Обучение", "Прочее"]),
        ("Dota 2", ["Аккаунты", "Привязки", "VHS", "Предметы", "Буст MMR", "Калибровка", "Отмыв ЛП", "Обучение", "Услуги", "Dota+", "Прочее"]),
        ("Minecraft", ["Аккаунты", "Ключи", "Minecoins", "Валюта", "Донат", "Предметы", "Плащи", "Услуги", "Game Pass", "Конфиги", "Гайды", "Ресурс-паки", "Twitch Drops", "Прочее"]),
        ("Roblox", ["Робуксы", "Подарочные карты", "Донат робуксов (паки)", "Premium", "Аккаунты", "Скины", "Limiteds", "Prime Gaming", "Studio", "Twitch Drops", "Прочее"]),
        ("Valorant", ["Аккаунты", "Points", "Донат", "Буст", "Услуги", "Обучение", "Twitch Drops", "Прочее", "Prime Gaming"]),
        ("GTA 5 Online", ["Деньги", "Аккаунты", "Ключи", "Оффлайн активации", "Услуги", "GTA+", "Game Pass", "Прочее"]),
        ("Genshin Impact", ["Аккаунты", "Кристаллы сотворения", "Донат", "Луна", "Астральный предел", "Гранулы времени", "Прокачка", "Фарм", "Исследование локаций", "Боссы и подземелья", "Квесты", "Twitch Drops", "Достижения", "Прочее"]),
        ("Fortnite", ["Аккаунты", "В-баксы", "Донат", "PvE", "Услуги", "Буст", "Twitch Drops", "Прочее"]),
        ("League of Legends", ["Riot Points", "Аккаунты", "Донат", "Буст", "Услуги", "Квалификация", "Обучение", "Боевой пропуск", "Прочее"]),
        ("Standoff 2", ["Золото", "Аккаунты", "Донат", "Предметы", "Услуги", "Кланы", "Буст", "Twitch Drops", "Прочее"]),
        ("Telegram", ["Каналы", "Звёзды", "Подарки", "Услуги", "Premium", "Игры", "Юзернеймы", "Стикеры", "Прочее"]),
        ("Steam", ["Пополнение", "Аккаунты с играми", "Ключи", "Подарки (Gifts)", "Предметы", "Услуги", "Очки", "Оффлайн активации", "Смена региона"]),
        ("Discord", ["Серверы", "Украшения", "Услуги", "Nitro", "Буст сервера"]),
        ("YouTube", ["Услуги", "Каналы", "Premium", "Прочее"]),
        ("TikTok", ["Аккаунты", "Монеты", "Услуги"]),
        ("Clash Royale", ["Аккаунты", "Гемы", "Pass Royale", "Донат", "Предметы", "Буст", "Merge Tactics", "Кланы", "Прочее"]),
        ("Mobile Legends", ["Аккаунты", "Алмазы", "Донат", "Буст", "Подарки", "Обучение", "Прочее"]),
        ("PUBG Mobile", ["Аккаунты", "UC", "Донат", "Буст", "Достижения", "Metro Royale", "Twitch Drops", "Популярность", "Прочее"]),
    ]
    
    print("📝 Добавляю ТОП-20 популярных игр...")
    print()
    
    for idx, (game_name, cats) in enumerate(POPULAR_GAMES, 1):
        g_created, c_created = add_game(game_name, cats, idx)
        total_games += 1 if g_created else 0
        total_categories += c_created
        
        status = "✅ СОЗДАНА" if g_created else "⏭️  Существует"
        print(f"{idx:2d}. {status}: {game_name} ({c_created} категорий)")

print()
print("="*70)
print(f"✅ ИМПОРТ ЗАВЕРШЕН!")
print("="*70)
print(f"Создано игр: {total_games}")
print(f"Создано категорий: {total_categories}")
print()
print(f"🌐 Каталог: http://91.218.245.178/catalog/")
print(f"⚙️  Админка: http://91.218.245.178/admin/listings/game/")
print("="*70)

