"""
Django management command для создания недостающих профилей.
Запуск: python manage.py create_profiles
"""
from django.core.management.base import BaseCommand
from accounts.models import CustomUser, Profile


class Command(BaseCommand):
    help = 'Создает профили для всех пользователей, у которых их нет'
    
    def handle(self, *args, **options):
        self.stdout.write("Начинаем проверку пользователей...")
        
        users = CustomUser.objects.all()
        total_users = users.count()
        created_count = 0
        exists_count = 0
        
        for user in users:
            try:
                # Пытаемся получить профиль
                profile = user.profile
                exists_count += 1
            except Profile.DoesNotExist:
                # Создаем профиль если его нет
                Profile.objects.create(user=user)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Создан профиль для пользователя: {user.username}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Ошибка для пользователя {user.username}: {e}")
                )
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("РЕЗУЛЬТАТЫ:"))
        self.stdout.write(f"Всего пользователей: {total_users}")
        self.stdout.write(f"Уже имели профиль: {exists_count}")
        self.stdout.write(f"Создано новых профилей: {created_count}")
        self.stdout.write("="*50)

