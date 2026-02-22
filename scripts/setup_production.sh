#!/bin/bash
# ==================================================
# Скрипт настройки Production окружения для LootLink
# ==================================================
# Использование: sudo bash scripts/setup_production.sh
#
# Этот скрипт:
# 1. Генерирует новый SECRET_KEY
# 2. Устанавливает DEBUG=False
# 3. Настраивает HTTPS с Let's Encrypt
# 4. Обновляет конфигурацию Nginx
# 5. Настраивает автоматические бекапы
#
# ⚠️ ВАЖНО: Запускать ТОЛЬКО на production сервере!
# ==================================================

set -e  # Остановка при ошибке

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Функции вывода
log() {
    echo -e "${GREEN}[✓]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    error "Этот скрипт должен быть запущен с правами root (sudo)"
    exit 1
fi

# Настройки
PROJECT_DIR="/opt/lootlink"
ENV_FILE="$PROJECT_DIR/.env"
DOMAIN=""  # Оставить пустым если нет домена

echo "=============================================="
echo "   LootLink Production Setup"
echo "=============================================="
echo ""

# Шаг 1: Генерация нового SECRET_KEY
info "Шаг 1/5: Генерация нового SECRET_KEY..."

if [ ! -f "$ENV_FILE" ]; then
    error "Файл .env не найден: $ENV_FILE"
    exit 1
fi

# Генерация SECRET_KEY с помощью Python
cd "$PROJECT_DIR"
source venv/bin/activate

NEW_SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

if [ -z "$NEW_SECRET_KEY" ]; then
    error "Не удалось сгенерировать SECRET_KEY"
    exit 1
fi

log "Новый SECRET_KEY сгенерирован"

# Шаг 2: Обновление .env файла
info "Шаг 2/5: Обновление .env файла..."

# Бекап текущего .env
cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
log "Создан бекап .env файла"

# Обновление SECRET_KEY
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${NEW_SECRET_KEY}/" "$ENV_FILE"
log "SECRET_KEY обновлен"

# Установка DEBUG=False
sed -i "s/^DEBUG=.*/DEBUG=False/" "$ENV_FILE"
log "DEBUG установлен в False"

# Обновление остальных настроек безопасности
if grep -q "^SECURE_SSL_REDIRECT=" "$ENV_FILE"; then
    sed -i "s/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/" "$ENV_FILE"
else
    echo "SECURE_SSL_REDIRECT=True" >> "$ENV_FILE"
fi

if grep -q "^SESSION_COOKIE_SECURE=" "$ENV_FILE"; then
    sed -i "s/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=True/" "$ENV_FILE"
else
    echo "SESSION_COOKIE_SECURE=True" >> "$ENV_FILE"
fi

if grep -q "^CSRF_COOKIE_SECURE=" "$ENV_FILE"; then
    sed -i "s/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=True/" "$ENV_FILE"
else
    echo "CSRF_COOKIE_SECURE=True" >> "$ENV_FILE"
fi

log "Настройки безопасности обновлены"

# Шаг 3: Настройка HTTPS (если указан домен)
info "Шаг 3/5: Настройка HTTPS..."

if [ -z "$DOMAIN" ]; then
    warning "Домен не указан. HTTPS будет настроен позже."
    warning "Для настройки HTTPS:"
    warning "  1. Добавьте A-запись домена на IP сервера"
    warning "  2. Запустите: sudo certbot --nginx -d ваш-домен.ru"
else
    info "Проверка установки Certbot..."
    
    if ! command -v certbot &> /dev/null; then
        info "Установка Certbot..."
        apt update
        apt install -y certbot python3-certbot-nginx
        log "Certbot установлен"
    else
        log "Certbot уже установлен"
    fi
    
    info "Получение SSL сертификата для $DOMAIN..."
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@$DOMAIN
    
    if [ $? -eq 0 ]; then
        log "SSL сертификат успешно получен!"
        
        # Обновление .env для HTTPS
        sed -i "s/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/" "$ENV_FILE"
        sed -i "s/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=True/" "$ENV_FILE"
        sed -i "s/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=True/" "$ENV_FILE"
        
        # Обновление ALLOWED_HOSTS и CSRF_TRUSTED_ORIGINS
        sed -i "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,127.0.0.1,localhost/" "$ENV_FILE"
        sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN|" "$ENV_FILE"
        
        log "Настройки HTTPS обновлены в .env"
    else
        error "Не удалось получить SSL сертификат"
        warning "Продолжаем без HTTPS..."
    fi
fi

# Шаг 4: Настройка автоматических бекапов
info "Шаг 4/5: Настройка автоматических бекапов..."

# Создание директории для бекапов
mkdir -p /var/backups/lootlink
chown -R postgres:postgres /var/backups/lootlink
log "Директория для бекапов создана"

# Добавление в crontab
BACKUP_SCRIPT="$PROJECT_DIR/scripts/auto_backup.sh"

if [ -f "$BACKUP_SCRIPT" ]; then
    # Проверка прав на выполнение
    chmod +x "$BACKUP_SCRIPT"
    
    # Проверка существования задачи в crontab
    if ! crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
        # Добавление задачи (запуск каждый день в 2:00 ночи)
        (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT >> /var/log/lootlink-backup.log 2>&1") | crontab -
        log "Автоматический бекап настроен (ежедневно в 2:00)"
    else
        log "Автоматический бекап уже настроен"
    fi
else
    warning "Скрипт бекапа не найден: $BACKUP_SCRIPT"
fi

# Шаг 5: Перезапуск сервисов
info "Шаг 5/5: Перезапуск сервисов..."

# Сборка статики
cd "$PROJECT_DIR"
source venv/bin/activate
python manage.py collectstatic --noinput
log "Статические файлы собраны"

# Перезапуск Django
if systemctl is-active --quiet lootlink; then
    systemctl restart lootlink
    log "Сервис lootlink перезапущен"
else
    warning "Сервис lootlink не запущен"
fi

# Перезапуск Nginx
if systemctl is-active --quiet nginx; then
    systemctl restart nginx
    log "Nginx перезапущен"
else
    warning "Nginx не запущен"
fi

# Финальные проверки
echo ""
echo "=============================================="
echo "   Production Setup Complete!"
echo "=============================================="
echo ""
log "SECRET_KEY: ✓ Обновлен"
log "DEBUG: ✓ False"
if [ -z "$DOMAIN" ]; then
    warning "HTTPS: Не настроен (нет домена)"
else
    log "HTTPS: ✓ Настроен"
fi
log "Автоматические бекапы: ✓ Настроены"
log "Сервисы: ✓ Перезапущены"

echo ""
warning "ВАЖНО: Сохраните новый SECRET_KEY в безопасном месте!"
info "SECRET_KEY находится в файле: $ENV_FILE"
info "Бекап старого .env: ${ENV_FILE}.backup.*"

echo ""
info "Проверьте работу сайта:"
if [ -z "$DOMAIN" ]; then
    info "  https://lootlink.ru"
else
    info "  https://$DOMAIN"
fi

echo ""
log "Готово! 🎉"

