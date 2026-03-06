# 🚀 Deployment Guide для LootLink

Полное руководство по развертыванию LootLink в production.

---

## 📋 Предварительные требования

- **Сервер**: Ubuntu 20.04+ / Debian 11+ / RHEL 8+
- **RAM**: минимум 2GB (рекомендуется 4GB+)
- **CPU**: минимум 2 cores
- **Диск**: минимум 20GB SSD
- **Домен**: с настроенными A/AAAA записями
- **Email**: SMTP сервер для уведомлений

---

## 🐳 Вариант 1: Docker Deployment (Рекомендуется)

### 1. Установка Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Клонирование проекта

```bash
git clone https://github.com/your-username/LootLink.git
cd LootLink
```

### 3. Настройка environment

```bash
# Создайте .env файл
cp env.example.txt .env

# Отредактируйте .env
nano .env
```

**Критичные настройки для production:**

```env
# Django
SECRET_KEY=<сгенерируйте через: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False
ALLOWED_HOSTS=lootlink.ru,www.lootlink.ru

# Database
DB_NAME=lootlink_db
DB_USER=lootlink_user
DB_PASSWORD=<strong-password-here>
DB_HOST=db
DB_PORT=5432

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>

# AWS S3 (опционально)
USE_S3=True
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_STORAGE_BUCKET_NAME=lootlink-media

# Redis
USE_REDIS=True
REDIS_URL=redis://redis:6379/1

# Sentry (опционально)
SENTRY_DSN=https://your-dsn@sentry.io/project
ENVIRONMENT=production
RELEASE_VERSION=1.0.0
```

### 4. Запуск через Docker Compose

```bash
# Сборка и запуск контейнеров
docker-compose up -d

# Применение миграций
docker-compose exec web python manage.py migrate

# Создание суперпользователя
docker-compose exec web python manage.py createsuperuser

# Сбор статики
docker-compose exec web python manage.py collectstatic --noinput
```

### 5. SSL сертификаты (Let's Encrypt)

```bash
# Установите Certbot
sudo apt install certbot python3-certbot-nginx

# Получите сертификат
sudo certbot --nginx -d lootlink.ru -d www.lootlink.ru

# Автоматическое обновление
sudo certbot renew --dry-run
```

### 6. Запуск Nginx

```bash
# Запустите Nginx профиль
docker-compose --profile production up -d nginx
```

---

## 🔧 Вариант 2: Manual Deployment (без Docker)

### 1. Установка зависимостей

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# Установите PostgreSQL
sudo apt install postgresql postgresql-contrib

# Установите Redis
sudo apt install redis-server

# Установите Nginx
sudo apt install nginx
```

### 2. Настройка PostgreSQL

```bash
# Подключитесь к PostgreSQL
sudo -u postgres psql

# Создайте БД и пользователя
CREATE DATABASE lootlink_db;
CREATE USER lootlink_user WITH PASSWORD 'strong_password_here';
ALTER ROLE lootlink_user SET client_encoding TO 'utf8';
ALTER ROLE lootlink_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE lootlink_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE lootlink_db TO lootlink_user;

# Включите русскую морфологию для full-text search
\c lootlink_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;

\q
```

### 3. Настройка проекта

```bash
# Клонируйте проект
cd /opt
sudo git clone https://github.com/your-username/LootLink.git
sudo chown -R $USER:$USER LootLink
cd LootLink

# Создайте venv
python3.11 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements/production.txt

# Настройте .env
cp env.example.txt .env
nano .env
```

### 4. Django setup

```bash
# Применить миграции
python manage.py migrate

# Собрать статику
python manage.py collectstatic --noinput

# Создать суперпользователя
python manage.py createsuperuser
```

### 5. Gunicorn setup

```bash
# Создайте systemd service
sudo nano /etc/systemd/system/lootlink.service
```

```ini
[Unit]
Description=LootLink Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/LootLink
Environment="PATH=/opt/LootLink/venv/bin"
EnvironmentFile=/opt/LootLink/.env
ExecStart=/opt/LootLink/venv/bin/gunicorn \
          --workers 4 \
          --bind unix:/opt/LootLink/lootlink.sock \
          --timeout 60 \
          --access-logfile /opt/LootLink/logs/gunicorn-access.log \
          --error-logfile /opt/LootLink/logs/gunicorn-error.log \
          --log-level info \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Запустите сервис
sudo systemctl start lootlink
sudo systemctl enable lootlink
sudo systemctl status lootlink
```

### 6. Nginx setup

```bash
# Создайте конфиг
sudo nano /etc/nginx/sites-available/lootlink
```

```nginx
upstream lootlink_app {
    server unix:/opt/LootLink/lootlink.sock fail_timeout=0;
}

server {
    listen 80;
    server_name lootlink.ru www.lootlink.ru;
    
    client_max_body_size 5M;
    
    location /static/ {
        alias /opt/LootLink/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /opt/LootLink/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://lootlink_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активируйте конфиг
sudo ln -s /etc/nginx/sites-available/lootlink /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL через Let's Encrypt

```bash
sudo certbot --nginx -d lootlink.ru -d www.lootlink.ru
```

---

## 📊 Мониторинг и обслуживание

### Логи

```bash
# Django логи
tail -f /opt/LootLink/logs/lootlink.log
tail -f /opt/LootLink/logs/errors.log

# Gunicorn логи
tail -f /opt/LootLink/logs/gunicorn-error.log

# Nginx логи
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# PostgreSQL логи
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Backup стратегия

```bash
# Автоматические бекапы через cron
crontab -e

# Добавьте строку (бекап каждый день в 2 ночи)
0 2 * * * /opt/LootLink/scripts/backup_db.sh

# Бекапы хранятся 30 дней
# Расположение: /var/backups/lootlink/
```

### Обновление проекта

Рекомендуемый способ: единый скрипт деплоя + post-deploy smoke.

```bash
cd /opt/LootLink

# Обязателен для автотриггера post-deploy smoke
export GITHUB_DISPATCH_TOKEN="<github_token>"

# Для e2e user-journey (если хотите автоподготовку smoke-аккаунтов)
export SMOKE_SELLER_USERNAME="<seller_username>"
export SMOKE_SELLER_PASSWORD="<seller_password>"
export SMOKE_BUYER_USERNAME="<buyer_username>"
export SMOKE_BUYER_PASSWORD="<buyer_password>"

# Docker mode (по умолчанию)
bash scripts/deploy_with_smoke.sh
```

Ручной путь (если нужно выполнить шаги по отдельности):

```bash
# Остановите сервис
sudo systemctl stop lootlink

# Обновите код
cd /opt/LootLink
git pull origin main

# Активируйте venv
source venv/bin/activate

# Обновите зависимости
pip install -r requirements/production.txt --upgrade

# Примените миграции
python manage.py migrate

# Соберите статику
python manage.py collectstatic --noinput

# Перезапустите сервис
sudo systemctl start lootlink
sudo systemctl restart nginx

# Запустите post-deploy smoke в GitHub Actions
# (нужен GITHUB_DISPATCH_TOKEN в окружении сервера)
bash scripts/trigger_post_deploy_smoke.sh
```

### Health Checks

```bash
# Проверка статуса сервисов
sudo systemctl status lootlink
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Проверка портов
sudo netstat -tlnp | grep -E ':(80|443|8000|5432|6379)'

# Проверка Django
curl -I http://localhost:8000/health/

# Проверка Nginx
curl -I http://lootlink.ru
```

---

## 🔒 Security Checklist

- [ ] `DEBUG=False` в production
- [ ] Сильный `SECRET_KEY` (64+ символов)
- [ ] `ALLOWED_HOSTS` настроен правильно
- [ ] SSL сертификаты установлены
- [ ] Firewall настроен (UFW/iptables)
- [ ] Только необходимые порты открыты (80, 443)
- [ ] SSH доступ только по ключу
- [ ] Регулярные обновления системы
- [ ] Автоматические бекапы настроены
- [ ] Sentry мониторинг активен
- [ ] Fail2ban установлен (защита от брутфорса)

### Настройка Firewall (UFW)

```bash
# Установите UFW
sudo apt install ufw

# Разрешите SSH (ВАЖНО! Сначала SSH!)
sudo ufw allow 22/tcp

# Разрешите HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Активируйте firewall
sudo ufw enable

# Проверьте статус
sudo ufw status
```

### Fail2ban для защиты от брутфорса

```bash
# Установите
sudo apt install fail2ban

# Настройте для Nginx
sudo nano /etc/fail2ban/jail.local
```

```ini
[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

[nginx-badbots]
enabled = true

[nginx-noproxy]
enabled = true
```

```bash
sudo systemctl restart fail2ban
```

---

## 📈 Performance Tuning

### PostgreSQL

```bash
sudo nano /etc/postgresql/15/main/postgresql.conf
```

```ini
# Memory
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 4MB

# Connections
max_connections = 100

# Logging
log_min_duration_statement = 1000  # Log slow queries (>1s)
```

### Gunicorn Workers

Формула: `(2 * CPU_CORES) + 1`

```bash
# Для 2 CPU cores
--workers 5

# Для 4 CPU cores
--workers 9
```

### Redis Memory

```bash
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## 🔄 CI/CD через GitHub Actions

При push в main:
1. ✅ Запускаются тесты
2. ✅ Проверяются линтеры
3. ✅ Сканируется безопасность
4. ✅ Собирается Docker image
5. ✅ Deploy на сервер (опционально)

См. `.github/workflows/django.yml`.

### Post-deploy smoke (production)

Добавлен отдельный workflow: `.github/workflows/post-deploy-smoke.yml`.

Что он делает:
1. Запускает публичные browser smoke проверки (`scripts/playwright_smoke.py`).
2. Запускает авторизованные user-journey сценарии (`scripts/playwright_user_journey.py`):
   создание объявления, старт чата, отправка запроса на покупку.

Перед первым запуском подготовьте QA-данные на сервере:

```bash
python manage.py setup_smoke_data \
  --seller-username "<seller_username>" \
  --seller-email "<seller_email>" \
  --seller-password "<seller_password>" \
  --buyer-username "<buyer_username>" \
  --buyer-email "<buyer_email>" \
  --buyer-password "<buyer_password>"
```

И добавьте в GitHub Secrets:
- `SMOKE_SELLER_USERNAME`
- `SMOKE_SELLER_PASSWORD`
- `SMOKE_BUYER_USERNAME`
- `SMOKE_BUYER_PASSWORD`

Опционально для login smoke:
- `SMOKE_LOGIN_USERNAME`
- `SMOKE_LOGIN_PASSWORD`

Запуск:
1. Через Actions -> `Post-Deploy Smoke` -> `Run workflow`.
2. Или через `repository_dispatch` (`event_type=post_deploy_smoke`) после вашего deploy-скрипта.

Для автоматического триггера после деплоя используйте скрипт:

```bash
# 1) Один раз задайте токен на сервере
export GITHUB_DISPATCH_TOKEN="<github_token>"

# 2) Вызовите триггер (по умолчанию base_url=https://lootlink.ru)
bash scripts/trigger_post_deploy_smoke.sh
```

Полный автодеплой + smoke:

```bash
bash scripts/deploy_with_smoke.sh
```

Опции для `deploy_with_smoke.sh` через переменные окружения:
- `DEPLOY_MODE=docker|systemd`
- `HEALTHCHECK_URL=https://lootlink.ru/health/`
- `RUN_DISPATCH_AFTER_DEPLOY=true|false`
- `STRICT_DISPATCH=true|false`
- `DEPLOY_SKIP_SETUP_SMOKE_DATA=true|false`

Опциональные переменные:
- `SMOKE_BASE_URL` (например `https://staging.lootlink.ru`)
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `DISPATCH_EVENT_TYPE`
- `DEPLOYED_SHA` (если хотите передать свой SHA вручную)

---

## 🆘 Troubleshooting

### 500 Internal Server Error

```bash
# Проверьте логи
tail -f /opt/LootLink/logs/errors.log
tail -f /opt/LootLink/logs/gunicorn-error.log

# Проверьте права на файлы
sudo chown -R www-data:www-data /opt/LootLink

# Перезапустите сервис
sudo systemctl restart lootlink
```

### Static files не загружаются

```bash
# Соберите статику заново
python manage.py collectstatic --clear --noinput

# Проверьте права
sudo chown -R www-data:www-data /opt/LootLink/staticfiles
```

### База данных недоступна

```bash
# Проверьте статус PostgreSQL
sudo systemctl status postgresql

# Проверьте подключение
psql -U lootlink_user -d lootlink_db -h localhost

# Проверьте pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

---

## 📞 Support

Если возникли проблемы при deployment:
- Создайте issue на GitHub
- Напишите на tech@lootlink.ru
- Проверьте документацию в `docs/`

---

**Успешного развертывания! 🚀**
