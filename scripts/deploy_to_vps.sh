#!/bin/bash
# ===========================================
# LootLink VPS Deployment Script
# Автоматическая установка и настройка
# ===========================================

set -e  # Выход при любой ошибке

echo "🚀 Начинаем установку LootLink на VPS..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    log_error "Запустите скрипт с правами root: sudo bash $0"
    exit 1
fi

# 1. Обновление системы
log_info "Обновление системы..."
apt update
apt upgrade -y

# 2. Установка необходимых пакетов
log_info "Установка необходимых пакетов..."
apt install -y python3 python3-venv python3-pip \
    postgresql postgresql-contrib \
    nginx \
    redis-server \
    git \
    ufw \
    fail2ban \
    certbot python3-certbot-nginx \
    unzip

# 3. Настройка PostgreSQL
log_info "Настройка PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE lootlink_db;" 2>/dev/null || log_warning "БД lootlink_db уже существует"
sudo -u postgres psql -c "CREATE USER lootlink_user WITH PASSWORD 'LootLink2025SecurePass!';" 2>/dev/null || log_warning "Пользователь lootlink_user уже существует"
sudo -u postgres psql -c "ALTER ROLE lootlink_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE lootlink_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE lootlink_user SET timezone TO 'Europe/Moscow';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lootlink_db TO lootlink_user;"
sudo -u postgres psql -d lootlink_db -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# 4. Настройка директорий
log_info "Создание директорий..."
mkdir -p /opt/lootlink
mkdir -p /var/log/lootlink
mkdir -p /var/backups/lootlink

# 5. Клонирование или обновление проекта
log_info "Настройка проекта..."
if [ -d "/opt/lootlink/.git" ]; then
    log_info "Проект уже существует, пропускаем клонирование..."
else
    log_info "Скопируйте файлы проекта в /opt/lootlink/"
fi

cd /opt/lootlink

# 6. Создание виртуального окружения
log_info "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# 7. Установка зависимостей Python
log_info "Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. Генерация SECRET_KEY
log_info "Генерация SECRET_KEY..."
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# 9. Создание .env файла
log_info "Создание .env файла..."
cat > .env << EOF
# Django Settings
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=91.218.245.178

# Database Settings
DB_NAME=lootlink_db
DB_USER=lootlink_user
DB_PASSWORD=LootLink2025SecurePass!
DB_HOST=localhost
DB_PORT=5432

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@lootlink.ru

# AWS S3 Settings (отключено)
USE_S3=False

# Redis Settings
USE_REDIS=True
REDIS_URL=redis://localhost:6379/1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Monitoring
ENVIRONMENT=production
RELEASE_VERSION=1.0.0
EOF

# 10. Применение миграций Django
log_info "Применение миграций Django..."
python manage.py migrate

# 11. Сбор статических файлов
log_info "Сбор статических файлов..."
python manage.py collectstatic --noinput

# 12. Создание суперпользователя (интерактивно)
log_warning "Создание суперпользователя (можете пропустить, нажав Ctrl+C)"
python manage.py createsuperuser || log_warning "Суперпользователь не создан"

# 13. Настройка прав доступа
log_info "Настройка прав доступа..."
chown -R www-data:www-data /opt/lootlink
chown -R www-data:www-data /var/log/lootlink
chmod -R 755 /opt/lootlink
chmod 600 /opt/lootlink/.env

# 14. Создание systemd сервиса для Gunicorn
log_info "Создание systemd сервиса..."
cat > /etc/systemd/system/lootlink.service << 'EOF'
[Unit]
Description=LootLink Gunicorn Daemon
After=network.target postgresql.service redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/lootlink
Environment="PATH=/opt/lootlink/venv/bin"
EnvironmentFile=/opt/lootlink/.env
ExecStart=/opt/lootlink/venv/bin/gunicorn \
          --workers 5 \
          --bind unix:/opt/lootlink/lootlink.sock \
          --timeout 60 \
          --access-logfile /var/log/lootlink/gunicorn-access.log \
          --error-logfile /var/log/lootlink/gunicorn-error.log \
          --log-level info \
          config.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 15. Создание systemd сервиса для Celery Worker
log_info "Создание Celery Worker сервиса..."
cat > /etc/systemd/system/lootlink-celery.service << 'EOF'
[Unit]
Description=LootLink Celery Worker
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/lootlink
Environment="PATH=/opt/lootlink/venv/bin"
EnvironmentFile=/opt/lootlink/.env
ExecStart=/opt/lootlink/venv/bin/celery -A config worker \
          --loglevel=info \
          --logfile=/var/log/lootlink/celery-worker.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 16. Создание systemd сервиса для Celery Beat
log_info "Создание Celery Beat сервиса..."
cat > /etc/systemd/system/lootlink-celery-beat.service << 'EOF'
[Unit]
Description=LootLink Celery Beat Scheduler
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/lootlink
Environment="PATH=/opt/lootlink/venv/bin"
EnvironmentFile=/opt/lootlink/.env
ExecStart=/opt/lootlink/venv/bin/celery -A config beat \
          --loglevel=info \
          --logfile=/var/log/lootlink/celery-beat.log \
          --pidfile=/opt/lootlink/celerybeat.pid

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 17. Настройка Nginx
log_info "Настройка Nginx..."
cat > /etc/nginx/sites-available/lootlink << 'EOF'
upstream lootlink_app {
    server unix:/opt/lootlink/lootlink.sock fail_timeout=0;
}

server {
    listen 80;
    server_name 91.218.245.178;
    
    client_max_body_size 5M;
    
    access_log /var/log/nginx/lootlink-access.log;
    error_log /var/log/nginx/lootlink-error.log;
    
    location /static/ {
        alias /opt/lootlink/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /opt/lootlink/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://lootlink_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
EOF

# Активация конфигурации Nginx
ln -sf /etc/nginx/sites-available/lootlink /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации Nginx
nginx -t

# 18. Настройка Firewall (UFW)
log_info "Настройка Firewall..."
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status

# 19. Настройка Fail2ban
log_info "Настройка Fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22

[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

[nginx-badbots]
enabled = true
EOF

systemctl restart fail2ban

# 20. Запуск сервисов
log_info "Запуск сервисов..."
systemctl daemon-reload
systemctl enable lootlink
systemctl enable lootlink-celery
systemctl enable lootlink-celery-beat
systemctl start lootlink
systemctl start lootlink-celery
systemctl start lootlink-celery-beat
systemctl restart nginx

# 21. Проверка статуса
log_info "Проверка статуса сервисов..."
systemctl status lootlink --no-pager
systemctl status nginx --no-pager

# 22. Итоговая информация
echo ""
echo "=============================================="
log_info "✅ Установка завершена успешно!"
echo "=============================================="
echo ""
echo "🌐 Сайт доступен по адресу: http://91.218.245.178"
echo ""
echo "📊 Полезные команды:"
echo "  - Перезапуск сервиса: sudo systemctl restart lootlink"
echo "  - Просмотр логов: sudo journalctl -u lootlink -f"
echo "  - Статус сервисов: sudo systemctl status lootlink"
echo ""
echo "📁 Расположение:"
echo "  - Проект: /opt/lootlink"
echo "  - Логи: /var/log/lootlink/"
echo "  - Nginx конфиг: /etc/nginx/sites-available/lootlink"
echo ""
echo "🔐 Следующие шаги:"
echo "  1. Настройте email в /opt/lootlink/.env"
echo "  2. Добавьте доменное имя в ALLOWED_HOSTS"
echo "  3. Настройте SSL: sudo certbot --nginx"
echo ""
log_warning "⚠️  ВАЖНО: Смените пароль root: passwd"
log_warning "⚠️  ВАЖНО: Настройте бэкапы базы данных"
echo ""

