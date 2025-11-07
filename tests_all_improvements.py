#!/usr/bin/env python
"""
Полный набор тестов для проверки всех внедренных улучшений.
Запуск: python tests_all_improvements.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.models_audit import SecurityAuditLog
import json

User = get_user_model()


class Colors:
    """ANSI цвета для красивого вывода."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(test_name, passed, details=''):
    """Красивый вывод результата теста."""
    status = f"{Colors.GREEN}✅ PASSED{Colors.RESET}" if passed else f"{Colors.RED}❌ FAILED{Colors.RESET}"
    print(f"  {status} | {test_name}")
    if details and not passed:
        print(f"         {Colors.YELLOW}└─ {details}{Colors.RESET}")


def print_section(title):
    """Красивый заголовок секции."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def test_secret_key():
    """Тест 1: SECRET_KEY настроен правильно."""
    try:
        # Проверяем что SECRET_KEY загружен
        secret_key = settings.SECRET_KEY
        
        # Проверяем что это не default значение
        is_secure = 'django-insecure' not in secret_key
        is_long_enough = len(secret_key) >= 50
        
        passed = is_secure and is_long_enough
        details = f"Length: {len(secret_key)}, Secure: {is_secure}" if not passed else ""
        
        print_test("SECRET_KEY безопасен и загружен из .env", passed, details)
        return passed
    except Exception as e:
        print_test("SECRET_KEY безопасен и загружен из .env", False, str(e))
        return False


def test_rate_limiting_configured():
    """Тест 2: Rate Limiting настроен."""
    try:
        throttle_classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
        throttle_rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        
        has_throttle_classes = len(throttle_classes) > 0
        has_throttle_rates = len(throttle_rates) >= 3
        
        passed = has_throttle_classes and has_throttle_rates
        details = f"Classes: {len(throttle_classes)}, Rates: {len(throttle_rates)}" if not passed else ""
        
        print_test("DRF Rate Limiting настроен", passed, details)
        return passed
    except Exception as e:
        print_test("DRF Rate Limiting настроен", False, str(e))
        return False


def test_connection_pooling():
    """Тест 3: Connection Pooling настроен."""
    try:
        conn_max_age = settings.DATABASES['default'].get('CONN_MAX_AGE', 0)
        
        passed = conn_max_age > 0
        details = f"CONN_MAX_AGE: {conn_max_age}" if not passed else ""
        
        print_test("Database Connection Pooling настроен", passed, details)
        return passed
    except Exception as e:
        print_test("Database Connection Pooling настроен", False, str(e))
        return False


def test_security_middleware():
    """Тест 4: Security Middleware добавлены."""
    try:
        middleware = settings.MIDDLEWARE
        
        required_middleware = [
            'core.middleware.SimpleRateLimitMiddleware',
            'core.middleware.SecurityHeadersMiddleware',
            'core.middleware_audit.BruteForceProtectionMiddleware',
            'core.middleware_audit.SecurityAuditMiddleware',
        ]
        
        all_present = all(mw in middleware for mw in required_middleware)
        
        missing = [mw for mw in required_middleware if mw not in middleware]
        details = f"Missing: {', '.join(missing)}" if missing else ""
        
        print_test("Security Middleware добавлены", all_present, details)
        return all_present
    except Exception as e:
        print_test("Security Middleware добавлены", False, str(e))
        return False


def test_celery_beat_tasks():
    """Тест 5: Celery Beat задачи настроены."""
    try:
        beat_schedule = settings.CELERY_BEAT_SCHEDULE
        
        required_tasks = [
            'auto-release-escrow-hourly',
            'check-pending-withdrawals-daily',
        ]
        
        all_present = all(task in beat_schedule for task in required_tasks)
        
        missing = [task for task in required_tasks if task not in beat_schedule]
        details = f"Missing: {', '.join(missing)}" if missing else ""
        
        print_test("Celery Beat задачи настроены", all_present, details)
        return all_present
    except Exception as e:
        print_test("Celery Beat задачи настроены", False, str(e))
        return False


def test_audit_log_model():
    """Тест 6: SecurityAuditLog модель работает."""
    try:
        # Пытаемся создать тестовую запись
        log = SecurityAuditLog.log(
            action_type='login_success',
            description='Test audit log entry',
            risk_level='low',
            metadata={'test': True}
        )
        
        # Проверяем что запись создана
        passed = log.id is not None
        
        # Удаляем тестовую запись
        if log.id:
            log.delete()
        
        print_test("SecurityAuditLog модель работает", passed)
        return passed
    except Exception as e:
        print_test("SecurityAuditLog модель работает", False, str(e))
        return False


def test_validators_imported():
    """Тест 7: Валидаторы импортируются."""
    try:
        from core.validators import SecureImageValidator, AvatarValidator, ListingImageValidator
        
        # Проверяем что классы существуют
        avatar_validator = AvatarValidator()
        listing_validator = ListingImageValidator()
        
        passed = True
        print_test("Image валидаторы импортируются", passed)
        return passed
    except Exception as e:
        print_test("Image валидаторы импортируются", False, str(e))
        return False


def test_api_permissions():
    """Тест 8: API permissions классы существуют."""
    try:
        from api.permissions import (
            IsOwnerOrReadOnly, IsReviewerOrReadOnly, 
            IsConversationParticipant, CanCreateReview
        )
        
        passed = True
        print_test("API Permission классы существуют", passed)
        return passed
    except Exception as e:
        print_test("API Permission классы существуют", False, str(e))
        return False


def test_celery_tasks():
    """Тест 9: Celery tasks импортируются."""
    try:
        from payments.tasks import auto_release_escrow, check_pending_withdrawals
        
        passed = True
        print_test("Celery tasks импортируются", passed)
        return passed
    except Exception as e:
        print_test("Celery tasks импортируются", False, str(e))
        return False


def test_password_reset_code_length():
    """Тест 10: Password reset коды используют 8 символов."""
    try:
        from accounts.models import PasswordResetCode
        
        code = PasswordResetCode.generate_code()
        
        passed = len(code) == 8
        details = f"Generated code length: {len(code)}" if not passed else ""
        
        print_test("Password reset коды 8 символов", passed, details)
        return passed
    except Exception as e:
        print_test("Password reset коды 8 символов", False, str(e))
        return False


def run_all_tests():
    """Запуск всех тестов."""
    print(f"\n{Colors.BOLD}🧪 ТЕСТИРОВАНИЕ ВСЕХ УЛУЧШЕНИЙ{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    tests = [
        ("БЕЗОПАСНОСТЬ", [
            test_secret_key,
            test_rate_limiting_configured,
            test_security_middleware,
            test_audit_log_model,
            test_api_permissions,
            test_password_reset_code_length,
            test_validators_imported,
        ]),
        ("ПРОИЗВОДИТЕЛЬНОСТЬ", [
            test_connection_pooling,
        ]),
        ("ФУНКЦИОНАЛЬНОСТЬ", [
            test_celery_beat_tasks,
            test_celery_tasks,
        ]),
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for section_name, section_tests in tests:
        print_section(section_name)
        
        for test_func in section_tests:
            total_tests += 1
            if test_func():
                passed_tests += 1
    
    # Итоги
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}ИТОГИ ТЕСТИРОВАНИЯ{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    color = Colors.GREEN if percentage == 100 else Colors.YELLOW if percentage >= 70 else Colors.RED
    
    print(f"  Всего тестов: {total_tests}")
    print(f"  {color}Успешно: {passed_tests}{Colors.RESET}")
    print(f"  {Colors.RED}Провалено: {total_tests - passed_tests}{Colors.RESET}")
    print(f"  {color}Процент: {percentage:.1f}%{Colors.RESET}\n")
    
    if percentage == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО! 🎉{Colors.RESET}\n")
    elif percentage >= 70:
        print(f"{Colors.YELLOW}⚠️  Большинство тестов прошло, но есть проблемы{Colors.RESET}\n")
    else:
        print(f"{Colors.RED}❌ Много проблем, требуется исправление{Colors.RESET}\n")
    
    return percentage == 100


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{Colors.RED}КРИТИЧЕСКАЯ ОШИБКА:{Colors.RESET} {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

