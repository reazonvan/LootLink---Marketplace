"""
Скрипт для добавления игр в базу данных LootLink
Запуск: python manage.py shell < add_games.py
"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Game
from django.utils.text import slugify

print("Добавление игр в базу данных...\n")

games_data = [
    {
        'name': 'Dota 2',
        'description': 'Многопользовательская онлайн-арена от Valve. Торгуйте предметами, скинами и аркан.'
    },
    {
        'name': 'CS:GO',
        'description': 'Counter-Strike: Global Offensive - тактический шутер. Покупайте и продавайте скины оружия.'
    },
    {
        'name': 'World of Warcraft',
        'description': 'Легендарная MMORPG от Blizzard. Торговля золотом, предметами и услугами.'
    },
    {
        'name': 'League of Legends',
        'description': 'Самая популярная MOBA в мире. Аккаунты, скины и наборы.'
    },
    {
        'name': 'Fortnite',
        'description': 'Battle Royale с системой строительства. Торговля аккаунтами и V-Bucks.'
    },
    {
        'name': 'Valorant',
        'description': 'Тактический шутер от Riot Games. Скины оружия и аккаунты.'
    },
    {
        'name': 'Minecraft',
        'description': 'Популярная песочница. Аккаунты, серверы и ресурсы.'
    },
    {
        'name': 'Rust',
        'description': 'Выживание в мультиплеере. Скины и игровые предметы.'
    },
]

created_count = 0
existing_count = 0

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
        print(f"[+] Добавлена игра: {game.name}")
        created_count += 1
    else:
        print(f"[!] Игра уже существует: {game.name}")
        existing_count += 1

print(f"\n{'='*50}")
print(f"Результат:")
print(f"  Добавлено новых игр: {created_count}")
print(f"  Уже существовало: {existing_count}")
print(f"  Всего игр в базе: {Game.objects.count()}")
print(f"{'='*50}\n")
print("[OK] Готово! Теперь можно создавать объявления.")

