"""
Модели для безопасности: 2FA, история входов.
"""
from django.db import models
from django.utils import timezone
from .models import CustomUser


class LoginHistory(models.Model):
    """
    История входов пользователя.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name='Пользователь'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='IP адрес'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    device_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Тип устройства',
        help_text='Desktop, Mobile, Tablet'
    )
    browser = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Браузер'
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Местоположение',
        help_text='Город, страна'
    )
    
    success = models.BooleanField(
        default=True,
        verbose_name='Успешный вход'
    )
    failure_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Причина неудачи'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата и время'
    )
    
    class Meta:
        verbose_name = 'История входа'
        verbose_name_plural = 'История входов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def __str__(self):
        status = '✓' if self.success else '✗'
        return f'{status} {self.user.username} - {self.ip_address} - {self.created_at}'
    
    @classmethod
    def log_login(cls, user, request, success=True, failure_reason=''):
        """Логирование входа"""
        ip = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(
            user=user,
            ip_address=ip,
            user_agent=user_agent,
            device_type=cls.detect_device_type(user_agent),
            browser=cls.detect_browser(user_agent),
            success=success,
            failure_reason=failure_reason
        )
    
    @staticmethod
    def get_client_ip(request):
        """Получить IP клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def detect_device_type(user_agent):
        """Определить тип устройства"""
        user_agent_lower = user_agent.lower()
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
            return 'Mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            return 'Tablet'
        return 'Desktop'
    
    @staticmethod
    def detect_browser(user_agent):
        """Определить браузер"""
        user_agent_lower = user_agent.lower()
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            return 'Chrome'
        elif 'firefox' in user_agent_lower:
            return 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return 'Safari'
        elif 'edg' in user_agent_lower:
            return 'Edge'
        elif 'opera' in user_agent_lower or 'opr' in user_agent_lower:
            return 'Opera'
        return 'Other'


class SuspiciousActivity(models.Model):
    """
    Подозрительная активность.
    """
    ACTIVITY_TYPES = [
        ('multiple_failed_logins', 'Множественные неудачные входы'),
        ('unusual_location', 'Необычное местоположение'),
        ('unusual_device', 'Необычное устройство'),
        ('too_many_requests', 'Слишком много запросов'),
        ('suspicious_purchase', 'Подозрительная покупка'),
    ]
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='suspicious_activities',
        verbose_name='Пользователь'
    )
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        verbose_name='Тип активности'
    )
    description = models.TextField(
        verbose_name='Описание'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP адрес'
    )
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Низкая'),
            ('medium', 'Средняя'),
            ('high', 'Высокая'),
            ('critical', 'Критическая'),
        ],
        default='medium',
        verbose_name='Серьезность'
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name='Разрешено'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Дата'
    )
    
    class Meta:
        verbose_name = 'Подозрительная активность'
        verbose_name_plural = 'Подозрительная активность'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['severity', 'is_resolved']),
        ]
    
    def __str__(self):
        return f'{self.get_activity_type_display()} - {self.user.username}'

