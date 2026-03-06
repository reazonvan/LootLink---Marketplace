#!/usr/bin/env python
"""
Скрипт для очистки кэша Django.
Используется для удаления закэшированных данных, особенно после критических изменений.
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.cache import cache

def clear_all_cache():
    """Очищает весь кэш Django."""
    try:
        cache.clear()
        print("Кэш успешно очищен!")
        return True
    except Exception as e:
        print(f"Ошибка при очистке кэша: {e}")
        return False

if __name__ == '__main__':
    print("Очистка кэша Django...")
    success = clear_all_cache()
    sys.exit(0 if success else 1)

