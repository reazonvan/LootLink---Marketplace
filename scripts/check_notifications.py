#!/usr/bin/env python
"""Проверка уведомлений о сообщениях"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Notification

notifs = Notification.objects.filter(
    notification_type='new_message',
    is_read=False
).values('id', 'user__username', 'title', 'message', 'link')

print('Непрочитанные уведомления о сообщениях:')
print('=' * 60)
for n in notifs:
    print(f"User: {n['user__username']}")
    print(f"Title: {n['title']}")
    print(f"Message: {n['message'][:100]}")
    print(f"Link: {n['link']}")
    print('-' * 60)

print(f'\nВсего непрочитанных: {len(notifs)}')

