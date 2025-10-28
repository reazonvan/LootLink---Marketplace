#!/usr/bin/env python
"""
Скрипт для проверки качества кода.
Запускает flake8, black (проверка), isort (проверка).
Использование: python scripts/check_code_quality.py
"""
import sys
import subprocess

def run_command(command, description):
    """Запускает команду и выводит результат."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True)
    return result.returncode == 0

def main():
    """Запускает все проверки качества кода."""
    print("🔍 ПРОВЕРКА КАЧЕСТВА КОДА")
    print("=" * 60)
    
    checks = [
        ("flake8 .", "Проверка стиля кода (Flake8)"),
        ("black --check .", "Проверка форматирования (Black)"),
        ("isort --check-only .", "Проверка сортировки импортов (isort)"),
    ]
    
    results = []
    for command, description in checks:
        success = run_command(command, description)
        results.append((description, success))
    
    # Итоговый отчет
    print(f"\n\n{'='*60}")
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*60}")
    
    all_passed = True
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {description}")
        if not success:
            all_passed = False
    
    print(f"{'='*60}")
    
    if all_passed:
        print("✅ Все проверки пройдены!")
        return 0
    else:
        print("❌ Некоторые проверки не пройдены!")
        print("\nДля автоматического исправления запустите:")
        print("  - black .")
        print("  - isort .")
        return 1

if __name__ == '__main__':
    sys.exit(main())

