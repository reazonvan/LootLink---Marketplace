#!/usr/bin/env python
"""
Автоматическая настройка окружения разработки.
Создает .env файл, базу данных, применяет миграции, создает суперпользователя.
"""
import os
import sys
import subprocess
import secrets
from pathlib import Path

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


def print_step(number, text):
    """Print step number."""
    print(f"\n{YELLOW}[{number}]{RESET} {text}")


def run_command(command, shell=True, check=True):
    """Run shell command."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def generate_secret_key():
    """Generate Django SECRET_KEY."""
    return ''.join(secrets.choice(
        'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    ) for _ in range(50))


def main():
    """Main setup function."""
    print_header("LootLink Development Setup")
    
    # Проверка Python версии
    if sys.version_info < (3, 10):
        print(f"{RED}❌ Python 3.10+ required. Current: {sys.version}{RESET}")
        return 1
    
    # Определяем корень проекта
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print(f"Project root: {project_root}")
    
    # Шаг 1: Создать .env файл
    print_step(1, "Creating .env file")
    
    env_file = project_root / '.env'
    
    if env_file.exists():
        overwrite = input(f"{YELLOW}.env already exists. Overwrite? (y/N): {RESET}")
        if overwrite.lower() != 'y':
            print("Skipping .env creation")
        else:
            create_env_file(env_file)
    else:
        create_env_file(env_file)
    
    # Шаг 2: Установить зависимости
    print_step(2, "Installing Python dependencies")
    
    success, stdout, stderr = run_command("pip install -r requirements.txt")
    
    if success:
        print(f"{GREEN}✓ Dependencies installed{RESET}")
    else:
        print(f"{RED}✗ Failed to install dependencies{RESET}")
        print(stderr)
        return 1
    
    # Шаг 3: Проверить PostgreSQL
    print_step(3, "Checking PostgreSQL")
    
    success, _, _ = run_command("psql --version")
    
    if success:
        print(f"{GREEN}✓ PostgreSQL installed{RESET}")
        
        # Создать БД
        db_name = 'lootlink_db'
        print(f"Creating database '{db_name}'...")
        
        # Попытка создать БД
        success, stdout, stderr = run_command(
            f'psql -U postgres -c "CREATE DATABASE {db_name};"',
            check=False
        )
        
        if 'already exists' in stderr:
            print(f"{YELLOW}⚠ Database already exists{RESET}")
        elif success:
            print(f"{GREEN}✓ Database created{RESET}")
        else:
            print(f"{RED}✗ Failed to create database{RESET}")
            print(f"{YELLOW}Please create database manually:{RESET}")
            print(f"  psql -U postgres -c \"CREATE DATABASE {db_name};\"")
    else:
        print(f"{RED}✗ PostgreSQL not found{RESET}")
        print("Install PostgreSQL: https://www.postgresql.org/download/")
        return 1
    
    # Шаг 4: Применить миграции
    print_step(4, "Applying migrations")
    
    success, stdout, stderr = run_command("python manage.py migrate")
    
    if success:
        print(f"{GREEN}✓ Migrations applied{RESET}")
    else:
        print(f"{RED}✗ Migrations failed{RESET}")
        print(stderr)
        return 1
    
    # Шаг 5: Создать суперпользователя
    print_step(5, "Creating superuser")
    
    print(f"\n{BLUE}Please enter superuser credentials:{RESET}")
    success, stdout, stderr = run_command(
        "python manage.py createsuperuser",
        check=False
    )
    
    if not success and 'already exists' not in stderr:
        print(f"{YELLOW}⚠ Superuser creation skipped{RESET}")
    
    # Шаг 6: Собрать статику
    print_step(6, "Collecting static files")
    
    success, stdout, stderr = run_command("python manage.py collectstatic --noinput")
    
    if success:
        print(f"{GREEN}✓ Static files collected{RESET}")
    else:
        print(f"{RED}✗ Failed to collect static{RESET}")
    
    # Шаг 7: Загрузить тестовые данные
    print_step(7, "Loading test data (optional)")
    
    load_test = input(f"{YELLOW}Load test data? (y/N): {RESET}")
    
    if load_test.lower() == 'y':
        test_script = project_root / 'scripts' / 'create_test_data.py'
        if test_script.exists():
            success, stdout, stderr = run_command(f"python {test_script}")
            if success:
                print(f"{GREEN}✓ Test data loaded{RESET}")
        else:
            print(f"{YELLOW}⚠ Test data script not found{RESET}")
    
    # Финал
    print_header("Setup Complete!")
    
    print(f"{GREEN}✅ Development environment is ready!{RESET}\n")
    print("Next steps:")
    print(f"  1. Review .env file: {BLUE}nano .env{RESET}")
    print(f"  2. Start server: {BLUE}python manage.py runserver{RESET}")
    print(f"  3. Visit: {BLUE}http://127.0.0.1:8000{RESET}")
    print(f"  4. Admin panel: {BLUE}http://127.0.0.1:8000/admin{RESET}\n")
    
    return 0


def create_env_file(env_file):
    """Create .env file with generated values."""
    secret_key = generate_secret_key()
    
    env_content = f"""# LootLink Environment Configuration
# Generated automatically by setup_dev.py

# Django Settings
SECRET_KEY={secret_key}
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings (PostgreSQL)
DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Email Settings (Console backend for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@lootlink.com

# AWS S3 (disabled for development)
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1

# Redis (disabled for development)
USE_REDIS=False
REDIS_URL=redis://127.0.0.1:6379/1

# Sentry (disabled for development)
SENTRY_DSN=
ENVIRONMENT=development
RELEASE_VERSION=1.0.0
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"{GREEN}✓ .env file created{RESET}")
    print(f"  SECRET_KEY: {secret_key[:20]}...{secret_key[-10:]}")


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Setup cancelled by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}❌ Unexpected error: {e}{RESET}")
        sys.exit(1)

