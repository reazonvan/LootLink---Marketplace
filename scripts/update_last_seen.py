#!/usr/bin/env python
"""
Обновляет last_seen для всех профилей
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import Profile
from django.utils import timezone

# Обновляем профили без last_seen (ставим 30 дней назад)
updated = Profile.objects.filter(last_seen__isnull=True).update(
    last_seen=timezone.now() - timezone.timedelta(days=30)
)

print(f'✅ Обновлено профилей: {updated}')
print('Теперь онлайн-статус будет работать корректно')

