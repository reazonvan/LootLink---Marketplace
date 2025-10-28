#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для проверки существования пользователя и его данных.
Использование: python scripts/check_user.py <username>
"""
import os
import sys
import django

# Для Windows - устанавливаем UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

CustomUser = get_user_model()

def check_user(username):
    """Проверяет существование и данные пользователя."""
    try:
        user = CustomUser.objects.get(username=username)
        print(f"\n✅ Пользователь найден!")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  ID: {user.id}")
        print(f"  Is Active: {user.is_active}")
        print(f"  Is Staff: {user.is_staff}")
        print(f"  Has Usable Password: {user.has_usable_password()}")
        print(f"  Date Joined: {user.date_joined}")
        print(f"  Last Login: {user.last_login}")
        
        # Проверяем профиль
        if hasattr(user, 'profile'):
            print(f"\n📋 Профиль:")
            print(f"  Phone: {user.profile.phone}")
            print(f"  Balance: {user.profile.balance}")
            print(f"  Rating: {user.profile.rating}")
            print(f"  Is Verified: {user.profile.is_verified}")
        else:
            print(f"\n⚠️  У пользователя нет профиля!")
        
        return True
    except CustomUser.DoesNotExist:
        print(f"\n❌ Пользователь '{username}' не найден!")
        return False

def list_all_users():
    """Выводит список всех пользователей."""
    users = CustomUser.objects.all()
    print(f"\n📋 Всего пользователей: {users.count()}\n")
    for user in users:
        print(f"  • {user.username} ({user.email}) - Active: {user.is_active}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        username = sys.argv[1]
        check_user(username)
    else:
        print("🔍 Список всех пользователей:")
        list_all_users()
        print("\nИспользование: python scripts/check_user.py <username>")

