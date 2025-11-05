#!/usr/bin/env python
"""
Скрипт для заполнения сайта демо-контентом
Запуск: python scripts/populate_demo_content.py
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print('═══════════════════════════════════════════')
    print('  ЗАПОЛНЕНИЕ ДЕМО-КОНТЕНТОМ')
    print('═══════════════════════════════════════════\n')
    
    # Создаем демо-объявления
    print('📦 Создание демо-объявлений...\n')
    call_command('create_demo_listings', count=30)
    
    print('\n═══════════════════════════════════════════')
    print('  ✅ ГОТОВО!')
    print('═══════════════════════════════════════════')
    print('\n💡 Теперь сайт выглядит намного живее!')
    print('🌐 Перейдите на http://localhost:8000 или http://91.218.245.178')

