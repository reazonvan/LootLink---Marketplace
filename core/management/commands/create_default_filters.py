"""
Команда для создания типовых фильтров для категорий (как на FunPay)
"""
from django.core.management.base import BaseCommand
from listings.models import Game, Category
from listings.models_filters import CategoryFilter, FilterOption


class Command(BaseCommand):
    help = 'Создает типовые фильтры для популярных категорий игр (по примеру FunPay)'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('  СОЗДАНИЕ ТИПОВЫХ ФИЛЬТРОВ ДЛЯ КАТЕГОРИЙ')
        self.stdout.write('=' * 60)
        
        # Фильтры по типам игр (на основе FunPay, G2G, PlayerAuctions)
        filters_data = {
            'CS2': {
                'Аккаунты': [
                    {
                        'name': 'Ранг',
                        'field_name': 'rank',
                        'type': 'select',
                        'options': [
                            'Silver I', 'Silver II', 'Silver III', 'Silver IV', 'Silver Elite', 'Silver Elite Master',
                            'Gold Nova I', 'Gold Nova II', 'Gold Nova III', 'Gold Nova Master',
                            'Master Guardian I', 'Master Guardian II', 'Master Guardian Elite', 'Distinguished Master Guardian',
                            'Legendary Eagle', 'Legendary Eagle Master', 'Supreme Master First Class', 'Global Elite'
                        ]
                    },
                    {
                        'name': 'Prime статус',
                        'field_name': 'prime_status',
                        'type': 'checkbox',
                        'options': []
                    },
                    {
                        'name': 'Количество часов',
                        'field_name': 'hours',
                        'type': 'select',
                        'options': ['Менее 100', '100-500', '500-1000', '1000-2000', '2000-5000', 'Более 5000']
                    },
                ],
                'Скины': [
                    {
                        'name': 'Тип оружия',
                        'field_name': 'weapon_type',
                        'type': 'select',
                        'options': ['Knife', 'AWP', 'AK-47', 'M4A4', 'M4A1-S', 'Desert Eagle', 'Glock-18', 'USP-S', 'Перчатки']
                    },
                    {
                        'name': 'Качество',
                        'field_name': 'quality',
                        'type': 'select',
                        'options': ['Factory New', 'Minimal Wear', 'Field-Tested', 'Well-Worn', 'Battle-Scarred']
                    },
                    {
                        'name': 'StatTrak',
                        'field_name': 'stattrak',
                        'type': 'checkbox',
                        'options': []
                    },
                ],
            },
            'Dota 2': {
                'Аккаунты': [
                    {
                        'name': 'MMR',
                        'field_name': 'mmr',
                        'type': 'select',
                        'options': ['Менее 1000', '1000-2000', '2000-3000', '3000-4000', '4000-5000', '5000-6000', '6000-7000', 'Более 7000']
                    },
                    {
                        'name': 'Медаль',
                        'field_name': 'medal',
                        'type': 'select',
                        'options': ['Herald', 'Guardian', 'Crusader', 'Archon', 'Legend', 'Ancient', 'Divine', 'Immortal']
                    },
                    {
                        'name': 'Количество героев',
                        'field_name': 'heroes',
                        'type': 'select',
                        'options': ['Менее 50', '50-80', '80-100', '100-120', 'Все герои']
                    },
                ],
                'Предметы': [
                    {
                        'name': 'Редкость',
                        'field_name': 'rarity',
                        'type': 'select',
                        'options': ['Common', 'Uncommon', 'Rare', 'Mythical', 'Legendary', 'Immortal', 'Arcana']
                    },
                    {
                        'name': 'Тип предмета',
                        'field_name': 'item_type',
                        'type': 'select',
                        'options': ['Оружие', 'Броня', 'Курьер', 'Ward', 'Taunt', 'Announcer']
                    },
                ],
            },
            'Brawl Stars': {
                'Аккаунты': [
                    {
                        'name': 'Количество кубков',
                        'field_name': 'trophies',
                        'type': 'select',
                        'options': ['Менее 5000', '5000-10000', '10000-15000', '15000-20000', '20000-30000', 'Более 30000']
                    },
                    {
                        'name': 'Легендарные броулеры',
                        'field_name': 'legendary_brawlers',
                        'type': 'select',
                        'options': ['Нет', '1-3', '4-6', '7-10', 'Все']
                    },
                    {
                        'name': 'Brawl Pass',
                        'field_name': 'brawl_pass',
                        'type': 'checkbox',
                        'options': []
                    },
                ],
                'Гемы': [
                    {
                        'name': 'Количество',
                        'field_name': 'amount',
                        'type': 'select',
                        'options': ['170', '360', '950', '2000', '5000', '10000']
                    },
                ],
            },
            'Valorant': {
                'Аккаунты': [
                    {
                        'name': 'Ранг',
                        'field_name': 'rank',
                        'type': 'select',
                        'options': ['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Ascendant', 'Immortal', 'Radiant']
                    },
                    {
                        'name': 'Количество скинов',
                        'field_name': 'skins_count',
                        'type': 'select',
                        'options': ['Менее 10', '10-20', '20-50', '50-100', 'Более 100']
                    },
                    {
                        'name': 'Есть Battlepass',
                        'field_name': 'battlepass',
                        'type': 'checkbox',
                        'options': []
                    },
                ],
                'Скины': [
                    {
                        'name': 'Оружие',
                        'field_name': 'weapon',
                        'type': 'select',
                        'options': ['Vandal', 'Phantom', 'Operator', 'Sheriff', 'Ghost', 'Classic', 'Knife']
                    },
                    {
                        'name': 'Коллекция',
                        'field_name': 'collection',
                        'type': 'select',
                        'options': ['Prime', 'Elderflame', 'Reaver', 'Glitchpop', 'Singularity', 'Champions']
                    },
                ],
            },
            'Steam': {
                'Ключи': [
                    {
                        'name': 'Регион',
                        'field_name': 'region',
                        'type': 'select',
                        'options': ['Весь мир', 'Россия и СНГ', 'Европа', 'США', 'Азия']
                    },
                    {
                        'name': 'Платформа',
                        'field_name': 'platform',
                        'type': 'select',
                        'options': ['Steam', 'Epic Games', 'Origin', 'Uplay', 'GOG']
                    },
                ],
                'Пополнение': [
                    {
                        'name': 'Сумма',
                        'field_name': 'amount',
                        'type': 'select',
                        'options': ['100₽', '500₽', '1000₽', '2000₽', '5000₽', '10000₽']
                    },
                ],
            },
            'Clash of Clans': {
                'Аккаунты': [
                    {
                        'name': 'Town Hall',
                        'field_name': 'town_hall',
                        'type': 'select',
                        'options': ['TH7', 'TH8', 'TH9', 'TH10', 'TH11', 'TH12', 'TH13', 'TH14', 'TH15', 'TH16']
                    },
                    {
                        'name': 'Герои макс уровня',
                        'field_name': 'max_heroes',
                        'type': 'checkbox',
                        'options': []
                    },
                ],
            },
            'Genshin Impact': {
                'Аккаунты': [
                    {
                        'name': 'Ранг приключений',
                        'field_name': 'adventure_rank',
                        'type': 'select',
                        'options': ['AR 1-20', 'AR 21-35', 'AR 36-45', 'AR 46-55', 'AR 55+']
                    },
                    {
                        'name': '5★ персонажи',
                        'field_name': 'five_star_chars',
                        'type': 'select',
                        'options': ['1-3', '4-6', '7-10', '10-15', 'Более 15']
                    },
                ],
                'Примогемы': [
                    {
                        'name': 'Количество',
                        'field_name': 'amount',
                        'type': 'select',
                        'options': ['60', '300', '980', '1980', '3280', '6480']
                    },
                ],
            },
        }
        
        created_filters = 0
        created_options = 0
        
        for game_name, categories_data in filters_data.items():
            # Ищем игру (case-insensitive)
            try:
                game = Game.objects.filter(name__icontains=game_name).first()
                if not game:
                    self.stdout.write(self.style.WARNING(f'  Игра "{game_name}" не найдена, пропускаем'))
                    continue

                self.stdout.write(f'\n{game.name}')
                
                for category_name, filters in categories_data.items():
                    # Ищем категорию
                    category = Category.objects.filter(game=game, name__icontains=category_name).first()
                    if not category:
                        self.stdout.write(f'  ⚠️  Категория "{category_name}" не найдена')
                        continue
                    
                    self.stdout.write(f'  📁 {category.name}')
                    
                    for filter_data in filters:
                        # Создаем или обновляем фильтр
                        cat_filter, filter_created = CategoryFilter.objects.get_or_create(
                            category=category,
                            field_name=filter_data['field_name'],
                            defaults={
                                'name': filter_data['name'],
                                'filter_type': filter_data['type'],
                                'is_active': True,
                            }
                        )
                        
                        if filter_created:
                            created_filters += 1
                            self.stdout.write(f'    Фильтр: {filter_data["name"]}')
                        
                        # Создаем опции для select/multiselect
                        if filter_data['options']:
                            for idx, option_value in enumerate(filter_data['options']):
                                option, opt_created = FilterOption.objects.get_or_create(
                                    filter=cat_filter,
                                    value=option_value,
                                    defaults={
                                        'order': idx,
                                        'is_active': True,
                                    }
                                )
                                if opt_created:
                                    created_options += 1
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Ошибка: {e}'))

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Создано фильтров: {created_filters}'))
        self.stdout.write(self.style.SUCCESS(f'Создано опций: {created_options}'))
        self.stdout.write('=' * 60)
        self.stdout.write('\n💡 Фильтры доступны в админке Django')
        self.stdout.write('🌐 Они автоматически появятся на страницах категорий\n')

