"""
Management команда для удаления тестовых данных перед production
"""
from django.core.management.base import BaseCommand
from listings.models import Listing
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Удаляет тестовые объявления и демо-пользователей'

    def handle(self, *args, **options):
        self.stdout.write('🧹 Очистка тестовых данных...')
        
        # Удаляем объявления от DemoSeller
        demo_listings = Listing.objects.filter(
            seller__username='DemoSeller'
        )
        demo_count = demo_listings.count()
        
        if demo_count > 0:
            self.stdout.write(f'  📦 Найдено {demo_count} тестовых объявлений от DemoSeller')
            demo_listings.delete()
            self.stdout.write(self.style.SUCCESS(f'  ✅ Удалено {demo_count} тестовых объявлений'))
        else:
            self.stdout.write('  ✅ Тестовых объявлений не найдено')
        
        # Удаляем пользователя DemoSeller (если он не нужен)
        try:
            demo_user = CustomUser.objects.get(username='DemoSeller')
            # Проверяем что у него нет реальных данных
            if not demo_user.listings.exists():
                demo_user.delete()
                self.stdout.write(self.style.SUCCESS('  ✅ Удален пользователь DemoSeller'))
        except CustomUser.DoesNotExist:
            pass
        
        # Очистка кеша статистики
        from django.core.cache import cache
        cache.delete('homepage_stats')
        self.stdout.write(self.style.SUCCESS('  ✅ Кеш статистики очищен'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Очистка завершена!'))
        self.stdout.write('')
        self.stdout.write('📊 Теперь на сайте будут отображаться только РЕАЛЬНЫЕ данные')

