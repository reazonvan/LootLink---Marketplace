from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from accounts.models import CustomUser


def validate_image_size(image):
    """Валидация размера загружаемого изображения."""
    if image:
        file_size = image.size
        limit_mb = 5
        if file_size > limit_mb * 1024 * 1024:
            raise ValidationError(f'Максимальный размер файла {limit_mb} МБ. Ваш файл: {file_size / (1024*1024):.2f} МБ')


def validate_image_type(image):
    """Валидация типа изображения с защитой от вредоносных файлов."""
    if image:
        import imghdr
        from PIL import Image
        
        # Проверка через PIL (защита от поврежденных/вредоносных файлов)
        try:
            img = Image.open(image)
            img.verify()  # Проверяет что файл является валидным изображением
            # Сбрасываем указатель файла после verify()
            image.seek(0)
        except Exception as e:
            raise ValidationError(f'Файл поврежден или не является валидным изображением: {str(e)}')
        
        # Определяем тип файла по содержимому
        file_type = imghdr.what(image)
        allowed_types = ['jpeg', 'jpg', 'png', 'gif', 'webp']
        
        if file_type not in allowed_types:
            raise ValidationError(f'Неподдерживаемый формат изображения. Разрешены: JPEG, PNG, GIF, WebP')
        
        # Дополнительная проверка через content_type
        if hasattr(image, 'content_type'):
            allowed_mime = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_mime:
                raise ValidationError('Файл должен быть изображением')
        
        # Сбрасываем указатель файла для дальнейшего использования
        image.seek(0)


class Favorite(models.Model):
    """
    Избранные объявления пользователя.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    listing = models.ForeignKey(
        'Listing',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Объявление'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    
    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ['user', 'listing']
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} → {self.listing.title}'


class Game(models.Model):
    """
    Модель игры для категоризации объявлений.
    """
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Название игры'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='URL-имя'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    icon = models.ImageField(
        upload_to='games/',
        blank=True,
        null=True,
        verbose_name='Иконка'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки',
        help_text='Меньше число = выше в списке'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    
    class Meta:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Запрещает удаление игры с активными объявлениями."""
        active_listings_count = self.listings.filter(status='active').count()
        if active_listings_count > 0:
            raise Exception(
                f'Нельзя удалить игру с активными объявлениями! '
                f'Найдено {active_listings_count} активных объявлений. '
                f'Сначала завершите или удалите все объявления этой игры.'
            )
        super().delete(*args, **kwargs)


class Category(models.Model):
    """
    Модель категории товаров внутри игры.
    Например: Brawl Stars → Аккаунты, Гемы, Brawl Pass
              Steam → Пополнение, Ключи, Подарки
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='Игра'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Название категории'
    )
    slug = models.SlugField(
        max_length=120,
        blank=True,
        verbose_name='URL slug'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание категории'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default='bi-tag',
        verbose_name='Иконка Bootstrap Icons',
        help_text='Например: bi-gem, bi-cart, bi-trophy, bi-star'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки',
        help_text='Меньше число = выше в списке'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['game', 'order', 'name']
        unique_together = [['game', 'name']]
        indexes = [
            models.Index(fields=['game', 'is_active']),
            models.Index(fields=['game', 'order']),
        ]
    
    def __str__(self):
        return f'{self.game.name} → {self.name}'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Простая транслитерация для русских букв
            translit_dict = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
            }
            name_lower = self.name.lower()
            transliterated = ''.join(translit_dict.get(c, c) for c in name_lower)
            self.slug = slugify(transliterated)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Проверка на наличие активных объявлений
        active_listings = self.listings.filter(status='active')
        if active_listings.exists():
            raise Exception(
                f'Невозможно удалить категорию с активными объявлениями! '
                f'Найдено {active_listings.count()} активных объявлений.'
            )
        super().delete(*args, **kwargs)


class Listing(models.Model):
    """
    Модель объявления о продаже внутриигрового предмета.
    """
    STATUS_CHOICES = [
        ('active', 'Активно'),
        ('reserved', 'Зарезервировано'),
        ('sold', 'Продано'),
        ('cancelled', 'Отменено'),
    ]
    
    seller = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='listings',
        verbose_name='Продавец'
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='listings',
        verbose_name='Игра'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='listings',
        null=True,
        blank=True,
        verbose_name='Категория',
        help_text='Категория товара (необязательно)'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    description = models.TextField(
        max_length=5000,
        verbose_name='Описание',
        help_text='Максимум 5000 символов'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Цена'
    )
    image = models.ImageField(
        upload_to='listings/',
        blank=True,
        null=True,
        validators=[validate_image_size, validate_image_type],
        verbose_name='Изображение'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        db_index=True,  # Добавлено для производительности
        verbose_name='Статус'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,  # Добавлено для производительности
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    # Full-text search vector
    search_vector = SearchVectorField(null=True, editable=False)
    
    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['game', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['-created_at', 'status']),
            GinIndex(fields=['search_vector']),  # Для full-text search
        ]
    
    def __str__(self):
        return f'{self.title} - {self.game.name}'
    
    def is_available(self):
        """Проверяет, доступно ли объявление для покупки."""
        return self.status == 'active'
    
    def save(self, *args, **kwargs):
        """Обновляем search_vector при сохранении."""
        super().save(*args, **kwargs)
        
        # Обновляем search_vector если изменились title или description
        if self.pk:
            from django.contrib.postgres.search import SearchVector
            Listing.objects.filter(pk=self.pk).update(
                search_vector=SearchVector('title', weight='A', config='russian') + 
                             SearchVector('description', weight='B', config='russian')
            )


class Report(models.Model):
    """
    Жалобы на объявления или пользователей.
    """
    REPORT_TYPE_CHOICES = [
        ('listing', 'На объявление'),
        ('user', 'На пользователя'),
    ]
    
    REASON_CHOICES = [
        ('spam', 'Спам'),
        ('fraud', 'Мошенничество'),
        ('inappropriate', 'Неприемлемый контент'),
        ('fake', 'Подделка'),
        ('other', 'Другое'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('reviewed', 'Рассмотрена'),
        ('resolved', 'Решена'),
        ('rejected', 'Отклонена'),
    ]
    
    reporter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name='Автор жалобы'
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        verbose_name='Тип жалобы'
    )
    listing = models.ForeignKey(
        'Listing',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name='Объявление'
    )
    reported_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports_received',
        verbose_name='Пользователь'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        verbose_name='Причина'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    admin_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий администратора'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата решения'
    )
    
    class Meta:
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.report_type == 'listing':
            return f'Жалоба на объявление: {self.listing.title if self.listing else "удалено"}'
        return f'Жалоба на пользователя: {self.reported_user.username if self.reported_user else "удален"}'

