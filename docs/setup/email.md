# Настройка Email и SMS

Email и SMS нужны для подтверждения регистрации, сброса пароля, верификации и уведомлений о сделках. В dev письма по умолчанию идут в консоль; для боевого режима настройте SMTP (и опционально SMS) через `.env`.

## Email

Любой SMTP-провайдер настраивается одним блоком в `.env`. Для России лучшая доставляемость у Yandex и Mail.ru.

### Yandex (рекомендуется)

Бесплатно до 500 писем/день. Включите пароль приложения на https://id.yandex.ru/security/app-passwords (нужна 2FA), затем:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=lootlink@yandex.ru
EMAIL_HOST_PASSWORD=пароль-приложения
DEFAULT_FROM_EMAIL=LootLink <lootlink@yandex.ru>
```

### Mail.ru

До 1000 писем/день. Использует SSL на порту 465 (не TLS):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_HOST_USER=lootlink@mail.ru
EMAIL_HOST_PASSWORD=пароль
DEFAULT_FROM_EMAIL=LootLink <lootlink@mail.ru>
```

### Gmail

Требует App Password (Google Account → Security → 2-Step Verification → App Passwords):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=app-password-16-символов
DEFAULT_FROM_EMAIL=LootLink <you@gmail.com>
```

### SendGrid

Профессиональный сервис, 100 писем/день бесплатно. Создайте API-ключ и используйте SMTP-релей:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=ваш-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@lootlink.ru
```

### Лимиты провайдеров

| Провайдер | Бесплатно | Примечание |
|-----------|-----------|------------|
| Yandex | 500/день | для >500 нужна верификация домена |
| Mail.ru | 1000/день | может блокировать за спам |
| Gmail | 500/день | требуется App Password |
| SendGrid | 100/день | требуется верификация |
| AWS SES | — | ~$0.10 за 1000 писем, для масштаба |

## SMS (SMS.ru)

SMS используются для кодов подтверждения телефона. SMS.ru — российский сервис, ~2.1 ₽ за сообщение, простой API.

1. Зарегистрируйтесь на https://sms.ru/registration, подтвердите email.
2. Пополните баланс (от 100 ₽ ≈ 50 SMS).
3. Получите API-ключ: Настройки → API.
4. Добавьте в `.env`:

```env
SMS_ENABLED=True
SMS_RU_API_KEY=ваш-api-ключ
```

Если `SMS_ENABLED=False`, коды не отправляются, а пишутся в лог — удобно для разработки.

Альтернативы: SMSC.ru (~2.5 ₽), SMS Aero (~2 ₽), Twilio (международный, дороже для РФ).

## Применение настроек

После правки `.env` на сервере перезапустите контейнеры, которым нужны новые переменные:

```bash
docker compose restart web celery_worker celery_beat
```

## Тестирование

Email — через Django shell:

```python
from django.core.mail import send_mail
from django.conf import settings
send_mail('Тест', 'Тестовое письмо', settings.DEFAULT_FROM_EMAIL, ['you@example.com'])
```

SMS:

```python
from core.sms_service import send_sms
send_sms('+79991234567', 'Тестовое СМС с LootLink')
```

Боевая проверка: сброс пароля (`/accounts/password-reset/`) и регистрация нового пользователя — должны прийти код и ссылка верификации.

## Troubleshooting

**SMTPAuthenticationError** — проверьте полный email в `EMAIL_HOST_USER` и пароль приложения (не основной пароль); для Gmail/Yandex нужна включённая 2FA.

**Connection refused** — проверьте `EMAIL_HOST`/`EMAIL_PORT`, доступ сервера в интернет и протокол (TLS на 587, SSL на 465). Исходящий порт: `ufw allow out 587/tcp`.

**Письма уходят в спам** — настройте SPF, DKIM и DMARC для домена, отправляйте с адреса на своём домене (`noreply@lootlink.ru`).

**SMTPServerDisconnected** — слишком частая отправка. Шлите письма асинхронно через Celery.

## Production-заметки

- Отправляйте письма асинхронно (в `core/tasks.py` есть `send_email_async`), чтобы не блокировать запрос.
- Коды подтверждения одноразовые, живут 15 минут, старые деактивируются; от перебора защищает `SimpleRateLimitMiddleware`.
- Никогда не коммитьте `.env` — он в `.gitignore`. Храните API-ключи и пароли приложений отдельно.
- Для масштаба (1000+ пользователей) переходите на SendGrid/Mailgun/AWS SES и собственный домен с SPF/DKIM/DMARC.
