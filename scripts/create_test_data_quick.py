#!/usr/bin/env python
"""Быстрое создание тестовых данных для LootLink"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from listings.models import Game, Category, Listing
from decimal import Decimal

User = get_user_model()

# Создаём игры
games_data = [
    {'name': 'CS2', 'slug': 'cs2'},
    {'name': 'Dota 2', 'slug': 'dota-2'},
    {'name': 'Valorant', 'slug': 'valorant'},
    {'name': 'World of Warcraft', 'slug': 'wow'},
    {'name': 'Genshin Impact', 'slug': 'genshin'},
    {'name': 'FIFA 24', 'slug': 'fifa-24'},
    {'name': 'Fortnite', 'slug': 'fortnite'},
    {'name': 'League of Legends', 'slug': 'lol'},
]

print("Создаём игры...")
for game_data in games_data:
    game, created = Game.objects.get_or_create(
        slug=game_data['slug'],
        defaults={'name': game_data['name']}
    )
    if created:
        print(f"  ✓ {game.name}")

# Создаём категории
categories_data = [
    {'name': 'Аккаунты', 'slug': 'accounts'},
    {'name': 'Валюта', 'slug': 'currency'},
    {'name': 'Предметы', 'slug': 'items'},
    {'name': 'Буст', 'slug': 'boost'},
]

print("\nСоздаём категории...")
for cat_data in categories_data:
    cat, created = Category.objects.get_or_create(
        slug=cat_data['slug'],
        defaults={'name': cat_data['name']}
    )
    if created:
        print(f"  ✓ {cat.name}")

# Создаём тестовых пользователей
print("\nСоздаём пользователей...")
users = []
for i in range(1, 4):
    username = f'user{i}'
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': f'{username}@test.com',
            'is_active': True,
        }
    )
    if created:
        user.set_password('test123')
        user.save()
        print(f"  ✓ {username}")
    users.append(user)

# Создаём объявления
print("\nСоздаём объявления...")
cs2 = Game.objects.get(slug='cs2')
dota = Game.objects.get(slug='dota-2')
valorant = Game.objects.get(slug='valorant')

accounts_cat = Category.objects.get(slug='accounts')
currency_cat = Category.objects.get(slug='currency')
items_cat = Category.objects.get(slug='items')

listings_data = [
    {
        'title': 'Аккаунт CS2 Global Elite',
        'description': 'Аккаунт с рангом Global Elite, 2000+ часов игры',
        'price': Decimal('5000.00'),
        'game': cs2,
        'category': accounts_cat,
        'seller': users[0],
    },
    {
        'title': 'CS2 Скины на 10000₽',
        'description': 'Набор скинов для CS2',
        'price': Decimal('8500.00'),
        'game': cs2,
        'category': items_cat,
        'seller': users[1],
    },
    {
        'title': 'Аккаунт Dota 2 Immortal',
        'description': 'Аккаунт с рангом Immortal',
        'price': Decimal('7000.00'),
        'game': dota,
        'category': accounts_cat,
        'seller': users[0],
    },
    {
        'title': 'Dota 2 Arcana набор',
        'description': 'Набор из 5 Arcana предметов',
        'price': Decimal('12000.00'),
        'game': dota,
        'category': items_cat,
        'seller': users[2],
    },
    {
        'title': 'Valorant Radiant аккаунт',
        'description': 'Аккаунт с рангом Radiant',
        'price': Decimal('6000.00'),
        'game': valorant,
        'category': accounts_cat,
        'seller': users[1],
    },
]

for listing_data in listings_data:
    listing, created = Listing.objects.get_or_create(
        title=listing_data['title'],
        defaults=listing_data
    )
    if created:
        print(f"  ✓ {listing.title}")

print("\n✅ Тестовые данные созданы!")
print(f"Игры: {Game.objects.count()}")
print(f"Категории: {Category.objects.count()}")
print(f"Пользователи: {User.objects.count()}")
print(f"Объявления: {Listing.objects.count()}")
