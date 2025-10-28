# 🚀 Руководство по настройке Production для LootLink

## 📋 Текущий статус проекта

**Дата проверки:** 28 октября 2025  
**Общая оценка:** 8.5/10 ⭐⭐⭐⭐⭐

### ✅ Что уже сделано и работает отлично

1. **Архитектура и код** ✓
   - Отличная структура Django проекта
   - Правильное разделение на приложения
   - PostgreSQL Full-Text Search с русской морфологией
   - Celery для асинхронных задач
   - Redis для кеширования

2. **Безопасность** ✓
   - CSRF защита активна
   - Rate limiting middleware
   - XSS защита (auto-escaping)
   - SQL Injection защита (ORM)
   - Валидация изображений через PIL

3. **Функциональность** ✓
   - Email верификация перед созданием объявлений
   - Лимит на количество активных объявлений (50)
   - Система уведомлений
   - Чат с real-time polling
   - Система отзывов и рейтингов

4. **Тестирование** ✓
   - Comprehensive unit тесты для всех моделей
   - Integration тесты для views
   - Coverage ~65%+

5. **Производительность** ✓
   - Кеширование главной страницы (5 минут)
   - Database индексы (24+)
   - select_related / prefetch_related
   - Pagination

6. **Мониторинг** ✓
   - Скрипт автоматических бекапов готов
   - Логирование настроено
   - Sentry integration готов

---

## ⚠️ Что нужно исправить на Production сервере

### 🔴 Критично (сделать НЕМЕДЛЕННО)

#### 1. Обновить SECRET_KEY и DEBUG

**Проблема:** В текущем `.env` на сервере:
```env
DEBUG=True  # ❌ Раскрывает подробности ошибок
SECRET_KEY=django-insecure-dev-key...  # ❌ Слабый ключ
```

**Решение:** Запустить скрипт автоматической настройки:

```bash
# На сервере (91.218.245.178)
cd /opt/lootlink
sudo bash scripts/setup_production.sh
```

Или вручную:

```bash
cd /opt/lootlink
source venv/bin/activate

# Генерация нового SECRET_KEY
NEW_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Обновление .env
nano .env
# Изменить:
# DEBUG=False
# SECRET_KEY=<новый ключ>

# Перезапуск
sudo systemctl restart lootlink nginx
```

#### 2. Настроить HTTPS (Let's Encrypt)

**Проблема:** Сайт работает только по HTTP:
- Пароли передаются в открытом виде
- Нет шифрования данных
- Cross-Origin-Opener-Policy errors

**Решение (автоматически):**

```bash
cd /opt/lootlink
sudo bash scripts/setup_production.sh
```

**Решение (вручную):**

```bash
# Установка Certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Если есть домен:
sudo certbot --nginx -d ваш-домен.ru -d www.ваш-домен.ru

# Если НЕТ домена (работает по IP):
# HTTPS для IP адреса требует self-signed сертификат или платный SSL
# Рекомендуется: купить домен ($1-10/год) и настроить Let's Encrypt
```

После установки HTTPS обновить `.env`:

```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
ALLOWED_HOSTS=localhost,127.0.0.1,91.218.245.178,ваш-домен.ru
CSRF_TRUSTED_ORIGINS=https://ваш-домен.ru,https://www.ваш-домен.ru
```

#### 3. Настроить автоматические бекапы

**Решение:**

```bash
# Создать директорию для бекапов
sudo mkdir -p /var/backups/lootlink
sudo chown postgres:postgres /var/backups/lootlink

# Добавить задачу в crontab
sudo crontab -e

# Добавить строку (бекап каждый день в 2:00 ночи):
0 2 * * * /opt/lootlink/scripts/auto_backup.sh >> /var/log/lootlink-backup.log 2>&1

# Проверить работу скрипта:
sudo /opt/lootlink/scripts/auto_backup.sh
```

---

### 🟡 Важно (сделать в ближайшее время)

#### 4. Настроить Sentry для мониторинга ошибок

```bash
# 1. Зарегистрироваться на sentry.io
# 2. Создать проект Django
# 3. Получить DSN

# 4. Добавить в .env на сервере:
SENTRY_DSN=https://...@sentry.io/...
ENVIRONMENT=production
RELEASE_VERSION=1.0.0

# 5. Перезапустить
sudo systemctl restart lootlink
```

#### 5. Настроить uptime monitoring

Рекомендуемые сервисы (бесплатно):
- UptimeRobot (https://uptimerobot.com) - 50 мониторов бесплатно
- Pingdom
- StatusCake

#### 6. Настроить Email отправку

Обновить `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password
DEFAULT_FROM_EMAIL=noreply@lootlink.com
```

**Важно:** Для Gmail нужно создать App Password:
1. Включить 2FA на аккаунте Google
2. Перейти в Security → App passwords
3. Создать новый App Password для LootLink

---

## 📝 Проверочный чеклист после настройки

После настройки production выполните проверки:

### Безопасность
- [ ] DEBUG=False ✓
- [ ] SECRET_KEY сгенерирован заново ✓
- [ ] HTTPS настроен (если есть домен)
- [ ] SECURE_SSL_REDIRECT=True (если HTTPS)
- [ ] SESSION_COOKIE_SECURE=True (если HTTPS)
- [ ] CSRF_COOKIE_SECURE=True (если HTTPS)
- [ ] Пароли удалены из документации ✓

### Функциональность
- [ ] Сайт открывается
- [ ] Регистрация работает
- [ ] Вход работает
- [ ] Создание объявлений работает
- [ ] Чат работает
- [ ] Email уведомления отправляются
- [ ] Загрузка изображений работает

### Мониторинг
- [ ] Sentry настроен
- [ ] Uptime monitoring настроен
- [ ] Автоматические бекапы работают
- [ ] Логи пишутся

### Производительность
- [ ] Static файлы отдаются корректно
- [ ] Время загрузки < 2 секунд
- [ ] Redis работает
- [ ] Celery работает

---

## 🛠️ Полезные команды для управления

### Управление сервисами

```bash
# Статус
sudo systemctl status lootlink nginx postgresql redis

# Перезапуск Django
sudo systemctl restart lootlink

# Перезапуск Nginx
sudo systemctl restart nginx

# Просмотр логов Django
sudo journalctl -u lootlink -f

# Просмотр логов Nginx
sudo tail -f /var/log/nginx/lootlink-error.log
```

### Работа с Django

```bash
cd /opt/lootlink
source venv/bin/activate

# Создание суперпользователя
python manage.py createsuperuser

# Миграции
python manage.py migrate

# Сбор статики
python manage.py collectstatic --noinput

# Django shell
python manage.py shell
```

### Бекапы и восстановление

```bash
# Ручной бекап
sudo -u postgres pg_dump lootlink_db | gzip > /tmp/backup_$(date +%Y%m%d).sql.gz

# Восстановление
gunzip -c backup_20251028.sql.gz | sudo -u postgres psql lootlink_db

# Бекап медиа
tar -czf /tmp/media_backup.tar.gz /opt/lootlink/media/
```

### Мониторинг ресурсов

```bash
# CPU и память
htop

# Диск
df -h

# Размер БД
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('lootlink_db'));"

# Количество пользователей
sudo -u postgres psql lootlink_db -c "SELECT COUNT(*) FROM accounts_customuser;"
```

---

## 🚨 Что делать при проблемах

### Сайт не открывается

```bash
# 1. Проверить статус
sudo systemctl status lootlink nginx

# 2. Проверить логи
sudo journalctl -u lootlink -n 50
sudo tail -f /var/log/nginx/lootlink-error.log

# 3. Проверить порты
sudo netstat -tlnp | grep -E ':(80|443|8000)'

# 4. Перезапустить
sudo systemctl restart lootlink nginx
```

### 500 Internal Server Error

```bash
# Проверить логи Django
sudo tail -f /opt/lootlink/logs/errors.log

# Проверить права
sudo chown -R www-data:www-data /opt/lootlink

# Проверить .env файл
cat /opt/lootlink/.env | grep -E "(DEBUG|SECRET_KEY|DB_)"
```

### База данных недоступна

```bash
# Проверить PostgreSQL
sudo systemctl status postgresql

# Подключиться к БД
sudo -u postgres psql lootlink_db

# Проверить пароль в .env
cat /opt/lootlink/.env | grep DB_PASSWORD
```

---

## 📊 Мониторинг метрик

Рекомендуемые метрики для отслеживания:

1. **Uptime** - доступность сайта (99.9%+)
2. **Response Time** - время ответа (< 200ms)
3. **Error Rate** - количество ошибок (< 1%)
4. **Database Size** - размер БД
5. **Active Users** - активные пользователи
6. **Listings Created** - созданные объявления за день

---

## 🎯 Рекомендации по масштабированию

Когда проект вырастет:

### 1. Horizontal Scaling (больше серверов)
```yaml
# docker-compose.yml
web:
  deploy:
    replicas: 4  # 4 инстанса Django
```

### 2. Database Optimization
- Master-Slave replication PostgreSQL
- Read replicas для чтения
- Pgpool для балансировки

### 3. Caching Strategy
- Redis Cluster для high availability
- Memcached для кеширования запросов
- CDN для static файлов (Cloudflare, AWS CloudFront)

### 4. Async Processing
- Celery workers для тяжелых задач
- RabbitMQ вместо Redis для очередей
- WebSocket (Django Channels) для real-time

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверить логи (команды выше)
2. Проверить статус сервисов
3. Проверить конфигурацию `.env`
4. Перезапустить сервисы
5. Проверить firewall (порты 80, 443, 8000)

**Email:** ivanpetrov20066.ip@gmail.com

---

**Последнее обновление:** 28 октября 2025  
**Версия:** 1.0.0

