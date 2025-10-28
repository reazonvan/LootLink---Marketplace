#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования входа пользователя.
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

from django.contrib.auth import authenticate, get_user_model
from django.test import Client

CustomUser = get_user_model()

def test_authentication(username, password):
    """Тестирует аутентификацию пользователя."""
    print(f"\n🔐 Тестирование аутентификации для '{username}'...")
    
    # Проверяем существование пользователя
    try:
        user = CustomUser.objects.get(username=username)
        print(f"✅ Пользователь найден: {user.username} ({user.email})")
        print(f"   Is Active: {user.is_active}")
        print(f"   Has Usable Password: {user.has_usable_password()}")
    except CustomUser.DoesNotExist:
        print(f"❌ Пользователь '{username}' не существует!")
        return False
    
    # Тестируем аутентификацию
    auth_user = authenticate(username=username, password=password)
    
    if auth_user is not None:
        print(f"✅ Аутентификация успешна!")
        print(f"   Authenticated user: {auth_user.username}")
        return True
    else:
        print(f"❌ Аутентификация не удалась!")
        print(f"   Возможные причины:")
        print(f"   - Неверный пароль")
        print(f"   - Пользователь неактивен (is_active=False)")
        print(f"   - Пароль не установлен")
        return False

def test_login_view():
    """Тестирует view функцию входа."""
    print(f"\n🌐 Тестирование view функции входа...")
    
    client = Client()
    
    # GET запрос на страницу входа
    response = client.get('/accounts/login/')
    print(f"   GET /accounts/login/ - Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ Страница входа загружается")
    else:
        print(f"   ❌ Проблема с загрузкой страницы входа!")
    
    # POST запрос с данными
    print(f"\n   Тестируем POST запрос с данными для 'reazonvan'...")
    response = client.post('/accounts/login/', {
        'username': 'reazonvan',
        'password': 'admin'  # Тестовый пароль
    })
    
    print(f"   POST /accounts/login/ - Status: {response.status_code}")
    
    if response.status_code == 302:
        print(f"   ✅ Редирект (возможно успешный вход)")
        print(f"   Redirect to: {response.url}")
    elif response.status_code == 200:
        print(f"   ⚠️  Остались на странице входа (возможно ошибка)")
        # Проверяем наличие ошибок
        if b'error' in response.content.lower() or b'invalid' in response.content.lower():
            print(f"   ❌ Форма содержит ошибки")
    else:
        print(f"   ❌ Неожиданный статус код")

def check_urls():
    """Проверяет доступность основных URL."""
    print(f"\n🔗 Проверка доступности URL...")
    
    client = Client()
    urls = [
        ('/', 'Главная'),
        ('/accounts/login/', 'Вход'),
        ('/accounts/register/', 'Регистрация'),
    ]
    
    for url, name in urls:
        try:
            response = client.get(url)
            status = '✅' if response.status_code == 200 else '❌'
            print(f"   {status} {name}: {url} - {response.status_code}")
        except Exception as e:
            print(f"   ❌ {name}: {url} - ERROR: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 ДИАГНОСТИКА СИСТЕМЫ ВХОДА")
    print("=" * 60)
    
    # Проверяем URLs
    check_urls()
    
    # Тестируем view
    test_login_view()
    
    # Тестируем аутентификацию для известных пользователей
    print("\n" + "=" * 60)
    print("Попробуйте ввести username и password для тестирования:")
    print("Например: reazonvan")
    
    if len(sys.argv) > 2:
        username = sys.argv[1]
        password = sys.argv[2]
        test_authentication(username, password)
    else:
        print("\nИспользование: python scripts/test_login.py <username> <password>")
        print("Пример: python scripts/test_login.py reazonvan mypassword")
    
    print("\n" + "=" * 60)

