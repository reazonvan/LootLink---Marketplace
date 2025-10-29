#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для добавления игр и категорий из списка Funpay
Автоматически создает slug, подбирает иконки
"""
import os
import sys
import django
from django.utils.text import slugify

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category
from django.db import transaction


# Маппинг категорий на иконки Bootstrap Icons
CATEGORY_ICONS = {
    'аккаунты': 'bi-person-circle',
    'ключи': 'bi-key-fill',
    'донат': 'bi-gem',
    'услуги': 'bi-tools',
    'предметы': 'bi-box-seam',
    'буст': 'bi-graph-up-arrow',
    'обучение': 'bi-book',
    'прокачка': 'bi-arrow-up-circle',
    'золото': 'bi-coin',
    'серебро': 'bi-coin',
    'монеты': 'bi-coin',
    'алмазы': 'bi-gem',
    'гемы': 'bi-gem',
    'кристаллы': 'bi-gem',
    'рубли': 'bi-currency-ruble',
    'доллары': 'bi-currency-dollar',
    'пополнение': 'bi-wallet2',
    'подписка': 'bi-star-fill',
    'premium': 'bi-star-fill',
    'pass': 'bi-award',
    'пропуск': 'bi-ticket-perforated',
    'рейды': 'bi-people-fill',
    'подземелья': 'bi-door-closed',
    'квесты': 'bi-journal-text',
    'достижения': 'bi-trophy',
    'twitch': 'bi-twitch',
    'prime': 'bi-star',
    'game pass': 'bi-xbox',
    'оффлайн': 'bi-shield-check',
    'кейсы': 'bi-box',
    'скины': 'bi-palette',
    'экипировка': 'bi-shield-shaded',
    'прочее': 'bi-three-dots',
}


def get_icon_for_category(category_name):
    """Подбирает иконку на основе названия категории."""
    name_lower = category_name.lower()
    
    # Ищем точное совпадение
    for keyword, icon in CATEGORY_ICONS.items():
        if keyword in name_lower:
            return icon
    
    # По умолчанию
    return 'bi-tag'


# Полный список игр от пользователя (сохранен в отдельный файл из-за размера)
# Загружаем из файла
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAMES_LIST_FILE = os.path.join(SCRIPT_DIR, 'funpay_games_list.txt')

# Если файла нет, используем встроенные данные для теста
if os.path.exists(GAMES_LIST_FILE):
    with open(GAMES_LIST_FILE, 'r', encoding='utf-8') as f:
        GAMES_DATA = f.read()
else:
    print(f"⚠️  Файл {GAMES_LIST_FILE} не найден. Используйте встроенный список.")
    GAMES_DATA = ""  # Будет заполнен ниже


def parse_games_list(text):
    """Парсит список игр и категорий."""
    games = []
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Пропускаем заголовки букв (A, B, C и т.д.)
        if len(line) <= 3 and (line.isalpha() or line.isdigit() or line in ['А', 'В', 'Г', 'Д', 'К', 'Л', 'М', 'О', 'П', 'Р', 'Т', 'Ш', '0', '2', '7', '8']):
            i += 1
            continue
        
        # Название игры
        game_name = line
        i += 1
        
        # Следующая строка - категории
        if i < len(lines):
            next_line = lines[i]
            # Проверяем что это не заголовок буквы и не название следующей игры
            if len(next_line) > 3 and not (len(next_line) <= 3 and next_line.isalpha()):
                categories = next_line.split()
                games.append({
                    'name': game_name,
                    'categories': categories
                })
                i += 1
            else:
                # Игра без категорий
                games.append({
                    'name': game_name,
                    'categories': []
                })
        else:
            games.append({
                'name': game_name,
                'categories': []
            })
    
    return games


def add_games_to_db(games_data):
    """Добавляет игры и категории в БД."""
    
    print("="*60)
    print(f"📝 Добавление {len(games_data)} игр в базу данных")
    print("="*60)
    print()
    
    created_games = 0
    created_categories = 0
    errors = []
    
    with transaction.atomic():
        for idx, game_data in enumerate(games_data, start=1):
            game_name = game_data['name']
            categories_list = game_data['categories']
            
            try:
                # Создаем игру
                game, created = Game.objects.get_or_create(
                    name=game_name,
                    defaults={
                        'slug': slugify(game_name, allow_unicode=True),
                        'is_active': True,
                        'order': idx,
                        'icon': 'bi-controller'
                    }
                )
                
                if created:
                    created_games += 1
                    print(f"✅ {idx}. {game_name}")
                else:
                    print(f"⏭️  {idx}. {game_name} (уже существует)")
                
                # Создаем категории
                for cat_idx, cat_name in enumerate(categories_list, start=1):
                    cat_slug = slugify(f"{game_name}-{cat_name}", allow_unicode=True)
                    cat_icon = get_icon_for_category(cat_name)
                    
                    category, cat_created = Category.objects.get_or_create(
                        game=game,
                        name=cat_name,
                        defaults={
                            'slug': cat_slug,
                            'icon': cat_icon,
                            'order': cat_idx,
                            'is_active': True
                        }
                    )
                    
                    if cat_created:
                        created_categories += 1
                        print(f"   ➕ {cat_name} ({cat_icon})")
                
                print()
                
            except Exception as e:
                error_msg = f"❌ Ошибка при добавлении {game_name}: {e}"
                errors.append(error_msg)
                print(error_msg)
                print()
    
    print("="*60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print("="*60)
    print(f"✅ Создано игр: {created_games}")
    print(f"✅ Создано категорий: {created_categories}")
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
        for error in errors:
            print(f"   {error}")
    print("="*60)
    print()
    print(f"🌐 Проверьте каталог: http://91.218.245.178/catalog/")
    print(f"⚙️  Админка: http://91.218.245.178/admin/listings/game/")
    print()


if __name__ == '__main__':
    # Парсим список
    games = parse_games_list(GAMES_DATA)
    
    print(f"📋 Найдено {len(games)} игр в списке")
    print()
    
    # Добавляем в БД
    add_games_to_db(games)

