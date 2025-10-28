#!/usr/bin/env python
"""
Скрипт для создания недостающих профилей для всех пользователей.
Запускать: python manage.py shell < scripts/create_missing_profiles.py
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import CustomUser, Profile

def create_missing_profiles():
    """Создает профили для пользователей, у которых их нет."""
    print("Начинаем проверку пользователей...")
    
    users = CustomUser.objects.all()
    total_users = users.count()
    created_count = 0
    exists_count = 0
    
    for user in users:
        try:
            # Пытаемся получить профиль
            profile = user.profile
            exists_count += 1
        except Profile.DoesNotExist:
            # Создаем профиль если его нет
            Profile.objects.create(user=user)
            created_count += 1
            print(f"✓ Создан профиль для пользователя: {user.username}")
        except Exception as e:
            print(f"✗ Ошибка для пользователя {user.username}: {e}")
    
    print("\n" + "="*50)
    print("РЕЗУЛЬТАТЫ:")
    print(f"Всего пользователей: {total_users}")
    print(f"Уже имели профиль: {exists_count}")
    print(f"Создано новых профилей: {created_count}")
    print("="*50)

if __name__ == "__main__":
    create_missing_profiles()

