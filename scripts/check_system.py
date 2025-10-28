#!/usr/bin/env python
"""
Скрипт проверки готовности системы к запуску.
Проверяет все зависимости, конфигурации и подключения.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from decouple import config

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print colored header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def check_item(name, status, details=""):
    """Print check result."""
    # Windows-compatible symbols
    symbol = f"{GREEN}[OK]{RESET}" if status else f"{RED}[FAIL]{RESET}"
    print(f"{symbol} {name}", end="")
    if details:
        print(f" - {details}")
    else:
        print()


def main():
    """Main system check."""
    print_header("LootLink System Check")
    
    errors = []
    warnings = []
    
    # 1. Python Version
    print(f"{YELLOW}1. Python Environment{RESET}")
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    check_item("Python Version", sys.version_info >= (3, 10), python_version)
    if sys.version_info < (3, 10):
        errors.append("Python 3.10+ required")
    
    # 2. Django
    print(f"\n{YELLOW}2. Django Configuration{RESET}")
    import django
    check_item("Django Version", True, django.get_version())
    check_item("DEBUG Mode", not settings.DEBUG, f"DEBUG={settings.DEBUG}")
    if settings.DEBUG:
        warnings.append("DEBUG=True не для production!")
    
    check_item("SECRET_KEY", len(settings.SECRET_KEY) > 50, f"{len(settings.SECRET_KEY)} chars")
    if settings.SECRET_KEY == 'django-insecure-dev-key-change-in-production':
        errors.append("SECRET_KEY не изменен!")
    
    check_item("ALLOWED_HOSTS", len(settings.ALLOWED_HOSTS) > 0, ", ".join(settings.ALLOWED_HOSTS))
    
    # 3. Database
    print(f"\n{YELLOW}3. Database (PostgreSQL){RESET}")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()[0]
            check_item("PostgreSQL Connection", True, db_version.split(',')[0])
            
            # Проверка таблиц
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            check_item("Tables Created", table_count > 10, f"{table_count} tables")
            
            # Проверка индексов
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            index_count = cursor.fetchone()[0]
            check_item("Database Indexes", index_count > 15, f"{index_count} indexes")
            
    except Exception as e:
        check_item("PostgreSQL Connection", False, str(e))
        errors.append(f"Database error: {e}")
    
    # 4. Cache (Redis)
    print(f"\n{YELLOW}4. Cache (Redis){RESET}")
    try:
        cache.set('test_key', 'test_value', 10)
        value = cache.get('test_key')
        redis_working = value == 'test_value'
        check_item("Redis Connection", redis_working, "OK" if redis_working else "Failed")
        
        if settings.USE_REDIS:
            check_item("Redis Enabled", True, settings.CACHES['default']['LOCATION'])
        else:
            check_item("Redis Enabled", False, "Using LocMemCache")
            warnings.append("Redis не включен - низкая производительность")
    except Exception as e:
        check_item("Redis Connection", False, str(e))
        warnings.append(f"Redis недоступен: {e}")
    
    # 5. Static Files
    print(f"\n{YELLOW}5. Static & Media Files{RESET}")
    check_item("STATIC_ROOT", os.path.exists(settings.STATIC_ROOT), settings.STATIC_ROOT)
    check_item("MEDIA_ROOT", os.path.exists(settings.MEDIA_ROOT), settings.MEDIA_ROOT)
    
    if settings.USE_S3:
        check_item("AWS S3 Enabled", True, settings.AWS_STORAGE_BUCKET_NAME)
    else:
        check_item("AWS S3 Enabled", False, "Using local storage")
    
    # 6. Email
    print(f"\n{YELLOW}6. Email Configuration{RESET}")
    check_item("EMAIL_BACKEND", True, settings.EMAIL_BACKEND.split('.')[-1])
    
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        check_item("SMTP Host", len(settings.EMAIL_HOST) > 0, settings.EMAIL_HOST)
        check_item("SMTP User", len(settings.EMAIL_HOST_USER) > 0, settings.EMAIL_HOST_USER)
    else:
        warnings.append("Используется Console Email Backend - письма не отправляются")
    
    # 7. Security
    print(f"\n{YELLOW}7. Security Settings{RESET}")
    
    if not settings.DEBUG:
        check_item("SECURE_SSL_REDIRECT", settings.SECURE_SSL_REDIRECT)
        check_item("SESSION_COOKIE_SECURE", settings.SESSION_COOKIE_SECURE)
        check_item("CSRF_COOKIE_SECURE", settings.CSRF_COOKIE_SECURE)
        check_item("SECURE_HSTS_SECONDS", settings.SECURE_HSTS_SECONDS > 0)
    else:
        check_item("Production Security", False, "DEBUG=True")
    
    check_item("SESSION_COOKIE_HTTPONLY", settings.SESSION_COOKIE_HTTPONLY)
    check_item("CSRF_COOKIE_HTTPONLY", settings.CSRF_COOKIE_HTTPONLY)
    
    # 8. Monitoring
    print(f"\n{YELLOW}8. Monitoring & Logging{RESET}")
    
    logs_dir = settings.BASE_DIR / 'logs'
    check_item("Logs Directory", os.path.exists(logs_dir), str(logs_dir))
    
    if hasattr(settings, 'SENTRY_DSN'):
        sentry_dsn = config('SENTRY_DSN', default='')
        check_item("Sentry DSN", len(sentry_dsn) > 0, "Configured" if sentry_dsn else "Not set")
        if not sentry_dsn:
            warnings.append("Sentry не настроен - ошибки не отслеживаются")
    
    # 9. Applications
    print(f"\n{YELLOW}9. Django Applications{RESET}")
    apps = ['accounts', 'listings', 'transactions', 'chat', 'core']
    for app in apps:
        # Check if app.apps.AppConfig format is in INSTALLED_APPS
        app_installed = any(
            app in installed_app.lower() 
            for installed_app in settings.INSTALLED_APPS
        )
        check_item(f"{app} installed", app_installed)
    
    # 10. Middleware
    print(f"\n{YELLOW}10. Middleware{RESET}")
    required_middleware = [
        'django.middleware.security.SecurityMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'core.middleware.SimpleRateLimitMiddleware',
        'core.middleware.SecurityHeadersMiddleware',
    ]
    
    for middleware in required_middleware:
        middleware_name = middleware.split('.')[-1]
        check_item(middleware_name, middleware in settings.MIDDLEWARE)
    
    # Summary
    print_header("Summary")
    
    if errors:
        print(f"{RED}[!] ERRORS ({len(errors)}){RESET}")
        for error in errors:
            print(f"  - {error}")
        print()
    
    if warnings:
        print(f"{YELLOW}[!] WARNINGS ({len(warnings)}){RESET}")
        for warning in warnings:
            print(f"  - {warning}")
        print()
    
    if not errors and not warnings:
        print(f"{GREEN}[OK] All checks passed! System ready.{RESET}\n")
        return 0
    elif not errors:
        print(f"{YELLOW}[!] System is operational but has warnings.{RESET}\n")
        return 0
    else:
        print(f"{RED}[ERROR] Critical errors found. Fix before running!{RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())

