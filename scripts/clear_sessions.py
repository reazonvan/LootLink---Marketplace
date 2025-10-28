#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для очистки всех сессий Django.
Полезно когда есть проблемы с "зависшими" сессиями.
"""
import os
import sys
import django

# Для Windows - устанавливаем UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.sessions.models import Session
from django.core.cache import cache

def clear_all_sessions():
    """Очищает все сессии и кэш."""
    print("\n🧹 Очистка сессий и кэша...\n")
    
    # Очищаем все сессии
    session_count = Session.objects.count()
    print(f"📋 Найдено сессий: {session_count}")
    
    if session_count > 0:
        Session.objects.all().delete()
        print(f"✅ Удалено {session_count} сессий")
    else:
        print("✅ Сессий не найдено")
    
    # Очищаем кэш
    try:
        cache.clear()
        print("✅ Кэш очищен")
    except Exception as e:
        print(f"⚠️  Ошибка при очистке кэша: {e}")
    
    print("\n✅ Готово! Теперь перезагрузите страницу в браузере (Ctrl+Shift+R)\n")

if __name__ == '__main__':
    clear_all_sessions()

