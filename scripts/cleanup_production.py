#!/usr/bin/env python
"""
Очистка тестовых данных для production
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from listings.models import Listing
from accounts.models import CustomUser
from django.core.cache import cache

print('🧹 Очистка production данных...')
print('')

# Удаляем неприличное объявление
try:
    bad_listing = Listing.objects.get(id=10)
    bad_listing.delete()
    print('✅ Удалено неприличное объявление #10')
except Listing.DoesNotExist:
    print('  Объявление #10 уже удалено')

# Деактивируем DemoSeller
try:
    demo = CustomUser.objects.get(username='DemoSeller')
    demo.is_active = False
    demo.save()
    print('✅ DemoSeller деактивирован')
except CustomUser.DoesNotExist:
    print('  DemoSeller не найден')

# Очищаем кеш
cache.clear()
print('✅ Весь кеш очищен')

print('')
print('✅ Очистка завершена!')
print('')
print('📊 Проверьте https://lootlink.ru/')

