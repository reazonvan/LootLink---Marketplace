#!/usr/bin/env python
"""Быстрое создание тестовых данных для LootLink (dev/UI-тесты).

Запуск:
    # standalone:
    python scripts/create_test_data_quick.py
    # или через docker:
    docker compose exec web python scripts/create_test_data_quick.py

Создаёт:
    - admin/admin12345 (superuser)
    - seller_demo/demo12345 (продавец, verified)
    - buyer_demo/demo12345 (покупатель, verified)
    - 5 игр, 4 категории, 6 объявлений
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from decimal import Decimal

from django.contrib.auth import get_user_model

from listings.models import Category, Game, Listing

User = get_user_model()

# Superuser
admin, created = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@lootlink.local", "is_staff": True, "is_superuser": True},
)
if created or not admin.has_usable_password():
    admin.set_password("admin12345")
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    print("[+] admin/admin12345 (superuser)")
else:
    print("[=] admin (already exists)")

# Тестовые пользователи
for username in ["seller_demo", "buyer_demo"]:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": f"{username}@lootlink.local", "is_active": True},
    )
    if created:
        user.set_password("demo12345")
        user.save()
        user.profile.is_verified = True
        user.profile.save(update_fields=["is_verified"])
        print(f"[+] {username}/demo12345 (verified)")
    else:
        print(f"[=] {username} (already exists)")

# Игры
games_data = [
    {"name": "CS2", "slug": "cs2"},
    {"name": "Dota 2", "slug": "dota-2"},
    {"name": "Valorant", "slug": "valorant"},
    {"name": "World of Warcraft", "slug": "wow"},
    {"name": "Genshin Impact", "slug": "genshin"},
    {"name": "FIFA 24", "slug": "fifa-24"},
    {"name": "Fortnite", "slug": "fortnite"},
    {"name": "League of Legends", "slug": "lol"},
]

for game_data in games_data:
    game, created = Game.objects.get_or_create(
        slug=game_data["slug"],
        defaults={"name": game_data["name"], "is_active": True},
    )
    if created:
        print(f"[+] Game: {game.name}")

# Категории (создаются для каждой игры отдельно — Category.game ForeignKey)
categories_template = [
    {"name": "Аккаунты", "icon": "bi-person-badge"},
    {"name": "Валюта", "icon": "bi-coin"},
    {"name": "Предметы", "icon": "bi-gem"},
    {"name": "Буст", "icon": "bi-graph-up-arrow"},
]

for game in Game.objects.all():
    for cat_data in categories_template:
        cat, created = Category.objects.get_or_create(
            game=game,
            name=cat_data["name"],
            defaults={"icon": cat_data["icon"], "is_active": True},
        )
        if created:
            print(f"[+] Category: {game.name} -> {cat.name}")

# Объявления (от seller_demo)
seller = User.objects.get(username="seller_demo")
cs2 = Game.objects.get(slug="cs2")
dota = Game.objects.get(slug="dota-2")
valorant = Game.objects.get(slug="valorant")
wow = Game.objects.get(slug="wow")
genshin = Game.objects.get(slug="genshin")


def cat_for(game, name):
    return Category.objects.get(game=game, name=name)


acc_cs2 = cat_for(cs2, "Аккаунты")
items_cs2 = cat_for(cs2, "Предметы")
acc_dota = cat_for(dota, "Аккаунты")
acc_valorant = cat_for(valorant, "Аккаунты")
cur_wow = cat_for(wow, "Валюта")
boost_genshin = cat_for(genshin, "Буст")

listings_data = [
    {
        "title": "Аккаунт CS2 Global Elite, 2000+ часов",
        "description": "Global Elite ранг, инвентарь на 5000₽, 2000+ часов. Steam Guard.",
        "price": Decimal("5000.00"),
        "game": cs2,
        "category": acc_cs2,
        "seller": seller,
    },
    {
        "title": "CS2 Скины: AK-47 Redline + AWP Asiimov",
        "description": "Набор скинов из 5 предметов на ~10000₽. Передача через Steam Trade.",
        "price": Decimal("8500.00"),
        "game": cs2,
        "category": items_cs2,
        "seller": seller,
    },
    {
        "title": "Аккаунт Dota 2 Immortal MMR 6500",
        "description": "Чистый аккаунт без бана, MMR 6500, все герои разблокированы.",
        "price": Decimal("7000.00"),
        "game": dota,
        "category": acc_dota,
        "seller": seller,
    },
    {
        "title": "Valorant Radiant аккаунт + 12 скинов",
        "description": "Ранг Radiant, 12 скинов оружия, 8 агентов разблокированы.",
        "price": Decimal("6000.00"),
        "game": valorant,
        "category": acc_valorant,
        "seller": seller,
    },
    {
        "title": "WoW Gold 100k Альянс/Орда",
        "description": "Игровая валюта World of Warcraft. Передача через аукцион.",
        "price": Decimal("1500.00"),
        "game": wow,
        "category": cur_wow,
        "seller": seller,
    },
    {
        "title": "Буст Genshin Impact Spiral Abyss 36★",
        "description": "Прохождение Spiral Abyss на 36 звёзд за 24 часа.",
        "price": Decimal("2500.00"),
        "game": genshin,
        "category": boost_genshin,
        "seller": seller,
    },
]

for data in listings_data:
    listing, created = Listing.objects.get_or_create(title=data["title"], defaults=data)
    if created:
        print(f"[+] Listing: {listing.title}")

print("\n--- Готово ---")
print(f"Users:      {User.objects.count()}")
print(f"Games:      {Game.objects.count()}")
print(f"Categories: {Category.objects.count()}")
print(f"Listings:   {Listing.objects.count()}")
print("\nЛогины для UI-тестов:")
print("  admin       / admin12345  (superuser)")
print("  seller_demo / demo12345   (продавец, verified)")
print("  buyer_demo  / demo12345   (покупатель, verified)")
