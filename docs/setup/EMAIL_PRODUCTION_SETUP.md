# НАСТРОЙКА EMAIL ДЛЯ PRODUCTION

## КРИТИЧНО: БЕЗ ЭТОГО САЙТ НЕ БУДЕТ РАБОТАТЬ ПОЛНОЦЕННО!

Email нужен для:
- Сброса пароля
- Верификации email
- Уведомлений о покупках/продажах
- Уведомлений о новых сообщениях

---

## РЕКОМЕНДУЕМЫЕ ПРОВАЙДЕРЫ ДЛЯ РОССИИ

### 1. YANDEX MAIL (РЕКОМЕНДУЕТСЯ)

**Преимущества:**
- Бесплатно до 500 писем/день
- Отличная доставляемость в России
- Простая настройка
- Надежность

**Настройка:**

1. **Создайте Yandex аккаунт:**
   - Перейдите на https://mail.yandex.ru
   - Зарегистрируйтесь (например: lootlink@yandex.ru)

2. **Включите "Пароль приложений":**
   - Перейдите: https://id.yandex.ru/security/app-passwords
   - Создайте пароль для приложения "LootLink"
   - Скопируйте сгенерированный пароль

3. **Обновите .env на сервере:**
```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=lootlink@yandex.ru
EMAIL_HOST_PASSWORD=ваш_пароль_приложения_сюда
DEFAULT_FROM_EMAIL=LootLink <lootlink@yandex.ru>
```

---

### 2. MAIL.RU

**Преимущества:**
- Бесплатно до 1000 писем/день
- Хорошая доставляемость в России

**Настройка:**

1. Регистрация: https://mail.ru
2. Настройте "Внешние приложения"

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=465
EMAIL_USE_SSL=True  # Внимание: SSL, не TLS!
EMAIL_USE_TLS=False
EMAIL_HOST_USER=lootlink@mail.ru
EMAIL_HOST_PASSWORD=ваш_пароль
DEFAULT_FROM_EMAIL=LootLink <lootlink@mail.ru>
```

**ВАЖНО:** Для Mail.ru нужно добавить в settings.py:
```python
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
```

---

### 3. GMAIL (Для международной аудитории)

**Преимущества:**
- Надежность
- Отличная доставляемость
- ВНИМАНИЕ: Требует "App Password"

**Настройка:**

1. **Создайте Gmail аккаунт**

2. **Включите 2FA:**
   - Google Account → Security → 2-Step Verification

3. **Создайте App Password:**
   - Google Account → Security → App Passwords
   - Выберите "Mail" и "Other (Custom name)" → "LootLink"
   - Скопируйте 16-значный пароль

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=ваш_app_password_16_символов
DEFAULT_FROM_EMAIL=LootLink <your_email@gmail.com>
```

---

### 4. SENDGRID (Профессиональное решение)

**Преимущества:**
- 100 писем/день бесплатно
- Продвинутая аналитика
- Высокая доставляемость
- API вместо SMTP

**Настройка:**

1. Регистрация: https://sendgrid.com
2. Получите API ключ
3. Установите: `pip install sendgrid`

```bash
EMAIL_BACKEND=sendgrid_backend.SendgridBackend
SENDGRID_API_KEY=ваш_api_ключ_сюда
DEFAULT_FROM_EMAIL=noreply@lootlink.com
```

**settings.py:**
```python
if config('SENDGRID_API_KEY', default=''):
    EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
    SENDGRID_API_KEY = config('SENDGRID_API_KEY')
```

---

## 🛠️ ПОШАГОВАЯ УСТАНОВКА (YANDEX - РЕКОМЕНДУЕТСЯ)

### Шаг 1: Создайте email на Yandex

```bash
1. Откройте https://mail.yandex.ru
2. Нажмите "Создать аккаунт"
3. Заполните форму (например: lootlink.marketplace@yandex.ru)
4. Подтвердите через SMS
```

### Шаг 2: Настройте пароль приложения

```bash
1. Перейдите https://id.yandex.ru/security
2. Включите двухфакторную аутентификацию (если еще нет)
3. Перейдите в "Пароли приложений"
4. Создайте новый пароль для "LootLink"
5. Скопируйте сгенерированный пароль (он показывается один раз!)
```

### Шаг 3: Обновите .env на сервере

```bash
# SSH на сервер
ssh root@91.218.245.178

# Редактируйте .env
cd /opt/lootlink
nano .env

# Найдите секцию Email Settings и измените:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=lootlink.marketplace@yandex.ru
EMAIL_HOST_PASSWORD=ваш_пароль_приложения_из_шага_2
DEFAULT_FROM_EMAIL=LootLink Marketplace <lootlink.marketplace@yandex.ru>

# Сохраните (Ctrl+O, Enter, Ctrl+X)
```

### Шаг 4: Перезапустите Django

```bash
sudo systemctl restart lootlink
sudo systemctl status lootlink
```

### Шаг 5: Протестируйте отправку

```bash
cd /opt/lootlink
source venv/bin/activate
python manage.py shell

# В shell выполните:
from core.email_service import EmailService
results = EmailService.test_email_configuration()
print(results)

# Если test_passed=True - всё работает!
```

---

## 🧪 ТЕСТИРОВАНИЕ EMAIL

### Тест 1: Отправка через Django shell

```python
python manage.py shell

from django.core.mail import send_mail
from django.conf import settings

# Отправьте тестовое письмо себе
send_mail(
    'Test from LootLink',
    'If you received this, email works!',
    settings.DEFAULT_FROM_EMAIL,
    ['your_email@example.com'],  # Замените на ваш email
    fail_silently=False
)

# Если ошибок нет - проверьте почту!
```

### Тест 2: Сброс пароля

```bash
1. Откройте http://91.218.245.178/accounts/password-reset/
2. Введите email зарегистрированного пользователя
3. Проверьте почту - должен прийти код
4. Введите код на странице подтверждения
```

### Тест 3: Верификация email

```bash
1. Зарегистрируйте нового пользователя
2. Проверьте почту - должна прийти ссылка верификации
3. Кликните по ссылке
4. Аккаунт должен активироваться
```

---

## 🔧 TROUBLESHOOTING

### Проблема: "SMTPAuthenticationError"

**Решение:**
```
1. Проверьте правильность EMAIL_HOST_USER (полный email)
2. Проверьте EMAIL_HOST_PASSWORD (для Gmail - App Password, для Yandex - пароль приложения)
3. Убедитесь что 2FA включена (для Gmail и Yandex)
4. Проверьте что EMAIL_USE_TLS=True
```

### Проблема: "Connection refused"

**Решение:**
```
1. Проверьте EMAIL_HOST и EMAIL_PORT
2. Убедитесь что сервер имеет доступ к интернету
3. Проверьте firewall: sudo ufw allow out 587/tcp
4. Проверьте что используется правильный протокол (TLS vs SSL)
```

### Проблема: Письма уходят в SPAM

**Решение:**
```
1. Настройте SPF record для домена
2. Настройте DKIM подпись
3. Используйте проверенный email домен (@yandex.ru лучше чем @mail.ru)
4. Не используйте слова "тест", "test" в subject
5. Добавьте функцию unsubscribe
```

### Проблема: "SMTPServerDisconnected"

**Решение:**
```
1. Слишком много писем в короткий период
2. Добавьте задержку между отправками
3. Используйте Celery для асинхронной отправки
4. Увеличьте лимит на стороне провайдера
```

---

## 📊 ЛИМИТЫ ПРОВАЙДЕРОВ

| Провайдер | Бесплатный лимит | Ограничения |
|-----------|------------------|-------------|
| Yandex | 500 писем/день | Требуется верификация домена для >500 |
| Mail.ru | 1000 писем/день | Могут блокировать за спам |
| Gmail | 500 писем/день | Требуется App Password |
| SendGrid | 100 писем/день | Требуется верификация |
| Mailgun | 100 писем/день | Требуется кредитная карта |

---

## 🎯 ОБЯЗАТЕЛЬНЫЕ НАСТРОЙКИ ДЛЯ PRODUCTION

### 1. Используйте Celery для отправки

В `core/tasks.py` уже есть:
```python
@shared_task
def send_email_async(subject, message, recipient_email):
    # Асинхронная отправка
```

### 2. Добавьте retry механизм

```python
# В settings.py
EMAIL_MAX_RETRIES = 3
EMAIL_RETRY_DELAY = 60  # секунд
```

### 3. Логируйте все отправки

```python
# Включено в SecurityAuditLog
```

### 4. Создайте email templates

```bash
templates/emails/
  - password_reset.html
  - email_verification.html
  - purchase_notification.html
  - etc.
```

---

## 🚀 БЫСТРЫЙ СТАРТ (5 МИНУТ)

**Для срочного запуска используйте Yandex:**

```bash
# 1. Создайте email: lootlink.marketplace@yandex.ru

# 2. Получите пароль приложения на https://id.yandex.ru/security/app-passwords

# 3. SSH на сервер и обновите .env:
ssh root@91.218.245.178
cd /opt/lootlink
nano .env

# Вставьте:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=lootlink.marketplace@yandex.ru
EMAIL_HOST_PASSWORD=вставьте_сюда_пароль_приложения
DEFAULT_FROM_EMAIL=LootLink <lootlink.marketplace@yandex.ru>

# 4. Перезапустите:
sudo systemctl restart lootlink

# 5. Протестируйте:
cd /opt/lootlink && source venv/bin/activate
python manage.py shell
>>> from core.email_service import EmailService
>>> EmailService.test_email_configuration()
```

**Готово! Теперь email работает!** 🎉

---

## 📞 ПОДДЕРЖКА

Если email всё еще не работает:

1. Проверьте логи: `sudo journalctl -u lootlink -n 100`
2. Проверьте .env файл: `cat /opt/lootlink/.env | grep EMAIL`
3. Проверьте интернет: `ping smtp.yandex.ru`
4. Проверьте firewall: `sudo ufw status`

---

## 💡 СОВЕТЫ ДЛЯ МАСШТАБИРОВАНИЯ

Когда пользователей станет много (1000+):

1. **Используйте профессиональный сервис:**
   - SendGrid (до 40,000 писем/мес бесплатно с верификацией)
   - Mailgun (pay-as-you-go)
   - AWS SES (очень дешево, $0.10 за 1000 писем)

2. **Настройте свой домен:**
   - Купите домен (lootlink.ru)
   - Настройте SPF, DKIM, DMARC
   - Используйте email@lootlink.ru вместо @yandex.ru

3. **Мониторинг:**
   - Отслеживайте bounce rate
   - Анализируйте открытия писем
   - Проверяйте спам-репутацию

---

## АВТОМАТИЧЕСКАЯ НАСТРОЙКА

Я создал скрипт для быстрой настройки:

```bash
# На сервере:
cd /opt/lootlink
chmod +x scripts/setup_email.sh
./scripts/setup_email.sh
```

Скрипт спросит необходимые данные и настроит всё автоматически.

