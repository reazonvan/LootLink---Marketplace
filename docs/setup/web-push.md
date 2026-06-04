# Настройка Web Push уведомлений для LootLink

## Требования

```bash
pip install pywebpush==1.14.0
```

## Настройка

### 1. Генерация VAPID ключей

VAPID (Voluntary Application Server Identification) ключи необходимы для идентификации вашего сервера при отправке push уведомлений.

```python
from pywebpush import webpush
import json

# Генерируем ключи
vapid_keys = webpush.generate_vapid_keys()

print("Private Key:", vapid_keys['private_key'])
print("Public Key:", vapid_keys['public_key'])
```

Или используйте онлайн генератор: https://web-push-codelab.glitch.me/

### 2. Добавьте ключи в .env

```env
# Web Push (VAPID keys)
VAPID_PUBLIC_KEY=your_public_key_here
VAPID_PRIVATE_KEY=your_private_key_here
```

### 3. Обновите settings.py

```python
# Web Push Notifications
VAPID_PUBLIC_KEY = config('VAPID_PUBLIC_KEY', default='')
VAPID_PRIVATE_KEY = config('VAPID_PRIVATE_KEY', default='')
```

### 4. Примените миграции

```bash
python manage.py migrate
```

## Использование

### Подключение JavaScript

Добавьте в ваш base.html перед закрывающим тегом `</body>`:

```html
{% if user.is_authenticated %}
<script src="{% static 'js/push-notifications.js' %}"></script>
{% endif %}
```

### Кнопка управления подпиской

Добавьте кнопку в настройки профиля или в любое другое место:

```html
<button id="push-notification-toggle" class="btn btn-primary">
    Включить уведомления
</button>
```

JavaScript автоматически обработает клики и обновит текст кнопки.

### Отправка push уведомлений из кода

```python
from accounts.utils_push import send_push_notification

# Отправка одному пользователю
send_push_notification(
    user=user,
    title="Новое сообщение",
    body="У вас новое сообщение от продавца",
    url="/chat/",
    icon="/static/img/message-icon.png"
)

# Отправка нескольким пользователям
from accounts.utils_push import send_push_to_multiple_users

users = User.objects.filter(is_active=True)
send_push_to_multiple_users(
    users=users,
    title="Важное объявление",
    body="Обновление системы завтра в 3:00",
    url="/announcements/"
)
```

## Интеграция с существующими уведомлениями

### В chat/models.py (сигнал для новых сообщений)

```python
@receiver(post_save, sender=Message)
def send_message_notification(sender, instance, created, **kwargs):
    if created:
        recipient = instance.conversation.get_other_participant(instance.sender)

        # Push уведомление
        if recipient.notification_settings.push_enabled:
            from accounts.utils_push import send_push_notification
            send_push_notification(
                user=recipient,
                title=f"💬 Новое сообщение от {instance.sender.username}",
                body=instance.content[:100],
                url=f"/chat/conversation/{instance.conversation.id}/",
            )
```

### В transactions/views.py (уведомление о сделке)

```python
def accept_purchase_request(request, pk):
    # ... existing code ...

    # Push уведомление покупателю
    if purchase_request.buyer.notification_settings.push_enabled:
        from accounts.utils_push import send_push_notification
        send_push_notification(
            user=purchase_request.buyer,
            title="✅ Ваш запрос принят!",
            body=f'Продавец {purchase_request.seller.username} принял ваш запрос на покупку "{purchase_request.listing.title}".',
            url="/chat/",
        )
```

## Типы уведомлений

Push уведомления могут отправляться для:

1. **Новых сообщений** - когда кто-то пишет в чат
2. **Запросов на покупку** - когда кто-то хочет купить ваш товар
3. **Изменения статуса сделки** - принятие, завершение, отмена
4. **Новых отзывов** - когда кто-то оставляет отзыв о вас
5. **Предложений цены** - когда кто-то предлагает другую цену

## Безопасность

- VAPID ключи хранятся в переменных окружения
- Service Worker работает только по HTTPS (кроме localhost)
- Подписки автоматически деактивируются при ошибке 410 Gone
- Пользователь может отключить уведомления в любой момент

## Требования браузера

Web Push поддерживается в:
- Chrome 42+
- Firefox 44+
- Edge 17+
- Safari 16+ (macOS 13+, iOS 16.4+)
- Opera 37+

## Troubleshooting

### Push уведомления не работают

1. Проверьте что VAPID ключи настроены в .env
2. Убедитесь что сайт работает по HTTPS (или localhost)
3. Проверьте что Service Worker зарегистрирован: откройте DevTools → Application → Service Workers
4. Проверьте разрешения браузера: Settings → Site Settings → Notifications

### Ошибка "Unauthorized"

Неверные VAPID ключи. Проверьте VAPID_PUBLIC_KEY и VAPID_PRIVATE_KEY в .env.

### Подписка не создается

1. Проверьте консоль браузера на ошибки JavaScript
2. Убедитесь что пользователь дал разрешение на уведомления
3. Проверьте что Service Worker успешно зарегистрирован

### Уведомления не приходят

1. Проверьте что подписка активна в базе данных
2. Проверьте логи Django на ошибки при отправке
3. Убедитесь что пользователь не закрыл все вкладки с сайтом (некоторые браузеры требуют хотя бы одну открытую вкладку)

## Тестирование

### Тестовая отправка из Django shell

```python
python manage.py shell

from accounts.models import CustomUser
from accounts.utils_push import send_push_notification

user = CustomUser.objects.get(username='testuser')
send_push_notification(
    user=user,
    title="Тестовое уведомление",
    body="Это тестовое push уведомление",
    url="/",
)
```

### Проверка подписок

```python
from core.models_notifications import PushSubscription

# Все активные подписки
active_subs = PushSubscription.objects.filter(is_active=True)
print(f"Активных подписок: {active_subs.count()}")

# Подписки конкретного пользователя
user_subs = PushSubscription.objects.filter(user__username='testuser')
for sub in user_subs:
    print(f"Подписка: {sub.subscription_info['endpoint'][:50]}...")
```

---

**Готово!** Web Push уведомления настроены и готовы к использованию.
