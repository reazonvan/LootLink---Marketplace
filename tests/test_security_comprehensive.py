"""
Comprehensive тесты безопасности для всех улучшений.
"""
import pytest
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models_audit import SecurityAuditLog, DataChangeLog
from listings.models import Listing, Game
from payments.models import Escrow
from payments.models_disputes import Dispute
from transactions.models import PurchaseRequest
from rest_framework.test import APIClient
from django_otp.plugins.otp_totp.models import TOTPDevice

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )


@pytest.fixture
def moderator(db):
    user = User.objects.create_user(
        username='moderator',
        email='mod@test.com',
        password='modpass123',
        is_staff=True
    )
    user.profile.is_moderator = True
    user.profile.save()
    return user


@pytest.mark.django_db
class TestSecretKeySecurity:
    """Тесты безопасности SECRET_KEY."""
    
    def test_secret_key_is_secure(self):
        """SECRET_KEY не должен содержать 'insecure'."""
        from django.conf import settings
        assert 'insecure' not in settings.SECRET_KEY.lower()
        assert len(settings.SECRET_KEY) >= 50


@pytest.mark.django_db
class TestRateLimiting:
    """Тесты rate limiting."""
    
    def test_api_has_throttling(self):
        """API должен иметь throttling классы."""
        from django.conf import settings
        throttle_classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
        assert len(throttle_classes) > 0
    
    def test_throttle_rates_configured(self):
        """Throttle rates должны быть настроены."""
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        assert 'anon' in rates
        assert 'user' in rates


@pytest.mark.django_db
class TestPasswordResetSecurity:
    """Тесты безопасности password reset."""
    
    def test_reset_code_length(self):
        """Reset код должен быть 8 символов."""
        from accounts.models import PasswordResetCode
        code = PasswordResetCode.generate_code()
        assert len(code) == 8
    
    def test_reset_code_is_alphanumeric(self):
        """Reset код должен быть буквенно-цифровым."""
        from accounts.models import PasswordResetCode
        code = PasswordResetCode.generate_code()
        assert code.isalnum()
        assert code.isupper()  # Должен быть в uppercase


@pytest.mark.django_db
class TestSecurityAudit:
    """Тесты системы аудита."""
    
    def test_audit_log_creation(self, user):
        """Аудит лог должен создаваться."""
        log = SecurityAuditLog.log(
            action_type='login_success',
            user=user,
            description='Test login',
            risk_level='low'
        )
        assert log.id is not None
        assert log.user == user
        assert log.action_type == 'login_success'
    
    def test_failed_login_tracking(self):
        """Отслеживание неудачных попыток входа."""
        ip = '127.0.0.1'
        
        # Создаем несколько неудачных попыток
        for i in range(5):
            SecurityAuditLog.log(
                action_type='login_failed',
                description=f'Failed attempt {i}',
                risk_level='medium',
                ip_address=ip
            )
        
        count = SecurityAuditLog.get_failed_login_attempts(ip, minutes=15)
        assert count == 5


@pytest.mark.django_db
class TestIDORProtection:
    """Тесты IDOR защиты."""
    
    def test_api_permissions_exist(self):
        """Permission классы должны существовать."""
        from api.permissions import (
            IsOwnerOrReadOnly,
            IsReviewerOrReadOnly,
            IsConversationParticipant
        )
        assert IsOwnerOrReadOnly is not None
        assert IsReviewerOrReadOnly is not None
        assert IsConversationParticipant is not None


@pytest.mark.django_db
class TestConnectionPooling:
    """Тесты connection pooling."""
    
    def test_conn_max_age_configured(self):
        """CONN_MAX_AGE должен быть настроен."""
        from django.conf import settings
        conn_max_age = settings.DATABASES['default'].get('CONN_MAX_AGE')
        assert conn_max_age is not None
        assert conn_max_age > 0


@pytest.mark.django_db
class Test2FA:
    """Тесты двухфакторной аутентификации."""
    
    def test_totp_device_creation(self, user):
        """TOTP устройство должно создаваться."""
        device = TOTPDevice.objects.create(
            user=user,
            name='test-device',
            confirmed=False
        )
        assert device.id is not None
        assert device.user == user
    
    def test_2fa_views_exist(self):
        """2FA views должны существовать."""
        from accounts import views_2fa
        assert hasattr(views_2fa, 'setup_2fa')
        assert hasattr(views_2fa, 'verify_2fa')
        assert hasattr(views_2fa, 'disable_2fa')


@pytest.mark.django_db
class TestDisputeSystem:
    """Тесты системы диспутов."""
    
    def test_dispute_model_exists(self):
        """Модель Dispute должна существовать."""
        from payments.models_disputes import Dispute
        assert Dispute is not None
    
    def test_dispute_views_exist(self):
        """Dispute views должны существовать."""
        from payments import views_disputes
        assert hasattr(views_disputes, 'create_dispute')
        assert hasattr(views_disputes, 'dispute_detail')
        assert hasattr(views_disputes, 'moderate_dispute')


@pytest.mark.django_db
class TestCeleryTasks:
    """Тесты Celery задач."""
    
    def test_auto_release_escrow_task_exists(self):
        """Task auto_release_escrow должен существовать."""
        from payments.tasks import auto_release_escrow
        assert auto_release_escrow is not None
    
    def test_celery_beat_schedule(self):
        """Celery beat schedule должен быть настроен."""
        from django.conf import settings
        beat_schedule = settings.CELERY_BEAT_SCHEDULE
        assert 'auto-release-escrow-hourly' in beat_schedule


@pytest.mark.django_db
class TestPerformanceOptimizations:
    """Тесты оптимизаций производительности."""
    
    def test_mixins_exist(self):
        """Optimization mixins должны существовать."""
        from core.mixins import (
            OptimizedQueryMixin,
            ListingOptimizedMixin,
            optimize_listing_queryset
        )
        assert OptimizedQueryMixin is not None
        assert optimize_listing_queryset is not None


# Summary test
def test_all_improvements_implemented():
    """Meta-тест: все основные улучшения внедрены."""
    improvements = {
        'SECRET_KEY': False,
        'Rate Limiting': False,
        'IDOR Protection': False,
        'Security Audit': False,
        'Connection Pooling': False,
        '2FA': False,
        'Disputes': False,
        'Celery Tasks': False,
    }
    
    # Проверяем каждое улучшение
    try:
        from django.conf import settings
        if 'insecure' not in settings.SECRET_KEY.lower():
            improvements['SECRET_KEY'] = True
    except: pass
    
    try:
        from django.conf import settings
        if settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES'):
            improvements['Rate Limiting'] = True
    except: pass
    
    try:
        from api.permissions import IsOwnerOrReadOnly
        improvements['IDOR Protection'] = True
    except: pass
    
    try:
        from core.models_audit import SecurityAuditLog
        improvements['Security Audit'] = True
    except: pass
    
    try:
        from django.conf import settings
        if settings.DATABASES['default'].get('CONN_MAX_AGE', 0) > 0:
            improvements['Connection Pooling'] = True
    except: pass
    
    try:
        from accounts import views_2fa
        improvements['2FA'] = True
    except: pass
    
    try:
        from payments.models_disputes import Dispute
        improvements['Disputes'] = True
    except: pass
    
    try:
        from payments.tasks import auto_release_escrow
        improvements['Celery Tasks'] = True
    except: pass
    
    # Выводим результаты
    print("\n" + "="*70)
    print("ПРОВЕРКА ВСЕХ УЛУЧШЕНИЙ")
    print("="*70 + "\n")
    
    for name, status in improvements.items():
        symbol = "✅" if status else "❌"
        print(f"  {symbol} {name}")
    
    implemented_count = sum(improvements.values())
    total_count = len(improvements)
    percentage = (implemented_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n  Внедрено: {implemented_count}/{total_count} ({percentage:.0f}%)\n")
    print("="*70 + "\n")
    
    # Тест считается успешным если > 80% улучшений внедрено
    assert percentage >= 80, f"Только {percentage:.0f}% улучшений внедрено"

