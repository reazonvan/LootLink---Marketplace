#!/usr/bin/env python
"""
Скрипт для автоматического исправления фейковых email адресов на реальные.
Заменяет все @lootlink.com email на реальный email разработчика.

Запуск: python scripts/fix_fake_emails.py
"""
import os
import re
from pathlib import Path

# Реальный email для замены
REAL_EMAIL = "ivanpetrov20066.ip@gmail.com"

# Список фейковых email паттернов для замены
FAKE_EMAILS = [
    "support@lootlink.com",
    "tech@lootlink.com",
    "noreply@lootlink.com",
    "demo@lootlink.com",
    "admin@lootlink.com",
    "security@lootlink.com",
]

# Файлы для исправления (относительно корня проекта)
FILES_TO_FIX = [
    "templates/base.html",
    "templates/core/requisites.html",
    "templates/pages/about.html",
    "templates/pages/faq.html",
    "templates/404.html",
    "core/seo_utils.py",
]

def get_project_root():
    """Получить корень проекта"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

def replace_fake_emails_in_file(file_path, dry_run=False):
    """
    Заменить фейковые email в файле на реальные.
    
    Args:
        file_path: путь к файлу
        dry_run: если True, только показать что будет изменено
    
    Returns:
        int: количество замен
    """
    if not os.path.exists(file_path):
        print(f"  [!] Файл не найден: {file_path}")
        return 0
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    
    # Заменяем каждый фейковый email
    for fake_email in FAKE_EMAILS:
        if fake_email in content:
            count = content.count(fake_email)
            replacements += count
            content = content.replace(fake_email, REAL_EMAIL)
            print(f"    [OK] {fake_email} -> {REAL_EMAIL} ({count} раз)")
    
    # Если были изменения и это не пробный запуск
    if replacements > 0 and not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return replacements

def main(dry_run=False):
    """
    Основная функция.
    
    Args:
        dry_run: если True, только показать что будет изменено без реальных изменений
    """
    print("=" * 70)
    print("  ИСПРАВЛЕНИЕ ФЕЙКОВЫХ EMAIL АДРЕСОВ")
    print("=" * 70)
    print()
    
    if dry_run:
        print("[INFO] РЕЖИМ ПРОВЕРКИ (без изменения файлов)")
    else:
        print("[WARNING] РЕЖИМ ИСПРАВЛЕНИЯ (файлы будут изменены)")
    
    print()
    print(f"Реальный email: {REAL_EMAIL}")
    print()
    print("Фейковые email для замены:")
    for email in FAKE_EMAILS:
        print(f"  - {email}")
    print()
    
    # Подтверждение
    if not dry_run:
        response = input("Продолжить? (yes/no): ")
        if response.lower() not in ['yes', 'y', 'да']:
            print("[X] Отменено пользователем")
            return
        print()
    
    project_root = get_project_root()
    total_replacements = 0
    files_modified = 0
    
    print("Обработка файлов:")
    print()
    
    for relative_path in FILES_TO_FIX:
        full_path = os.path.join(project_root, relative_path)
        print(f"[FILE] {relative_path}")
        
        replacements = replace_fake_emails_in_file(full_path, dry_run)
        
        if replacements > 0:
            total_replacements += replacements
            files_modified += 1
        else:
            print("    [i] Изменений не требуется")
        
        print()
    
    # Итоги
    print("=" * 70)
    
    if dry_run:
        print(f"[STATS] Найдено для замены:")
        print(f"   - Файлов: {files_modified}")
        print(f"   - Замен: {total_replacements}")
        print()
        print("[TIP] Запустите без --dry-run для применения изменений:")
        print("   python scripts/fix_fake_emails.py")
    else:
        print(f"[SUCCESS] ГОТОВО!")
        print(f"   - Обработано файлов: {len(FILES_TO_FIX)}")
        print(f"   - Изменено файлов: {files_modified}")
        print(f"   - Выполнено замен: {total_replacements}")
        print()
        print("[NEXT] Следующие шаги:")
        print("   1. Проверьте изменения: git diff")
        print("   2. Обновите .env файл:")
        print(f"      DEFAULT_FROM_EMAIL={REAL_EMAIL}")
        print("   3. Удалите тестового пользователя:")
        print("      python scripts/cleanup_production.py")
    
    print("=" * 70)

if __name__ == '__main__':
    import sys
    
    # Проверяем аргументы
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    try:
        main(dry_run)
    except KeyboardInterrupt:
        print("\n\n[X] Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

