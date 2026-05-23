"""Создаём реалистичные демо-данные для скриншотов."""

import io
import os
import sys

import django

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\LootLink---Marketplace")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from listings.models import Category, Game, Listing

User = get_user_model()

# Базовые продавцы
sellers_data = [
    ("cs_master", "cs_master@example.com", "Алексей К.", 4.9, 287),
    ("skin_trader", "skin_trader@example.com", "Дмитрий М.", 4.8, 142),
    ("pro_gamer", "pro_gamer@example.com", "Игорь В.", 4.7, 95),
    ("dota_hero", "dota_hero@example.com", "Артём С.", 4.6, 68),
    ("wow_legend", "wow_legend@example.com", "Михаил Р.", 4.95, 412),
]
sellers = []
for username, email, full_name, rating, deals in sellers_data:
    u, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "is_active": True, "first_name": full_name.split()[0]},
    )
    sellers.append(u)
    print(f"Seller: {u.username} ({'new' if created else 'exists'})")

# Найдём ключевые игры
key_games = {}
for name in [
    "Counter-Strike 2",
    "Dota 2",
    "PUBG",
    "World of Warcraft",
    "Genshin Impact",
    "Mobile Legends",
    "Final Fantasy XIV",
    "Rust",
]:
    g = Game.objects.filter(name__icontains=name).first()
    if g:
        key_games[name] = g

print(f"\nКлючевые игры: {list(key_games.keys())}")


# Категории-универсалы (нам нужно найти любую категорию-Скины и т.п.)
# Просто берём любую существующую категорию для каждой игры
def get_any_category(game):
    return Category.objects.filter(game=game).first()


# Демо-листинги
demo_listings = [
    # (game_name, title, price, description)
    (
        "Counter-Strike 2",
        "AK-47 | Поверхностная закалка (StatTrak™)",
        "2450.00",
        "Закалённое в боях, Float 0.27. Стикеры: iBUYPOWER (Holo) Katowice 2014.",
    ),
    (
        "Counter-Strike 2",
        "AWP | Драконий шторм",
        "18600.00",
        "Прямо с завода, Float 0.012. Один из самых редких скинов AWP.",
    ),
    (
        "Counter-Strike 2",
        "Karambit | Доплер Ruby",
        "82400.00",
        "Прямо с завода, фаза Ruby. Float 0.008. Доплер серии 4-го поколения.",
    ),
    (
        "Counter-Strike 2",
        "M4A4 | Asiimov",
        "11200.00",
        "После полевых испытаний, Float 0.21. Хорошее состояние.",
    ),
    (
        "Dota 2",
        "Аркана Pudge — Feast of Abscession",
        "3200.00",
        "Аркана для Pudge. Включает кастомные звуки и анимации.",
    ),
    (
        "PUBG",
        "Set «Ghillie» — Premium Crate",
        "1250.00",
        "Полный сет маскировки. Получен из премиум-ящика PUBG.",
    ),
    (
        "Genshin Impact",
        "Аккаунт AR 58 — 5★ Хутао + Райдэн + Кадзуха",
        "24800.00",
        "Прокачанный аккаунт. AR 58, World Level 8. Несколько 5★ персонажей.",
    ),
    (
        "Mobile Legends",
        "Аккаунт Mythical Glory — 15 героев 5★",
        "8900.00",
        "Аккаунт с рангом Mythical Glory. 15 героев в максимальной прокачке.",
    ),
    (
        "World of Warcraft",
        "Аккаунт WoW Mythic 600 — Холодная Сталь",
        "9850.00",
        "Mythic+ 600 рейтинг. Полный сет 478+ ilvl.",
    ),
]

created_count = 0
for game_name, title, price, desc in demo_listings:
    game = key_games.get(game_name)
    if not game:
        # Попробуем без точного совпадения
        game = Game.objects.filter(name__icontains=game_name.split()[0]).first()
    if not game:
        print(f"❌ Игра не найдена: {game_name}")
        continue
    cat = get_any_category(game)
    if not cat:
        print(f"❌ Категория не найдена для: {game.name}")
        continue
    seller = random.choice(sellers)
    listing, created = Listing.objects.get_or_create(
        title=title,
        defaults={
            "seller": seller,
            "game": game,
            "category": cat,
            "price": Decimal(price),
            "description": desc,
            "status": "active",
        },
    )
    if created:
        created_count += 1
        print(f"✓ Создано: {title[:60]} — {price}₽")

print(f"\nСоздано листингов: {created_count}")
print(f"Всего активных листингов: {Listing.objects.filter(status='active').count()}")
