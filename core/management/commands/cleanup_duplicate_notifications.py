"""
Команда для очистки дублирующихся уведомлений о новых сообщениях.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import Notification


class Command(BaseCommand):
    help = 'Удаляет дублирующиеся непрочитанные уведомления о сообщениях'

    def handle(self, *args, **options):
        # Находим дубликаты: одинаковые user + notification_type + link + is_read=False
        duplicates = (
            Notification.objects
            .filter(notification_type='new_message', is_read=False)
            .values('user', 'link')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        total_deleted = 0
        
        for dup in duplicates:
            # Для каждой группы дубликатов оставляем только самое новое
            notifications = Notification.objects.filter(
                user_id=dup['user'],
                notification_type='new_message',
                link=dup['link'],
                is_read=False
            ).order_by('-created_at')
            
            # Удаляем все кроме первого (самого нового)
            notifications_to_delete = notifications[1:]
            count = len(notifications_to_delete)
            
            if count > 0:
                for notif in notifications_to_delete:
                    notif.delete()
                    total_deleted += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Удалено {count} дубликатов для пользователя {dup["user"]}, ссылка {dup["link"]}'
                    )
                )
        
        if total_deleted > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Всего удалено дублирующихся уведомлений: {total_deleted}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Дублирующихся уведомлений не найдено')
            )

