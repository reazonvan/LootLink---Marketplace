#!/usr/bin/env python
"""
Автоматическая очистка ВСЕХ объявлений и игр (БЕЗ подтверждения).
ОПАСНО! Используйте только если точно уверены!
Использование: python scripts/auto_clear_all.py --listings | --games | --all
"""
import os
import sys
import django
import argparse

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category, Listing
from django.db import transaction


def clear_listings():
    """Удаляет все объявления БЕЗ подтверждения."""
    total = Listing.objects.count()
    
    print(f"🗑️  Удаление {total} объявлений...")
    
    with transaction.atomic():
        deleted = Listing.objects.all().delete()[0]
    
    print(f"✅ Удалено объявлений: {deleted}")
    return deleted


def clear_games():
    """Удаляет все игры, категории и объявления БЕЗ подтверждения."""
    games_count = Game.objects.count()
    categories_count = Category.objects.count()
    listings_count = Listing.objects.count()
    
    print(f"🗑️  Удаление {games_count} игр, {categories_count} категорий, {listings_count} объявлений...")
    
    with transaction.atomic():
        # Удаление игр автоматически удалит категории и объявления (CASCADE)
        deleted = Game.objects.all().delete()
    
    print(f"✅ Удалено:")
    print(f"   • Игр: {games_count}")
    print(f"   • Категорий: {categories_count}")
    print(f"   • Объявлений: {listings_count}")
    return deleted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Очистка БД')
    parser.add_argument('--listings', action='store_true', help='Удалить только объявления')
    parser.add_argument('--games', action='store_true', help='Удалить игры, категории и объявления')
    parser.add_argument('--all', action='store_true', help='Удалить все (то же что --games)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("⚠️  АВТОМАТИЧЕСКАЯ ОЧИСТКА БД (БЕЗ ПОДТВЕРЖДЕНИЯ)")
    print("="*60)
    print()
    
    try:
        if args.listings:
            clear_listings()
        elif args.games or args.all:
            clear_games()
        else:
            print("❌ Укажите опцию:")
            print("   python scripts/auto_clear_all.py --listings")
            print("   python scripts/auto_clear_all.py --games")
            print("   python scripts/auto_clear_all.py --all")
            sys.exit(1)
        
        print()
        print("="*60)
        print("✅ ГОТОВО!")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        sys.exit(1)

