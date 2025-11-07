"""
Модели для аудита безопасности и логирования важных действий.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class SecurityAuditLog(models.Model):
    """
    Лог всех важных действий в системе для аудита безопасности.
    Помогает отследить мошеннические действия и взломы.
    """
    
    ACTION_TYPES = [
        # Аутентификация
        ('login_success', 'Успешный вход'),
        ('login_failed', 'Неудачная попытка входа'),
        ('logout', 'Выход'),
        ('password_change', 'Смена пароля'),
        ('password_reset_request', 'Запрос сброса пароля'),
        ('password_reset_complete', 'Сброс пароля завершен'),
        ('2fa_enabled', '2FA включена'),
        ('2fa_disabled', '2FA отключена'),
        
        # Финансы
        ('balance_change', 'Изменение баланса'),
        ('withdrawal_request', 'Запрос на вывод'),
        ('withdrawal_complete', 'Вывод завершен'),
        ('deposit', 'Пополнение'),
        ('escrow_create', 'Создание escrow'),
        ('escrow_release', 'Освобождение escrow'),
        ('escrow_refund', 'Возврат escrow'),
        
        # Объявления
        ('listing_create', 'Создание объявления'),
        ('listing_edit', 'Редактирование объявления'),
        ('listing_delete', 'Удаление объявления'),
        
        # Транзакции
        ('purchase_request', 'Запрос на покупку'),
        ('purchase_accept', 'Принятие запроса'),
        ('purchase_reject', 'Отклонение запроса'),
        ('purchase_complete', 'Завершение сделки'),
        ('review_create', 'Создание отзыва'),
        
        # Безопасность
        ('account_locked', 'Блокировка аккаунта'),
        ('account_unlocked', 'Разблокировка аккаунта'),
        ('suspicious_activity', 'Подозрительная активность'),
        ('rate_limit_exceeded', 'Превышен лимит запросов'),
        ('idor_attempt', 'Попытка IDOR атаки'),
        ('report_create', 'Создание жалобы'),
        
        # Настройки
        ('profile_update', 'Обновление профиля'),
        ('email_change', 'Смена email'),
        ('phone_change', 'Смена телефона'),
    ]
    
    RISK_LEVELS = [
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('critical', 'Критический'),
    ]
    
    # Основная информация
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Пользователь',
        help_text='Может быть NULL для анонимных действий'
    )
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        db_index=True,
        verbose_name='Тип действия'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
        default='low',
        db_index=True,
        verbose_name='Уровень риска'
    )
    
    # Детали действия
    description = models.TextField(
        verbose_name='Описание',
        help_text='Детальное описание действия'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Метаданные',
        help_text='Дополнительные данные в JSON формате'
    )
    
    # Информация о запросе
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP адрес'
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='User Agent'
    )
    
    # Временные метки
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Лог аудита безопасности'
        verbose_name_plural = 'Логи аудита безопасности'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['risk_level', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Аноним'
        return f'[{self.risk_level.upper()}] {user_str}: {self.get_action_type_display()}'
    
    @classmethod
    def log(cls, action_type, user=None, description='', risk_level='low', 
            ip_address=None, user_agent='', metadata=None, request=None):
        """
        Создает запись в логе аудита.
        
        Args:
            action_type: Тип действия из ACTION_TYPES
            user: Пользователь (опционально)
            description: Описание действия
            risk_level: Уровень риска (low/medium/high/critical)
            ip_address: IP адрес
            user_agent: User Agent браузера
            metadata: Дополнительные данные (dict)
            request: Django request объект (автоматически извлечет IP и User-Agent)
        """
        # Если передан request, извлекаем из него данные
        if request:
            if not ip_address:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
            
            if not user_agent:
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            if not user and request.user.is_authenticated:
                user = request.user
        
        return cls.objects.create(
            user=user,
            action_type=action_type,
            risk_level=risk_level,
            description=description,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def get_suspicious_activity(cls, user, hours=24):
        """
        Получить подозрительную активность пользователя за последние N часов.
        
        Args:
            user: Пользователь
            hours: Количество часов назад
        
        Returns:
            QuerySet с подозрительными действиями
        """
        from datetime import timedelta
        threshold = timezone.now() - timedelta(hours=hours)
        
        return cls.objects.filter(
            user=user,
            created_at__gte=threshold,
            risk_level__in=['high', 'critical']
        )
    
    @classmethod
    def get_failed_login_attempts(cls, ip_address, minutes=15):
        """
        Получить количество неудачных попыток входа с IP за последние N минут.
        
        Args:
            ip_address: IP адрес
            minutes: Количество минут назад
        
        Returns:
            Количество попыток
        """
        from datetime import timedelta
        threshold = timezone.now() - timedelta(minutes=minutes)
        
        return cls.objects.filter(
            ip_address=ip_address,
            action_type='login_failed',
            created_at__gte=threshold
        ).count()


class DataChangeLog(models.Model):
    """
    Лог изменений критичных данных (для соответствия требованиям).
    Хранит историю изменений важных полей.
    """
    
    # Информация о записи
    model_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Модель'
    )
    object_id = models.PositiveIntegerField(
        db_index=True,
        verbose_name='ID объекта'
    )
    field_name = models.CharField(
        max_length=100,
        verbose_name='Поле'
    )
    
    # Изменения
    old_value = models.TextField(
        blank=True,
        verbose_name='Старое значение'
    )
    new_value = models.TextField(
        blank=True,
        verbose_name='Новое значение'
    )
    
    # Кто изменил
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='data_changes',
        verbose_name='Изменено пользователем'
    )
    
    # Когда
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата изменения'
    )
    
    class Meta:
        verbose_name = 'Лог изменения данных'
        verbose_name_plural = 'Логи изменений данных'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id', '-created_at']),
            models.Index(fields=['changed_by', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.model_name}#{self.object_id}.{self.field_name} изменено'
    
    @classmethod
    def log_change(cls, instance, field_name, old_value, new_value, changed_by):
        """
        Логирует изменение поля модели.
        
        Args:
            instance: Экземпляр модели
            field_name: Название поля
            old_value: Старое значение
            new_value: Новое значение
            changed_by: Пользователь, совершивший изменение
        """
        # Конвертируем значения в строки для хранения
        old_str = str(old_value) if old_value is not None else ''
        new_str = str(new_value) if new_value is not None else ''
        
        return cls.objects.create(
            model_name=instance.__class__.__name__,
            object_id=instance.pk,
            field_name=field_name,
            old_value=old_str,
            new_value=new_str,
            changed_by=changed_by
        )
