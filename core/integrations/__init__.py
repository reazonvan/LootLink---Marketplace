"""
Интеграции с внешними сервисами.

Модули:
- email_service — отправка email через SMTP (Yandex/др.)
- sms_service   — SMS через SMS.ru
- telegram_bot  — нотификации в Telegram
- push_notifications — Web Push (VAPID)

Все эти модули — без БД-моделей. Если нужно добавить интеграцию
(например, S3, Stripe, OAuth), её место — здесь.
"""
