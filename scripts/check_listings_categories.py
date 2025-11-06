#!/usr/bin/env python
"""
Скрипт для проверки категорий у объявлений
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Listing, Game

print("=" * 60)
print("ПРОВЕРКА КАТЕГОРИЙ У ОБЪЯВЛЕНИЙ")
print("=" * 60)

# Получаем все активные объявления
active_listings = Listing.objects.filter(status='active').select_related('game', 'category')
print(f"\n✅ Всего активных объявлений: {active_listings.count()}")

# Проверяем каждое объявление
print("\nДетальная информация:")
print("-" * 60)
for listing in active_listings:
    category_info = listing.category.name if listing.category else "❌ НЕТ КАТЕГОРИИ"
    print(f"ID: {listing.id}")
    print(f"  Название: {listing.title}")
    print(f"  Игра: {listing.game.name}")
    print(f"  Категория: {category_info}")
    print()

# Подсчет объявлений без категории
no_category_count = active_listings.filter(category__isnull=True).count()
print("-" * 60)
print(f"⚠️  Объявлений без категории: {no_category_count}")

if no_category_count > 0:
    print("\n💡 РЕКОМЕНДАЦИЯ: Необходимо установить категории для этих объявлений!")

# Проверка по играм
print("\n" + "=" * 60)
print("СТАТИСТИКА ПО ИГРАМ")
print("=" * 60)

games = Game.objects.filter(is_active=True)
for game in games:
    total = Listing.objects.filter(game=game, status='active').count()
    with_category = Listing.objects.filter(game=game, status='active', category__isnull=False).count()
    without_category = total - with_category
    
    if total > 0:
        print(f"\n🎮 {game.name}:")
        print(f"   Всего объявлений: {total}")
        print(f"   С категорией: {with_category}")
        print(f"   Без категории: {without_category}")
        
        # Показываем категории
        for category in game.categories.all():
            cat_count = Listing.objects.filter(
                game=game,
                category=category,
                status='active'
            ).count()
            print(f"     └─ {category.name}: {cat_count} шт.")

print("\n" + "=" * 60)

