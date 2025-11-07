"""
Команда для проверки уведомлений о сообщениях.
"""
from django.core.management.base import BaseCommand
from core.models import Notification


class Command(BaseCommand):
    help = 'Проверяет непрочитанные уведомления о сообщениях'

    def handle(self, *args, **options):
        notifs = Notification.objects.filter(
            notification_type='new_message',
            is_read=False
        ).select_related('user')
        
        self.stdout.write('Непрочитанные уведомления о сообщениях:')
        self.stdout.write('=' * 60)
        
        for n in notifs:
            self.stdout.write(f"\nUser: {n.user.username}")
            self.stdout.write(f"Title: {n.title}")
            self.stdout.write(f"Message: {n.message[:100]}")
            self.stdout.write(f"Link: {n.link}")
            self.stdout.write('-' * 60)
        
        self.stdout.write(self.style.SUCCESS(f'\nВсего непрочитанных: {len(notifs)}'))

