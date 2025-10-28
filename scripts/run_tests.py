#!/usr/bin/env python
"""
Скрипт для запуска тестов с покрытием кода.
Использование: python scripts/run_tests.py
"""
import os
import sys
import subprocess

def main():
    """Запускает тесты с coverage."""
    print("🧪 Запуск тестов с измерением покрытия кода...")
    print("=" * 60)
    
    # Запускаем pytest с coverage
    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing',
        '--verbose'
    ])
    
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ Все тесты пройдены!")
        print("📊 Отчет о покрытии сохранен в htmlcov/index.html")
    else:
        print("❌ Некоторые тесты не прошли!")
        sys.exit(1)

if __name__ == '__main__':
    main()

