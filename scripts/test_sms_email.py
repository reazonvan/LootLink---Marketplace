#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования отправки Email и SMS.
Использование: python scripts/test_sms_email.py
"""
import os
import sys
import django

# Для Windows - устанавливаем UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from core.sms_service import send_sms


def test_email():
    """Тестирует отправку email."""
    print("\n📧 Тестирование отправки Email...")
    print(f"   Backend: {settings.EMAIL_BACKEND}")
    print(f"   Host: {settings.EMAIL_HOST}")
    print(f"   User: {settings.EMAIL_HOST_USER or 'НЕ НАСТРОЕН'}")
    
    if not settings.EMAIL_HOST_USER:
        print("   ⚠️  Email не настроен (используется console backend)")
        print("   📝 Письма выводятся в консоль сервера\n")
        return False
    
    try:
        test_email = input("\n   Введите email для теста: ").strip()
        if not test_email:
            print("   ❌ Email не введен, пропускаем тест")
            return False
        
        send_mail(
            'Тестовое письмо - LootLink',
            'Это тестовое письмо для проверки настройки SMTP.\n\nЕсли вы получили это письмо, значит email настроен правильно!',
            settings.DEFAULT_FROM_EMAIL,
            [test_email],
            fail_silently=False
        )
        print(f"   ✅ Email успешно отправлен на {test_email}")
        print(f"   📬 Проверьте почту (и папку Спам)")
        return True
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def test_sms():
    """Тестирует отправку SMS."""
    print("\n📱 Тестирование отправки SMS...")
    print(f"   Включено: {settings.SMS_ENABLED}")
    print(f"   API ключ: {'Настроен' if settings.SMS_RU_API_KEY else 'НЕ НАСТРОЕН'}")
    
    if not settings.SMS_ENABLED:
        print("   ⚠️  SMS отключены (SMS_ENABLED=False)")
        print("   📝 СМС выводятся в консоль сервера\n")
        return False
    
    if not settings.SMS_RU_API_KEY:
        print("   ❌ API ключ SMS.ru не настроен")
        print("   📝 Добавьте SMS_RU_API_KEY в .env файл\n")
        return False
    
    try:
        test_phone = input("\n   Введите телефон для теста (+79991234567): ").strip()
        if not test_phone:
            print("   ❌ Телефон не введен, пропускаем тест")
            return False
        
        result = send_sms(
            test_phone,
            'Тестовое СМС с LootLink. Если вы получили это сообщение, SMS настроены правильно!'
        )
        
        if result:
            print(f"   ✅ СМС отправлено на {test_phone}")
            print(f"   📱 Проверьте телефон")
            return True
        else:
            print(f"   ❌ Не удалось отправить СМС")
            print(f"   💡 Проверьте API ключ и баланс на sms.ru")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ EMAIL И SMS")
    print("=" * 60)
    
    email_ok = test_email()
    sms_ok = test_sms()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    print(f"   Email: {'✅ Работает' if email_ok else '⚠️  Не настроен или ошибка'}")
    print(f"   SMS:   {'✅ Работает' if sms_ok else '⚠️  Не настроен или ошибка'}")
    print("=" * 60)
    
    if not email_ok and not sms_ok:
        print("\n⚠️  Ни email, ни SMS не настроены!")
        print("📖 Смотрите инструкцию: docs/EMAIL_SMS_SETUP.md")
    elif email_ok and not sms_ok:
        print("\n✅ Email работает!")
        print("💡 Для включения SMS смотрите: docs/EMAIL_SMS_SETUP.md")
    elif not email_ok and sms_ok:
        print("\n✅ SMS работают!")
        print("💡 Для включения Email смотрите: docs/EMAIL_SMS_SETUP.md")
    else:
        print("\n🎉 Все работает отлично!")
        print("✅ Коды будут отправляться на email И телефон")
    
    print()


if __name__ == '__main__':
    main()

