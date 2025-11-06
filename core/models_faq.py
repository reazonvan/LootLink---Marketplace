"""
Модели для FAQ и шаблонов.
"""
from django.db import models
from listings.models import Game


class FAQ(models.Model):
    """
    Часто задаваемые вопросы.
    """
    CATEGORIES = [
        ('general', 'Общие'),
        ('trading', 'Торговля'),
        ('payments', 'Платежи'),
        ('security', 'Безопасность'),
        ('technical', 'Технические'),
    ]
    
    category = models.CharField(
        max_length=50,
        choices=CATEGORIES,
        default='general',
        verbose_name='Категория'
    )
    question = models.CharField(
        max_length=500,
        verbose_name='Вопрос'
    )
    answer = models.TextField(
        verbose_name='Ответ'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Просмотров'
    )
    helpful_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Полезно'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено'
    )
    
    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['category', 'order', 'question']
    
    def __str__(self):
        return self.question


class DescriptionTemplate(models.Model):
    """
    Шаблоны описаний для объявлений.
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='description_templates',
        verbose_name='Игра'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название шаблона'
    )
    template = models.TextField(
        verbose_name='Шаблон',
        help_text='Используйте {переменные} для подстановки'
    )
    variables = models.JSONField(
        default=list,
        verbose_name='Переменные',
        help_text='Список переменных: ["level", "items", "price"]'
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Использований'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    
    class Meta:
        verbose_name = 'Шаблон описания'
        verbose_name_plural = 'Шаблоны описаний'
        ordering = ['game', '-usage_count']
    
    def __str__(self):
        return f'{self.game.name} - {self.name}'
    
    def render(self, **kwargs):
        """Рендер шаблона с переменными"""
        return self.template.format(**kwargs)


class AntiFraudRule(models.Model):
    """
    Правила антифрод системы.
    """
    RULE_TYPES = [
        ('blacklist_email', 'Email в черном списке'),
        ('blacklist_phone', 'Телефон в черном списке'),
        ('suspicious_price', 'Подозрительная цена'),
        ('rapid_account_creation', 'Быстрое создание аккаунтов'),
        ('multiple_accounts_ip', 'Множественные аккаунты с одного IP'),
        ('chargeback_history', 'История чарджбеков'),
    ]
    
    rule_type = models.CharField(
        max_length=50,
        choices=RULE_TYPES,
        verbose_name='Тип правила'
    )
    pattern = models.CharField(
        max_length=500,
        verbose_name='Паттерн',
        help_text='Email, телефон, IP и т.д.'
    )
    risk_score = models.PositiveIntegerField(
        default=50,
        verbose_name='Оценка риска',
        help_text='0-100, где 100 = максимальный риск'
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('flag', 'Пометить'),
            ('block', 'Заблокировать'),
            ('review', 'На проверку'),
        ],
        default='flag',
        verbose_name='Действие'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    
    class Meta:
        verbose_name = 'Правило антифрод'
        verbose_name_plural = 'Правила антифрод'
        ordering = ['-risk_score']
    
    def __str__(self):
        return f'{self.get_rule_type_display()} - {self.pattern}'

