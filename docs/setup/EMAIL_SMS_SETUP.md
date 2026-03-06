# НАСТРОЙКА EMAIL И SMS

Полное руководство по настройке реальной отправки email и SMS кодов.

---

## НАСТРОЙКА EMAIL

### Вариант 1: Gmail SMTP (Рекомендуется для начала)

#### Шаг 1: Создайте пароль приложения Gmail

1. Перейдите на https://myaccount.google.com/apppasswords
2. Войдите в свой Google аккаунт
3. Выберите "Почта" и "Другое устройство"
4. Введите название: "LootLink"
5. Нажмите "Создать"
6. **Скопируйте 16-значный пароль** (его покажут только один раз!)

#### Шаг 2: Обновите .env файл на сервере

```bash
ssh root@91.218.245.178
nano /opt/lootlink/.env
```

Добавьте/измените:
```env
# Email Settings (Gmail)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=скопированный-пароль-приложения
DEFAULT_FROM_EMAIL=noreply@lootlink.com
```

### Вариант 2: Yandex SMTP

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@yandex.ru
EMAIL_HOST_PASSWORD=ваш-пароль
DEFAULT_FROM_EMAIL=noreply@lootlink.com
```

### Вариант 3: Mail.ru SMTP

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@mail.ru
EMAIL_HOST_PASSWORD=ваш-пароль
DEFAULT_FROM_EMAIL=noreply@lootlink.com
```

### Вариант 4: SendGrid (Профессиональный)

1. Зарегистрируйтесь на https://sendgrid.com (бесплатно до 100 писем/день)
2. Создайте API ключ
3. Установите: `pip install sendgrid`

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=ваш-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@lootlink.com
```

---

## НАСТРОЙКА SMS (SMS.ru)

### Почему SMS.ru?

- Российский сервис
- Низкая цена (~2-3₽ за СМС)
- Простой API
- Быстрая доставка
- Поддержка всех операторов РФ

### Шаг 1: Регистрация на SMS.ru

1. Перейдите на https://sms.ru/registration
2. Зарегистрируйтесь (email + пароль)
3. Подтвердите email
4. Войдите в личный кабинет

### Шаг 2: Пополните баланс

1. В личном кабинете: "Пополнить баланс"
2. Минимум: **100₽** (хватит на ~50 СМС)
3. Для начала: **300₽** (хватит на ~150 СМС)
4. Оплатите любым способом

### Шаг 3: Получите API ключ

1. В личном кабинете: "Настройки" → "API"
2. Скопируйте ваш API ключ
3. Или создайте новый (кнопка "Добавить")

### Шаг 4: Обновите .env на сервере

```bash
ssh root@91.218.245.178
nano /opt/lootlink/.env
```

Добавьте:
```env
# SMS Settings (SMS.ru)
SMS_ENABLED=True
SMS_RU_API_KEY=ваш-api-ключ-из-sms-ru
```

### Цены SMS.ru (ориентировочно):

| Оператор | Цена за СМС |
|----------|-------------|
| МТС | 2.10₽ |
| Билайн | 2.10₽ |
| Мегафон | 2.10₽ |
| Теле2 | 2.10₽ |

**Итого:** ~300₽ = ~140 СМС = ~140 регистраций/сбросов пароля

---

## 🔄 ПРИМЕНЕНИЕ НАСТРОЕК

После изменения .env файла:

```bash
ssh root@91.218.245.178
cd /opt/lootlink
sudo systemctl restart lootlink
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Проверка Email:

```bash
cd /opt/lootlink
source venv/bin/activate
python manage.py shell
```

В shell:
```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'Тест',
    'Это тестовое письмо',
    settings.DEFAULT_FROM_EMAIL,
    ['ваш-email@gmail.com'],
)
```

Если письмо пришло - работает!

### Проверка SMS:

```python
from core.sms_service import send_sms

send_sms('+79991234567', 'Тестовое СМС с LootLink')
```

Если СМС пришло - работает!

---

## МОНИТОРИНГ

### Проверка отправленных писем:

Логи:
```bash
tail -f /opt/lootlink/logs/lootlink.log | grep -i email
```

### Проверка отправленных СМС:

1. Личный кабинет SMS.ru → "Статистика"
2. Логи приложения:
```bash
tail -f /opt/lootlink/logs/lootlink.log | grep -i sms
```

---

## 💰 РАСХОДЫ (примерно)

### Начальная настройка:

| Услуга | Стоимость |
|--------|-----------|
| Gmail SMTP | **БЕСПЛАТНО** (до 500 писем/день) |
| SMS.ru баланс | **300₽** (на старт) |
| **ИТОГО** | **300₽** |

### Ежемесячно (при 100 регистрациях):

| Услуга | Стоимость |
|--------|-----------|
| Email | **БЕСПЛАТНО** |
| SMS (100 шт) | **~210₽** |
| **ИТОГО** | **~210₽/месяц** |

---

## 🔧 АЛЬТЕРНАТИВНЫЕ СЕРВИСЫ

### Для SMS:

1. **SMSC.ru** (https://smsc.ru)
   - Цена: ~2.5₽ за СМС
   - Надежность: высокая
   
2. **SMS Aero** (https://smsaero.ru)
   - Цена: ~2₽ за СМС
   - Бонус: 1₽ при регистрации

3. **Twilio** (https://twilio.com)
   - Международный
   - Дороже для РФ (~5₽)
   - Очень надежный

### Для Email:

1. **SendGrid** - до 100 писем/день бесплатно
2. **Mailgun** - до 5000 писем/месяц бесплатно
3. **Amazon SES** - $0.10 за 1000 писем
4. **Gmail SMTP** - до 500 писем/день бесплатно

---

## БЕЗОПАСНОСТЬ

### Важно:

1. **Никогда не коммитьте .env** в git (уже в .gitignore)
2. **Используйте пароли приложений**, не основной пароль
3. **Храните API ключи в безопасности**
4. **Мониторьте расход** (SMS и email)
5. **Используйте rate limiting** (защита от спама)

### Защита от злоупотреблений:

```python
# Уже реализовано:
- Ограничение на создание кодов (старые деактивируются)
- Коды действуют 15 минут
- Коды одноразовые
- Rate limiting middleware (SimpleRateLimitMiddleware)
```

---

## ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Как это работает сейчас:

1. **При регистрации:**
   - Email: ссылка для подтверждения + код
   - SMS: код подтверждения

2. **При сбросе пароля:**
   - Email: код для сброса
   - SMS: тот же код (дублирование для надежности)

3. **Уведомления:**
   - Email: уведомления о сделках
   - SMS: критические уведомления (опционально)

---

## 🚀 БЫСТРАЯ НАСТРОЙКА (5 минут)

### Для тестирования (бесплатно):

```env
# .env на сервере
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-gmail@gmail.com
EMAIL_HOST_PASSWORD=пароль-приложения
DEFAULT_FROM_EMAIL=noreply@lootlink.com
SMS_ENABLED=False  # СМС отключены (показываются в логах)
```

### Для продакшена (с SMS):

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-gmail@gmail.com
EMAIL_HOST_PASSWORD=пароль-приложения
DEFAULT_FROM_EMAIL=noreply@lootlink.com
SMS_ENABLED=True
SMS_RU_API_KEY=ваш-api-ключ
```

Перезапустите сервер:
```bash
sudo systemctl restart lootlink
```

**Готово!** Теперь коды отправляются реально! 🎉

---

**Документация:** https://sms.ru/api  
**Поддержка SMS.ru:** support@sms.ru  
**Цены:** https://sms.ru/price

