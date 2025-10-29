#!/usr/bin/env python
"""
Скрипт для удаления ВСЕХ игр и категорий из базы данных.
ВНИМАНИЕ: Это удалит ВСЕ связанные объявления!
Использование: python scripts/clear_all_games.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game, Category, Listing
from django.db import transaction


def clear_all_games():
    """Удаляет все игры, категории и связанные объявления из БД."""
    
    print("="*60)
    print("⚠️  УДАЛЕНИЕ ВСЕХ ИГР, КАТЕГОРИЙ И ОБЪЯВЛЕНИЙ")
    print("="*60)
    print()
    
    # Подсчитываем данные
    games_count = Game.objects.all().count()
    categories_count = Category.objects.all().count()
    listings_count = Listing.objects.all().count()
    
    print(f"📊 Текущее состояние:")
    print(f"   Игр: {games_count}")
    print(f"   Категорий: {categories_count}")
    print(f"   Объявлений: {listings_count}")
    print()
    
    if games_count == 0:
        print("✅ Игр нет! БД уже пустая.")
        return
    
    # Показываем список игр
    print("📋 Список игр:")
    for game in Game.objects.all():
        cat_count = game.categories.count()
        list_count = game.listings.count()
        print(f"   • {game.name} ({cat_count} категорий, {list_count} объявлений)")
    print()
    
    # Запрашиваем подтверждение
    print("⚠️  ЭТО НЕОБРАТИМАЯ ОПЕРАЦИЯ!")
    print(f"   Будет удалено:")
    print(f"   • {games_count} игр")
    print(f"   • {categories_count} категорий")
    print(f"   • {listings_count} объявлений")
    print(f"   • Все связанные данные (избранное, жалобы и т.д.)")
    print()
    confirmation = input("Введите 'УДАЛИТЬ ВСЕ ИГРЫ' для подтверждения: ")
    
    if confirmation != 'УДАЛИТЬ ВСЕ ИГРЫ':
        print("\n❌ Операция отменена. Данные не удалены.")
        return
    
    # Дополнительное подтверждение
    print()
    final_confirm = input(f"ПОСЛЕДНЕЕ ПРЕДУПРЕЖДЕНИЕ! Удалится {listings_count} объявлений! Введите 'ДА': ")
    
    if final_confirm != 'ДА':
        print("\n❌ Операция отменена. Данные не удалены.")
        return
    
    # Удаляем в транзакции
    print("\n🗑️  Удаление данных...")
    
    try:
        with transaction.atomic():
            # При удалении Game автоматически удалятся Category (CASCADE) и Listing (CASCADE)
            deleted = Game.objects.all().delete()
        
        print()
        print("="*60)
        print(f"✅ УСПЕШНО УДАЛЕНО!")
        print("="*60)
        print()
        print("📋 Что удалено:")
        print(f"   • Игры: {games_count}")
        print(f"   • Категории: {categories_count}")
        print(f"   • Объявления: {listings_count}")
        print(f"   • Связанные данные (CASCADE)")
        print()
        print("✅ База данных полностью очищена от игр!")
        print("🎮 Теперь можно добавлять новые игры через админку.")
        print()
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при удалении: {e}")
        print("Данные НЕ удалены.")


if __name__ == '__main__':
    clear_all_games()

