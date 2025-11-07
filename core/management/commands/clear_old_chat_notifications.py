"""
Команда для очистки старых уведомлений о сообщениях.
"""
from django.core.management.base import BaseCommand
from core.models import Notification


class Command(BaseCommand):
    help = 'Удаляет все непрочитанные уведомления о сообщениях (для переключения на новую систему)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтвердить удаление',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'Эта команда удалит ВСЕ непрочитанные уведомления о сообщениях.\n'
                    'Запустите с флагом --confirm для подтверждения.'
                )
            )
            return
        
        count, _ = Notification.objects.filter(
            notification_type='new_message',
            is_read=False
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Удалено {count} старых уведомлений о сообщениях')
        )

