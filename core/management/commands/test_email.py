"""
Management command для тестирования email конфигурации.
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from core.email_service import EmailService
import sys


class Command(BaseCommand):
    help = 'Тестирование email конфигурации'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help='Email получателя для теста'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Только проверить настройки без отправки'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('='*70)
        self.stdout.write(self.style.HTTP_INFO('  EMAIL CONFIGURATION TEST'))
        self.stdout.write('='*70 + '\n')
        
        # Проверяем текущую конфигурацию
        self.stdout.write(self.style.WARNING('Текущая конфигурация:'))
        self.stdout.write(f'  Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'  Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'  TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'  From: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  User: {settings.EMAIL_HOST_USER or "(not set)"}')
        self.stdout.write(f'  Password: {"***" + settings.EMAIL_HOST_PASSWORD[-3:] if settings.EMAIL_HOST_PASSWORD else "(not set)"}\n')
        
        # Проверка на console backend
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            self.stdout.write(self.style.ERROR('ВНИМАНИЕ: EMAIL_BACKEND = console!'))
            self.stdout.write(self.style.ERROR('   Письма НЕ будут отправляться реально!\n'))
            self.stdout.write(self.style.WARNING('Для production настройте реальный SMTP:'))
            self.stdout.write('   1. Создайте email на Yandex/Gmail')
            self.stdout.write('   2. Получите пароль приложения')
            self.stdout.write('   3. Обновите .env файл')
            self.stdout.write('   4. Перезапустите сервер\n')
            self.stdout.write(self.style.HTTP_INFO('См. docs/EMAIL_PRODUCTION_SETUP.md для инструкций\n'))
            
            if not options['check_only']:
                self.stdout.write(self.style.WARNING('Тестовое письмо будет выведено в консоль (не отправлено)...\n'))
            else:
                return
        
        # Проверяем что все параметры заполнены
        if settings.EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
            missing = []
            if not settings.EMAIL_HOST_USER:
                missing.append('EMAIL_HOST_USER')
            if not settings.EMAIL_HOST_PASSWORD:
                missing.append('EMAIL_HOST_PASSWORD')
            
            if missing:
                self.stdout.write(self.style.ERROR(f'Не хватает параметров: {", ".join(missing)}'))
                self.stdout.write(self.style.ERROR('   Настройте их в .env файле\n'))
                return

        if options['check_only']:
            self.stdout.write(self.style.SUCCESS('Конфигурация выглядит корректно'))
            return
        
        # Отправка тестового письма
        recipient = options.get('to')
        
        if not recipient:
            recipient = input('\nВведите email для отправки тестового письма: ').strip()
        
        if not recipient:
            self.stdout.write(self.style.ERROR('Email получателя не указан'))
            return
        
        self.stdout.write(f'\n{self.style.WARNING("Отправка тестового письма на:")} {recipient}...\n')
        
        try:
            send_mail(
                subject='[TEST] LootLink Email Configuration Test',
                message='''
Поздравляем! Email настроен правильно и работает!

Теперь пользователи вашего сайта будут получать:
- Коды сброса пароля
- Ссылки верификации email
- Уведомления о покупках и продажах
- Уведомления о новых сообщениях

Ваш сайт готов к работе с реальными пользователями!

С уважением,
Команда LootLink
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False
            )
            
            self.stdout.write(self.style.SUCCESS('\nУСПЕХ! Письмо отправлено!'))
            self.stdout.write(self.style.SUCCESS(f'   Проверьте почту: {recipient}'))
            self.stdout.write(self.style.WARNING('   (Возможно письмо попало в SPAM)\n'))

            self.stdout.write('='*70)
            self.stdout.write(self.style.SUCCESS('EMAIL РАБОТАЕТ КОРРЕКТНО!'))
            self.stdout.write('='*70 + '\n')

        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR('\nОШИБКА АУТЕНТИФИКАЦИИ:'))
            self.stdout.write(self.style.ERROR(f'   {str(e)}\n'))
            self.stdout.write(self.style.WARNING('Проверьте:'))
            self.stdout.write('  1. EMAIL_HOST_USER (должен быть полный email)')
            self.stdout.write('  2. EMAIL_HOST_PASSWORD (пароль приложения, не основной)')
            self.stdout.write('  3. Для Gmail/Yandex требуется App Password')
            self.stdout.write('  4. Убедитесь что 2FA включена\n')
            
        except smtplib.SMTPException as e:
            self.stdout.write(self.style.ERROR(f'\nSMTP ОШИБКА: {str(e)}\n'))
            self.stdout.write(self.style.WARNING('Проверьте EMAIL_HOST и EMAIL_PORT\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nОШИБКА: {str(e)}\n'))
            self.stdout.write(self.style.WARNING('Проверьте логи: sudo journalctl -u lootlink -n 50\n'))


import smtplib  # Для обработки SMTP исключений

