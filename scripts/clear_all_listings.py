#!/usr/bin/env python
"""
Скрипт для удаления ВСЕХ объявлений из базы данных.
ВНИМАНИЕ: Это необратимая операция!
Использование: python scripts/clear_all_listings.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Listing
from django.db import transaction


def clear_all_listings():
    """Удаляет все объявления из БД с подтверждением."""
    
    print("="*60)
    print("⚠️  УДАЛЕНИЕ ВСЕХ ОБЪЯВЛЕНИЙ ИЗ БАЗЫ ДАННЫХ")
    print("="*60)
    print()
    
    # Подсчитываем объявления
    total_count = Listing.objects.all().count()
    active_count = Listing.objects.filter(status='active').count()
    sold_count = Listing.objects.filter(status='sold').count()
    
    print(f"📊 Текущее состояние:")
    print(f"   Всего объявлений: {total_count}")
    print(f"   Активных: {active_count}")
    print(f"   Проданных: {sold_count}")
    print()
    
    if total_count == 0:
        print("✅ Объявлений нет! БД уже пустая.")
        return
    
    # Запрашиваем подтверждение
    print("⚠️  ЭТО НЕОБРАТИМАЯ ОПЕРАЦИЯ!")
    print("   Все объявления будут УДАЛЕНЫ навсегда!")
    print()
    confirmation = input("Введите 'УДАЛИТЬ ВСЕ' для подтверждения: ")
    
    if confirmation != 'УДАЛИТЬ ВСЕ':
        print("\n❌ Операция отменена. Объявления не удалены.")
        return
    
    # Дополнительное подтверждение
    print()
    final_confirm = input(f"Вы уверены? Будет удалено {total_count} объявлений. Введите 'ДА': ")
    
    if final_confirm != 'ДА':
        print("\n❌ Операция отменена. Объявления не удалены.")
        return
    
    # Удаляем в транзакции
    print("\n🗑️  Удаление объявлений...")
    
    try:
        with transaction.atomic():
            deleted_count = Listing.objects.all().delete()[0]
        
        print()
        print("="*60)
        print(f"✅ УСПЕШНО УДАЛЕНО: {deleted_count} объявлений")
        print("="*60)
        print()
        print("📋 Что удалено:")
        print(f"   • Объявления: {deleted_count}")
        print(f"   • Связанные данные: избранное, жалобы и т.д.")
        print()
        print("✅ База данных очищена!")
        print()
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при удалении: {e}")
        print("Объявления НЕ удалены.")


if __name__ == '__main__':
    clear_all_listings()

