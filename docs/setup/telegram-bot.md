# Настройка Telegram бота для LootLink

## Требования

```bash
pip install python-telegram-bot==20.7
```

## Настройка

### 1. Создайте бота в Telegram

1. Найдите [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### 2. Добавьте токен в .env

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 3. Обновите settings.py

```python
# Telegram Bot
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
```

## Запуск бота

### Локально (для разработки)

```bash
python manage.py run_telegram_bot
```

### Production (systemd service)

Создайте файл `/etc/systemd/system/lootlink-telegram-bot.service`:

```ini
[Unit]
Description=LootLink Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/LootLink---Marketplace
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python manage.py run_telegram_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lootlink-telegram-bot
sudo systemctl start lootlink-telegram-bot
sudo systemctl status lootlink-telegram-bot
```

## Использование

### Команды бота

- `/start` - Начать работу с ботом
- `/link` - Получить инструкции по привязке аккаунта
- `/unlink` - Отвязать аккаунт
- `/notifications` - Управление уведомлениями
- `/help` - Справка

### Привязка аккаунта

1. Пользователь отправляет `/link` боту
2. Бот показывает Telegram ID пользователя
3. Пользователь вводит этот ID в настройках профиля на сайте
4. После сохранения уведомления начинают приходить

### Отправка уведомлений из кода

```python
from core.telegram_bot import send_notification_sync

# В Django view или Celery task
if user.profile.telegram_notifications and user.profile.telegram_chat_id:
    send_notification_sync(
        chat_id=user.profile.telegram_chat_id,
        message="<b>Новое сообщение!</b>\n\nУ вас новое сообщение в чате."
    )
```

## Интеграция с существующими уведомлениями

### В chat/models.py (сигнал для новых сообщений)

```python
@receiver(post_save, sender=Message)
def send_message_notification(sender, instance, created, **kwargs):
    if created:
        recipient = instance.conversation.get_other_participant(instance.sender)

        # Telegram уведомление
        if recipient.profile.telegram_notifications and recipient.profile.telegram_chat_id:
            from core.telegram_bot import send_notification_sync
            message = f"""
<b>💬 Новое сообщение от {instance.sender.username}</b>

{instance.content[:100]}...

<a href="{settings.SITE_URL}/chat/conversation/{instance.conversation.id}/">Открыть чат</a>
            """
            send_notification_sync(recipient.profile.telegram_chat_id, message)
```

### В transactions/views.py (уведомление о сделке)

```python
def accept_purchase_request(request, pk):
    # ... existing code ...

    # Telegram уведомление покупателю
    if purchase_request.buyer.profile.telegram_notifications:
        from core.telegram_bot import send_notification_sync
        message = f"""
<b>✅ Ваш запрос принят!</b>

Продавец {purchase_request.seller.username} принял ваш запрос на покупку "{purchase_request.listing.title}".

<a href="{settings.SITE_URL}/chat/">Перейти в чат</a>
        """
        send_notification_sync(
            purchase_request.buyer.profile.telegram_chat_id,
            message
        )
```

## Типы уведомлений

Бот может отправлять уведомления о:

1. **Новых сообщениях** - когда кто-то пишет в чат
2. **Запросах на покупку** - когда кто-то хочет купить ваш товар
3. **Изменении статуса сделки** - принятие, завершение, отмена
4. **Новых отзывах** - когда кто-то оставляет отзыв о вас

## Безопасность

- Токен бота хранится в переменных окружения
- Telegram ID проверяется при привязке аккаунта
- Пользователь может отключить уведомления в любой момент
- Бот не имеет доступа к паролям и личным данным

## Мониторинг

Проверка статуса бота:

```bash
sudo systemctl status lootlink-telegram-bot
sudo journalctl -u lootlink-telegram-bot -f
```

## Troubleshooting

### Бот не отвечает

1. Проверьте токен в .env
2. Убедитесь что бот запущен: `systemctl status lootlink-telegram-bot`
3. Проверьте логи: `journalctl -u lootlink-telegram-bot -n 50`

### Уведомления не приходят

1. Проверьте что `telegram_notifications = True` в профиле
2. Проверьте что `telegram_chat_id` заполнен
3. Убедитесь что пользователь не заблокировал бота

### Ошибка "Unauthorized"

Неверный токен бота. Проверьте TELEGRAM_BOT_TOKEN в .env.

## Дополнительные возможности

### Inline кнопки

Бот поддерживает inline кнопки для быстрых действий:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [InlineKeyboardButton("Открыть чат", url=f"{settings.SITE_URL}/chat/")],
    [InlineKeyboardButton("Мои объявления", url=f"{settings.SITE_URL}/accounts/my-listings/")]
]
reply_markup = InlineKeyboardMarkup(keyboard)
```

### Rich форматирование

Бот поддерживает HTML форматирование:

```python
message = """
<b>Жирный текст</b>
<i>Курсив</i>
<code>Код</code>
<a href="url">Ссылка</a>
"""
```

---

**Готово!** Telegram бот настроен и готов к использованию.
