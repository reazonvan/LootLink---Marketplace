"""
Скрипт для создания тестовых данных в LootLink.
Запуск: python manage.py shell < create_test_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import CustomUser, Profile
from listings.models import Game, Listing
from transactions.models import PurchaseRequest, Review
from django.utils.text import slugify

print("Начинаем создание тестовых данных...\n")

# 1. Создание тестовых пользователей
print("1. Создание пользователей...")
users_data = [
    {'username': 'seller1', 'email': 'seller1@test.com', 'password': 'testpass123'},
    {'username': 'buyer1', 'email': 'buyer1@test.com', 'password': 'testpass123'},
    {'username': 'trader1', 'email': 'trader1@test.com', 'password': 'testpass123'},
]

users = []
for user_data in users_data:
    user, created = CustomUser.objects.get_or_create(
        username=user_data['username'],
        email=user_data['email']
    )
    if created:
        user.set_password(user_data['password'])
        user.save()
        print(f"✓ Создан пользователь: {user.username}")
    else:
        print(f"○ Пользователь уже существует: {user.username}")
    users.append(user)

# 2. Создание игр
print("\n2. Создание игр...")
games_data = [
    {'name': 'Dota 2', 'description': 'Популярная MOBA игра от Valve'},
    {'name': 'CS:GO', 'description': 'Культовый тактический шутер'},
    {'name': 'World of Warcraft', 'description': 'Легендарная MMORPG от Blizzard'},
    {'name': 'League of Legends', 'description': 'Самая популярная MOBA в мире'},
    {'name': 'Fortnite', 'description': 'Battle Royale с системой строительства'},
    {'name': 'Valorant', 'description': 'Тактический шутер от Riot Games'},
]

games = []
for game_data in games_data:
    game, created = Game.objects.get_or_create(
        name=game_data['name'],
        defaults={
            'slug': slugify(game_data['name']),
            'description': game_data['description'],
            'is_active': True
        }
    )
    if created:
        print(f"✓ Создана игра: {game.name}")
    else:
        print(f"○ Игра уже существует: {game.name}")
    games.append(game)

# 3. Обновление профилей пользователей
print("\n3. Обновление профилей...")
for user in users:
    profile = user.profile
    profile.bio = f"Привет! Я {user.username}. Занимаюсь торговлей игровыми предметами."
    profile.rating = 4.5
    profile.total_sales = 10
    profile.total_purchases = 8
    profile.save()
    print(f"✓ Обновлен профиль: {user.username}")

print("\n" + "="*50)
print("✅ Тестовые данные успешно созданы!")
print("="*50)
print("\nТеперь вы можете:")
print("1. Войти как seller1/buyer1/trader1 (пароль: testpass123)")
print("2. Создавать объявления")
print("3. Тестировать функционал покупки и продажи")
print("\nАдмин-панель: http://127.0.0.1:8000/admin/")
print("Главная страница: http://127.0.0.1:8000/")

