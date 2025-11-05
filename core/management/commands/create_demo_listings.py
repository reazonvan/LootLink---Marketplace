"""
Команда для создания демо-объявлений для наполнения сайта
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from listings.models import Listing, Game
from accounts.models import Profile
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает демо-объявления для наполнения маркетплейса'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Количество объявлений для создания (по умолчанию 30)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Создаем демо-пользователя если его нет
        demo_username = 'DemoSeller'
        demo_user, created = User.objects.get_or_create(
            username=demo_username,
            defaults={
                'email': 'demo@lootlink.com',
                'is_active': True
            }
        )
        
        if created:
            demo_user.set_password('demo123456')
            demo_user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Создан демо-пользователь: {demo_username}'))
        
        # Обновляем профиль
        profile, _ = Profile.objects.get_or_create(user=demo_user)
        profile.rating = Decimal('4.8')
        profile.total_sales = 45
        profile.total_purchases = 12
        profile.is_verified = True
        profile.save()
        
        # Получаем активные игры
        games = list(Game.objects.filter(is_active=True))
        
        if not games:
            self.stdout.write(self.style.ERROR('❌ Нет активных игр в базе!'))
            return
        
        # Шаблоны объявлений для разных игр
        templates = {
            'CS2': [
                {'title': 'Knife Karambit Fade', 'desc': 'Редкий нож с градиентом Fade. Factory New, float 0.008. Без царапин.', 'price': (8000, 25000)},
                {'title': 'AWP Dragon Lore', 'desc': 'Легендарный AWP Dragon Lore. Field-Tested. Одна из самых редких винтовок.', 'price': (15000, 45000)},
                {'title': 'AK-47 Fire Serpent', 'desc': 'Классический Fire Serpent. Minimal Wear. Отличное состояние.', 'price': (5000, 15000)},
                {'title': 'Аккаунт Global Elite', 'desc': 'Ранг: Global Elite. 2000+ часов. Prime статус. Чистая история.', 'price': (3000, 8000)},
                {'title': 'M4A4 Howl', 'desc': 'Контрабандный скин M4A4 Howl. Field-Tested. Коллекционный предмет.', 'price': (12000, 35000)},
            ],
            'Dota 2': [
                {'title': 'Arcana Legion Commander', 'desc': 'Полный комплект Arcana для Legion Commander. Все стили разблокированы.', 'price': (2500, 4500)},
                {'title': 'Arcana Phantom Assassin', 'desc': 'Arcana PA с максимальным уровнем. Все эффекты включены.', 'price': (3000, 5000)},
                {'title': 'Аккаунт 5000 MMR', 'desc': 'Аккаунт Divine ранга. 5000+ MMR. Много редких сетов и курьеров.', 'price': (4000, 10000)},
                {'title': 'Bundle Immortals', 'desc': 'Набор из 15 Immortal предметов. Редкие эффекты и анимации.', 'price': (1500, 3500)},
            ],
            'Brawl Stars': [
                {'title': 'Аккаунт 30000+ кубков', 'desc': 'Все легендарные бойцы прокачаны. 30000+ кубков. Много скинов.', 'price': (1000, 3000)},
                {'title': '5000 гемов', 'desc': 'Пополнение аккаунта на 5000 гемов. Безопасная передача через Supercell ID.', 'price': (2500, 3500)},
                {'title': 'Аккаунт с Brawl Pass', 'desc': 'Текущий Brawl Pass полностью прокачан. Все награды получены.', 'price': (800, 1500)},
            ],
            'Valorant': [
                {'title': 'Аккаунт Immortal', 'desc': 'Ранг: Immortal 2. Много скинов. Полная коллекция Battle Pass.', 'price': (5000, 12000)},
                {'title': 'Phantom Champions 2021', 'desc': 'Редкий скин Champions 2021 на Phantom. Коллекционный предмет.', 'price': (8000, 15000)},
                {'title': 'Valorant Points 11000', 'desc': 'Пополнение на 11000 Valorant Points. Официальная передача.', 'price': (6000, 7000)},
            ],
            'Steam': [
                {'title': 'Пополнение кошелька 1000₽', 'desc': 'Пополнение Steam кошелька на 1000 рублей. Мгновенная передача.', 'price': (950, 1050)},
                {'title': 'Случайный ключ Steam', 'desc': 'Случайная игра от известных издателей. Гарантия активации.', 'price': (50, 300)},
                {'title': 'Elden Ring + DLC', 'desc': 'Ключ Elden Ring с дополнением Shadow of the Erdtree.', 'price': (2500, 3500)},
            ],
        }
        
        # Создаем объявления
        created_count = 0
        
        for i in range(count):
            # Выбираем случайную игру
            game = random.choice(games)
            
            # Выбираем шаблон в зависимости от игры
            game_name = game.name
            
            # Ищем подходящий шаблон
            template_data = None
            for key in templates.keys():
                if key.lower() in game_name.lower():
                    template_data = random.choice(templates[key])
                    break
            
            # Если нет специфичного шаблона, используем общий
            if not template_data:
                template_data = {
                    'title': f'{game.name} - {random.choice(["Аккаунт", "Предмет", "Валюта", "Буст"])}',
                    'desc': f'Качественный товар для {game.name}. Быстрая передача, гарантия качества.',
                    'price': (100, 5000)
                }
            
            # Генерируем случайную цену в диапазоне
            price = Decimal(str(random.randint(template_data['price'][0], template_data['price'][1])))
            
            # Создаем объявление
            try:
                listing = Listing.objects.create(
                    seller=demo_user,
                    game=game,
                    title=template_data['title'],
                    description=template_data['desc'],
                    price=price,
                    status='active'
                )
                created_count += 1
                self.stdout.write(f'  ✓ {listing.title} - {listing.price}₽')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Ошибка создания: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Создано {created_count} демо-объявлений!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Общее количество активных объявлений: {Listing.objects.filter(status="active").count()}'))

