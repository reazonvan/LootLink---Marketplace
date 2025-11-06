#!/usr/bin/env python
"""
Скрипт для автоматического назначения категорий объявлениям
на основе ключевых слов в названии
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Listing

print("=" * 60)
print("АВТОМАТИЧЕСКОЕ НАЗНАЧЕНИЕ КАТЕГОРИЙ")
print("=" * 60)

# Получаем все активные объявления без категории
listings_without_category = Listing.objects.filter(category__isnull=True)
print(f"\n📊 Найдено объявлений без категории: {listings_without_category.count()}")

# Словарь ключевых слов для определения категории
CATEGORY_KEYWORDS = {
    'аккаунт': ['аккаунт', 'account', 'акк'],
    'валюта': ['валюта', 'золото', 'серебро', 'деньги', 'монеты', 'coins', 'алмазы', 'гемы', 'gems', 'звёзды', 'diamonds'],
    'буст': ['буст', 'boost', 'прокачка', 'leveling'],
    'услуги': ['услуги', 'service', 'обучение'],
    'донат': ['донат', 'donate', 'пополнение'],
    'предмет': ['предмет', 'item', 'вещь'],
    'ключ': ['ключ', 'key', 'ключи', 'keys'],
}

updated_count = 0
print("\n" + "=" * 60)
print("ОБРАБОТКА ОБЪЯВЛЕНИЙ:")
print("=" * 60 + "\n")

for listing in listings_without_category:
    title_lower = listing.title.lower()
    game_categories = listing.game.categories.filter(is_active=True)
    
    # Пытаемся найти подходящую категорию
    best_category = None
    
    # Проверяем ключевые слова
    for cat_key, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                # Ищем категорию, в названии которой есть это ключевое слово
                for category in game_categories:
                    if keyword in category.name.lower() or cat_key in category.name.lower():
                        best_category = category
                        break
                if best_category:
                    break
        if best_category:
            break
    
    # Если не нашли по ключевым словам, берем первую категорию или "Прочее"
    if not best_category and game_categories.exists():
        # Попытка найти категорию "Прочее" или "Прочий"
        prochee = game_categories.filter(name__icontains='прочее').first() or \
                  game_categories.filter(name__icontains='прочий').first()
        
        if prochee:
            best_category = prochee
        else:
            # Берем первую доступную категорию
            best_category = game_categories.first()
    
    if best_category:
        listing.category = best_category
        listing.save(update_fields=['category'])
        updated_count += 1
        print(f"✅ ID: {listing.id} | {listing.game.name} | '{listing.title}' → {best_category.name}")
    else:
        print(f"⚠️  ID: {listing.id} | {listing.game.name} | '{listing.title}' → НЕТ ДОСТУПНЫХ КАТЕГОРИЙ!")

print("\n" + "=" * 60)
print(f"✅ Обновлено объявлений: {updated_count}")
print(f"⚠️  Осталось без категории: {Listing.objects.filter(category__isnull=True).count()}")
print("=" * 60)

