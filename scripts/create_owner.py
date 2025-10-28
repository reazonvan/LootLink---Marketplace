#!/usr/bin/env python
"""
Скрипт создания владельца сайта (Owner/Superuser)
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import CustomUser, Profile

def create_owner():
    """Создание владельца сайта"""
    
    username = 'reazonvan'
    email = 'ivanpetrov20066.ip@gmail.com'
    phone = '+79269269988'
    password = '5906639Pe'
    
    # Проверка существования
    if CustomUser.objects.filter(username=username).exists():
        print(f'❌ Пользователь {username} уже существует!')
        user = CustomUser.objects.get(username=username)
        
        # Обновление до superuser если не является
        if not user.is_superuser:
            user.is_superuser = True
            user.is_staff = True
            user.save()
            print(f'✅ Пользователь {username} обновлен до владельца!')
        else:
            print(f'✅ Пользователь {username} уже является владельцем!')
        
        # Обновление профиля
        profile = user.profile
        profile.phone = phone
        profile.is_verified = True
        profile.save()
        print(f'✅ Профиль обновлен!')
        
        return user
    
    # Создание нового владельца
    print(f'Создание владельца: {username}...')
    
    user = CustomUser.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    
    # Обновление профиля
    profile = user.profile
    profile.phone = phone
    profile.is_verified = True
    profile.save()
    
    print('=' * 50)
    print('✅ ВЛАДЕЛЕЦ УСПЕШНО СОЗДАН!')
    print('=' * 50)
    print(f'Username: {user.username}')
    print(f'Email: {user.email}')
    print(f'Phone: {profile.phone}')
    print(f'Superuser: {user.is_superuser}')
    print(f'Staff: {user.is_staff}')
    print(f'Verified: {profile.is_verified}')
    print('=' * 50)
    print('\nВладелец имеет доступ:')
    print('  ✅ Админ-панель Django (/admin/)')
    print('  ✅ Все функции сайта')
    print('  ✅ Управление пользователями')
    print('  ✅ Модерация контента')
    print('  ✅ Просмотр всех данных')
    print('=' * 50)
    
    return user

if __name__ == '__main__':
    create_owner()

