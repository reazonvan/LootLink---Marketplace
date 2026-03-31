# Настройка почты для production

## Yandex SMTP (рекомендуется для .ru доменов)

### 1. Создайте почтовый ящик

Вариант A — **Яндекс.Почта для домена** (лучший вариант):
- Перейдите на https://connect.yandex.ru
- Добавьте домен `lootlink.ru`
- Создайте ящик `noreply@lootlink.ru`
- Настройте DNS-записи (MX, SPF, DKIM) по инструкции

Вариант B — **Обычный Яндекс аккаунт**:
- Создайте аккаунт на https://mail.yandex.ru
- Создайте пароль приложения: Настройки → Безопасность → Пароли приложений

### 2. Получите пароль приложения

- Яндекс ID → Безопасность → Пароли приложений
- Создайте пароль для "Почта"
- Скопируйте сгенерированный пароль

### 3. Обновите .env на сервере

```bash
ssh root@lootlink.ru
nano /opt/lootlink/.env
```

Замените/добавьте:
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=noreply@lootlink.ru
EMAIL_HOST_PASSWORD=ваш-пароль-приложения
DEFAULT_FROM_EMAIL=noreply@lootlink.ru
```

### 4. Перезапустите контейнеры

```bash
cd /opt/lootlink && docker compose up -d web celery_worker
```

### 5. Проверьте отправку

```bash
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Тест LootLink', 'Почта работает!', None, ['ваш@email.ru'])
print('OK')
"
```

## Альтернативы

### Gmail SMTP
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```
Нужен пароль приложения: Google Account → Security → App passwords

### Mail.ru SMTP
```
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
```

## Лимиты

| Провайдер | Лимит | Примечание |
|-----------|-------|-----------|
| Yandex | 500/сутки | Достаточно для старта |
| Gmail | 500/сутки | Строгие антиспам правила |
| Mail.ru | 1000/сутки | Хорошая альтернатива |

Для масштабирования: Mailgun, SendGrid, или Yandex Cloud Postbox.
