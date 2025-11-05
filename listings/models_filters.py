"""
Модели для динамических фильтров категорий
"""
from django.db import models
from .models import Category


class CategoryFilter(models.Model):
    """
    Динамический фильтр для категории игры.
    Админ может создавать кастомные фильтры для каждой категории.
    
    Примеры:
    - CS2 > Аккаунты: Ранг (Silver, Gold, Global Elite)
    - Dota 2 > Предметы: Редкость (Common, Rare, Immortal, Arcana)
    - Brawl Stars > Аккаунты: Кубки (10000+, 20000+, 30000+)
    """
    FILTER_TYPES = [
        ('select', 'Выбор из списка'),
        ('multiselect', 'Множественный выбор'),
        ('range', 'Диапазон (от-до)'),
        ('checkbox', 'Чекбокс (да/нет)'),
    ]
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='filters',
        verbose_name='Категория'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Название фильтра',
        help_text='Например: Ранг, Редкость, Количество кубков'
    )
    field_name = models.CharField(
        max_length=100,
        verbose_name='Имя поля',
        help_text='Техническое имя (латиница, без пробелов). Например: rank, rarity, trophies'
    )
    filter_type = models.CharField(
        max_length=20,
        choices=FILTER_TYPES,
        default='select',
        verbose_name='Тип фильтра'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки',
        help_text='Меньше число = выше в списке фильтров'
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name='Обязательный фильтр',
        help_text='Требовать заполнение при создании объявления'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Фильтр категории'
        verbose_name_plural = 'Фильтры категорий'
        ordering = ['category', 'order', 'name']
        unique_together = [['category', 'field_name']]
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['category', 'order']),
        ]
    
    def __str__(self):
        return f'{self.category.game.name} > {self.category.name} > {self.name}'


class FilterOption(models.Model):
    """
    Опция для фильтра типа select/multiselect.
    
    Примеры:
    - Фильтр "Ранг": Silver I, Silver II, ..., Global Elite
    - Фильтр "Редкость": Common, Uncommon, Rare, Mythical, Legendary, Arcana
    """
    filter = models.ForeignKey(
        CategoryFilter,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Фильтр'
    )
    value = models.CharField(
        max_length=100,
        verbose_name='Значение',
        help_text='Например: Global Elite, Arcana, 30000+'
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Отображаемое имя',
        help_text='Если пусто, используется value'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    
    class Meta:
        verbose_name = 'Опция фильтра'
        verbose_name_plural = 'Опции фильтров'
        ordering = ['filter', 'order', 'value']
        unique_together = [['filter', 'value']]
    
    def __str__(self):
        return f'{self.filter.name}: {self.value}'
    
    def get_display_name(self):
        """Возвращает отображаемое имя или value"""
        return self.display_name or self.value


class ListingFilterValue(models.Model):
    """
    Значения фильтров для конкретного объявления.
    Связь: Объявление → Фильтр → Значение
    """
    listing = models.ForeignKey(
        'Listing',
        on_delete=models.CASCADE,
        related_name='filter_values',
        verbose_name='Объявление'
    )
    category_filter = models.ForeignKey(
        CategoryFilter,
        on_delete=models.CASCADE,
        related_name='listing_values',
        verbose_name='Фильтр'
    )
    # Для разных типов фильтров используются разные поля
    value_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Текстовое значение'
    )
    value_int = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Числовое значение'
    )
    value_bool = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Булевое значение'
    )
    # Для multiselect - множественные опции
    selected_options = models.ManyToManyField(
        FilterOption,
        blank=True,
        related_name='selected_in_listings',
        verbose_name='Выбранные опции'
    )
    
    class Meta:
        verbose_name = 'Значение фильтра объявления'
        verbose_name_plural = 'Значения фильтров объявлений'
        unique_together = [['listing', 'category_filter']]
        indexes = [
            models.Index(fields=['listing', 'category_filter']),
            models.Index(fields=['category_filter', 'value_text']),
            models.Index(fields=['category_filter', 'value_int']),
        ]
    
    def __str__(self):
        return f'{self.listing.title} | {self.category_filter.name}: {self.get_value()}'
    
    def get_value(self):
        """Возвращает значение в зависимости от типа фильтра"""
        if self.selected_options.exists():
            return ', '.join([opt.get_display_name() for opt in self.selected_options.all()])
        elif self.value_text:
            return self.value_text
        elif self.value_int is not None:
            return str(self.value_int)
        elif self.value_bool is not None:
            return 'Да' if self.value_bool else 'Нет'
        return 'Не указано'

