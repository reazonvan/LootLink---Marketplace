from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from core.validators import AvatarValidator
import random
import string


# Import export model
from .models_export import DataExportRequest


class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя.
    Расширяет стандартную модель User Django.
    """
    email = models.EmailField(unique=True, verbose_name='Email')
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.username
    
    def delete(self, *args, **kwargs):
        """
        Запрещает удаление пользователя.
        Аккаунты существуют навсегда.
        """
        raise Exception('Удаление пользователей запрещено! Аккаунты существуют навсегда.')


class Profile(models.Model):
    """
    Профиль пользователя с дополнительной информацией.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        validators=[AvatarValidator()],
        verbose_name='Аватар',
        help_text='Макс. 2 МБ. Форматы: JPG, PNG, WebP'
    )
    cover_image = models.ImageField(
        upload_to='covers/',
        blank=True,
        null=True,
        verbose_name='Обложка профиля',
        help_text='Рекомендуемый размер: 1200x300px'
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='О себе'
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Телефон'
    )
    # Социальные сети удалены - общение только на сайте через встроенный чат
    
    # Telegram
    telegram_chat_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Telegram Chat ID'
    )
    telegram_notifications = models.BooleanField(
        default=False,
        verbose_name='Telegram уведомления'
    )
    
    # Баланс
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Баланс'
    )
    
    # Статистика
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        db_index=True,  # Добавлено для фильтрации по рейтингу
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='Рейтинг'
    )
    total_sales = models.PositiveIntegerField(
        default=0,
        verbose_name='Всего продаж'
    )
    total_purchases = models.PositiveIntegerField(
        default=0,
        verbose_name='Всего покупок'
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Верифицирован'
    )
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата верификации'
    )
    is_moderator = models.BooleanField(
        default=False,
        verbose_name='Модератор',
        help_text='Права модератора (просмотр жалоб, удаление контента)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя активность',
        help_text='Обновляется middleware при каждом запросе пользователя'
    )
    
    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
    
    def __str__(self):
        return f'Профиль {self.user.username}'
    
    def update_rating(self):
        """Обновляет рейтинг на основе отзывов с защитой от race condition."""
        from django.db.models import Avg
        from django.db import transaction
        from transactions.models import Review
        
        # Используем транзакцию и SELECT FOR UPDATE для предотвращения race condition
        with transaction.atomic():
            # Блокируем запись профиля для обновления
            profile = Profile.objects.select_for_update().get(id=self.id)
            
            reviews = Review.objects.filter(reviewed_user=profile.user)
            if reviews.exists():
                avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
                profile.rating = round(avg_rating, 2)
            else:
                profile.rating = 0.00
            
            profile.save(update_fields=['rating'])
        
        # Обновляем текущий объект из БД
        self.refresh_from_db()
    
    def get_online_status(self):
        """
        Возвращает онлайн-статус пользователя.
        
        Returns:
            str: 'online' или 'offline'
        """
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.last_seen:
            return 'offline'
        
        now = timezone.now()
        diff = now - self.last_seen
        
        # Онлайн: активность в последние 5 минут
        if diff < timedelta(minutes=5):
            return 'online'
        # Offline: более 5 минут назад
        else:
            return 'offline'
    
    def get_last_seen_display(self):
        """
        Возвращает читаемое представление последней активности.
        
        Returns:
            str: например "Онлайн", "5 минут назад", "Сегодня в 14:30"
        """
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.last_seen:
            return 'Не был(а) в сети'
        
        status = self.get_online_status()
        
        if status == 'online':
            return 'Онлайн'
        
        now = timezone.now()
        diff = now - self.last_seen
        
        # Менее часа - показываем минуты
        if diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} мин. назад'
        
        # Сегодня - показываем время
        if self.last_seen.date() == now.date():
            return f'Сегодня в {self.last_seen.strftime("%H:%M")}'
        
        # Вчера
        if self.last_seen.date() == (now.date() - timedelta(days=1)):
            return f'Вчера в {self.last_seen.strftime("%H:%M")}'
        
        # Другая дата
        return self.last_seen.strftime('%d.%m.%Y')
    
    def delete(self, *args, **kwargs):
        """
        Запрещает удаление профиля.
        Профили существуют навсегда.
        """
        raise Exception('Удаление профилей запрещено! Данные пользователя неизменны.')


# Сигнал для автоматического создания профиля при создании пользователя
@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Создает профиль при создании пользователя или обновляет существующий.
    Объединенный сигнал для предотвращения дублирования логики.
    """
    if created:
        Profile.objects.create(user=instance)
    elif hasattr(instance, 'profile'):
        # Обновляем профиль только если он уже существует
        instance.profile.save()


class EmailVerification(models.Model):
    """
    Модель для верификации email адреса пользователя.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='email_verification',
        verbose_name='Пользователь'
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Токен верификации'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Верифицирован'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата верификации'
    )
    
    class Meta:
        verbose_name = 'Верификация Email'
        verbose_name_plural = 'Верификации Email'
    
    def __str__(self):
        status = 'Верифицирован' if self.is_verified else 'Не верифицирован'
        return f'{self.user.username} - {status}'
    
    @classmethod
    def generate_token(cls):
        """Генерирует уникальный токен."""
        import secrets
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_for_user(cls, user):
        """Создает токен верификации для пользователя."""
        # Удаляем старые токены если есть
        cls.objects.filter(user=user).delete()
        
        token = cls.generate_token()
        return cls.objects.create(user=user, token=token)
    
    def verify(self):
        """Помечает email как верифицированный."""
        from django.utils import timezone
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
        
        # Обновляем статус пользователя
        self.user.profile.is_verified = True
        self.user.profile.verification_date = timezone.now()
        self.user.profile.save()


class PasswordResetCode(models.Model):
    """
    Модель для хранения кодов сброса пароля.
    Каждый код уникален и действует ограниченное время.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reset_codes',
        verbose_name='Пользователь'
    )
    code = models.CharField(
        max_length=10,  # 8 символов + запас на будущее
        verbose_name='Код подтверждения'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='Использован'
    )
    expires_at = models.DateTimeField(
        verbose_name='Действителен до'
    )

    class Meta:
        verbose_name = 'Код сброса пароля'
        verbose_name_plural = 'Коды сброса пароля'
        ordering = ['-created_at']

    def __str__(self):
        return f'Код {self.code} для {self.user.username}'

    @classmethod
    def generate_code(cls):
        """
        Генерирует безопасный 8-символьный буквенно-цифровой код.
        Использует uppercase буквы и цифры для удобства ввода (исключая похожие символы).
        Комбинаций: 32^8 = 1,099,511,627,776 (более триллиона)
        """
        # Исключаем похожие символы: 0/O, 1/I/L для удобства пользователя
        safe_chars = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'
        import secrets
        return ''.join(secrets.choice(safe_chars) for _ in range(8))

    @classmethod
    def create_code(cls, user):
        """Создаёт новый код для пользователя."""
        # Деактивируем все старые неиспользованные коды
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # Генерируем уникальный код (проверка на дубликаты)
        max_attempts = 10
        for attempt in range(max_attempts):
            code = cls.generate_code()
            # Проверяем что такого кода нет среди неиспользованных
            if not cls.objects.filter(code=code, is_used=False).exists():
                break
            if attempt == max_attempts - 1:
                # В крайнем случае используем timestamp для уникальности
                import time
                code = str(int(time.time() * 1000))[-6:]

        expires_at = timezone.now() + timezone.timedelta(minutes=15)

        return cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )

    def is_valid(self):
        """Проверяет, действителен ли код."""
        return not self.is_used and timezone.now() < self.expires_at

    def mark_as_used(self):
        """Помечает код как использованный."""
        self.is_used = True
        self.save()


class PhoneVerification(models.Model):
    """
    Модель для верификации телефона через SMS код.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='phone_verifications',
        verbose_name='Пользователь'
    )
    phone = models.CharField(
        max_length=20,
        verbose_name='Номер телефона'
    )
    code = models.CharField(
        max_length=6,
        verbose_name='Код верификации'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Верифицирован'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата верификации'
    )
    expires_at = models.DateTimeField(
        verbose_name='Действителен до'
    )
    attempts = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество попыток'
    )

    class Meta:
        verbose_name = 'Верификация телефона'
        verbose_name_plural = 'Верификации телефонов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_verified']),
            models.Index(fields=['phone', 'is_verified']),
        ]

    def __str__(self):
        status = 'Верифицирован' if self.is_verified else 'Не верифицирован'
        return f'{self.user.username} - {self.phone} - {status}'

    @classmethod
    def generate_code(cls):
        """Генерирует 6-значный код."""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    @classmethod
    def create_for_user(cls, user, phone):
        """Создает новую верификацию для пользователя."""
        # Деактивируем старые неверифицированные коды
        cls.objects.filter(user=user, phone=phone, is_verified=False).delete()

        code = cls.generate_code()
        expires_at = timezone.now() + timezone.timedelta(minutes=10)

        return cls.objects.create(
            user=user,
            phone=phone,
            code=code,
            expires_at=expires_at
        )

    def is_valid(self):
        """Проверяет, действителен ли код."""
        return not self.is_verified and timezone.now() < self.expires_at and self.attempts < 5

    def verify(self, entered_code):
        """
        Проверяет код и верифицирует телефон.
        Returns: (success: bool, message: str)
        """
        self.attempts += 1
        self.save()

        if self.attempts >= 5:
            return False, 'Превышено количество попыток. Запросите новый код.'

        if timezone.now() > self.expires_at:
            return False, 'Код истек. Запросите новый код.'

        if self.is_verified:
            return False, 'Телефон уже верифицирован.'

        if entered_code != self.code:
            return False, f'Неверный код. Осталось попыток: {5 - self.attempts}'

        # Верифицируем
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()

        # Обновляем профиль
        self.user.profile.is_verified = True
        self.user.profile.verification_date = timezone.now()
        self.user.profile.save()

        return True, 'Телефон успешно верифицирован!'


class DocumentVerification(models.Model):
    """
    Модель для верификации документов (KYC).
    """
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ('passport', 'Паспорт'),
        ('id_card', 'ID карта'),
        ('driver_license', 'Водительские права'),
        ('selfie', 'Селфи с документом'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='document_verifications',
        verbose_name='Пользователь'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        verbose_name='Тип документа'
    )
    document_file = models.FileField(
        upload_to='verification_documents/%Y/%m/',
        verbose_name='Файл документа',
        help_text='Макс. 10 МБ. Форматы: JPG, PNG, PDF'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='Статус'
    )
    admin_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий администратора'
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_documents',
        verbose_name='Проверил'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата проверки'
    )

    class Meta:
        verbose_name = 'Верификация документа'
        verbose_name_plural = 'Верификации документов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.get_document_type_display()} - {self.get_status_display()}'

    def approve(self, admin_user, comment=''):
        """Одобряет документ."""
        self.status = 'approved'
        self.admin_comment = comment
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()

        # Проверяем, все ли обязательные документы одобрены
        required_types = ['passport', 'selfie']
        approved_types = DocumentVerification.objects.filter(
            user=self.user,
            status='approved'
        ).values_list('document_type', flat=True)

        if all(doc_type in approved_types for doc_type in required_types):
            # Верифицируем пользователя
            self.user.profile.is_verified = True
            self.user.profile.verification_date = timezone.now()
            self.user.profile.save()

    def reject(self, admin_user, comment):
        """Отклоняет документ."""
        self.status = 'rejected'
        self.admin_comment = comment
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()

    def clean(self):
        """Валидация файла."""
        if self.document_file:
            # Проверка размера (макс 10 МБ)
            if self.document_file.size > 10 * 1024 * 1024:
                raise ValidationError('Размер файла не должен превышать 10 МБ.')

            # Проверка расширения
            import os
            ext = os.path.splitext(self.document_file.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            if ext not in allowed_extensions:
                raise ValidationError(f'Разрешены только файлы: {", ".join(allowed_extensions)}')

