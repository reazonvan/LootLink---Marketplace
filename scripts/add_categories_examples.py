#!/usr/bin/env python
"""
Скрипт добавления примеров категорий для популярных игр
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category

# Примеры категорий для разных игр
CATEGORIES = {
    'Brawl Stars': [
        {'name': 'Аккаунты', 'icon': 'bi-person-circle', 'order': 1},
        {'name': 'Гемы', 'icon': 'bi-gem', 'order': 2},
        {'name': 'Brawl Pass', 'icon': 'bi-trophy', 'order': 3},
        {'name': 'Pro Pass', 'icon': 'bi-award', 'order': 4},
        {'name': 'Донат', 'icon': 'bi-currency-dollar', 'order': 5},
        {'name': 'Буст кубков', 'icon': 'bi-graph-up-arrow', 'order': 6},
        {'name': 'Буст рангов', 'icon': 'bi-arrow-up-circle', 'order': 7},
        {'name': 'Прочий буст', 'icon': 'bi-rocket-takeoff', 'order': 8},
        {'name': 'Квесты', 'icon': 'bi-list-check', 'order': 9},
        {'name': 'Прочее', 'icon': 'bi-three-dots', 'order': 10},
    ],
    'Steam': [
        {'name': 'Пополнение', 'icon': 'bi-wallet2', 'order': 1},
        {'name': 'Аккаунты с играми', 'icon': 'bi-person-badge', 'order': 2},
        {'name': 'Ключи', 'icon': 'bi-key', 'order': 3},
        {'name': 'Подарки (Gifts)', 'icon': 'bi-gift', 'order': 4},
        {'name': 'Предметы', 'icon': 'bi-box-seam', 'order': 5},
        {'name': 'Услуги', 'icon': 'bi-gear', 'order': 6},
        {'name': 'Очки', 'icon': 'bi-coin', 'order': 7},
        {'name': 'Оффлайн активации', 'icon': 'bi-shield-check', 'order': 8},
        {'name': 'Смена региона', 'icon': 'bi-globe', 'order': 9},
    ],
    'CS:GO': [
        {'name': 'Скины оружия', 'icon': 'bi-crosshair', 'order': 1},
        {'name': 'Ножи', 'icon': 'bi-knife', 'order': 2},
        {'name': 'Перчатки', 'icon': 'bi-hand-index-thumb', 'order': 3},
        {'name': 'Аккаунты', 'icon': 'bi-person-circle', 'order': 4},
        {'name': 'Кейсы', 'icon': 'bi-box', 'order': 5},
        {'name': 'Услуги буста', 'icon': 'bi-graph-up', 'order': 6},
    ],
    'Dota 2': [
        {'name': 'Арканы', 'icon': 'bi-lightning', 'order': 1},
        {'name': 'Скины', 'icon': 'bi-palette', 'order': 2},
        {'name': 'Сеты', 'icon': 'bi-collection', 'order': 3},
        {'name': 'Аккаунты', 'icon': 'bi-person-circle', 'order': 4},
        {'name': 'Буст MMR', 'icon': 'bi-arrow-up', 'order': 5},
        {'name': 'Калибровка', 'icon': 'bi-speedometer', 'order': 6},
    ],
}

def add_categories():
    """Добавление категорий для игр"""
    
    print('=' * 60)
    print('  Добавление категорий для игр')
    print('=' * 60)
    print()
    
    added = 0
    skipped = 0
    
    for game_name, categories in CATEGORIES.items():
        try:
            game = Game.objects.get(name=game_name)
            print(f'📦 Игра: {game_name}')
            
            for cat_data in categories:
                # Проверка существования
                if Category.objects.filter(game=game, name=cat_data['name']).exists():
                    print(f'  ⏭️  {cat_data["name"]} - уже существует')
                    skipped += 1
                    continue
                
                # Создание категории
                category = Category.objects.create(
                    game=game,
                    name=cat_data['name'],
                    icon=cat_data['icon'],
                    order=cat_data['order']
                )
                print(f'  ✅ {cat_data["name"]} - добавлена')
                added += 1
            
            print()
            
        except Game.DoesNotExist:
            print(f'⚠️  Игра "{game_name}" не найдена - пропускаем')
            print()
            continue
    
    print('=' * 60)
    print(f'✅ Добавлено категорий: {added}')
    print(f'⏭️  Пропущено (уже существуют): {skipped}')
    print('=' * 60)
    print()
    print('Теперь перейдите в админ-панель для просмотра:')
    print('  http://91.218.245.178/admin/listings/category/')
    print()

if __name__ == '__main__':
    add_categories()

