"""
Management команда для очистки некорректных значений в поле Game.icon
"""
from django.core.management.base import BaseCommand
from listings.models import Game


class Command(BaseCommand):
    help = 'Очищает некорректные значения в поле icon у игр'

    def handle(self, *args, **options):
        self.stdout.write('Поиск игр с некорректными иконками...')

        fixed_count = 0
        total_games = Game.objects.count()

        for game in Game.objects.all():
            # Если icon существует, но файла нет
            if game.icon and not game.icon.name:
                self.stdout.write(
                    self.style.WARNING(f'  {game.name}: icon="{game.icon}" (файл не существует)')
                )
                game.icon = None
                game.save()
                fixed_count += 1
            # Если icon.name содержит "bi-" (Bootstrap Icon класс)
            elif game.icon and game.icon.name and 'bi-' in game.icon.name:
                self.stdout.write(
                    self.style.WARNING(f'  {game.name}: icon="{game.icon.name}" (Bootstrap Icon класс)')
                )
                game.icon = None
                game.save()
                fixed_count += 1

        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nИсправлено: {fixed_count} из {total_games} игр')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nВсе иконки корректны ({total_games} игр проверено)')
            )

