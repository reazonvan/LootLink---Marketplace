#!/bin/bash
# ==================================================
# Скрипт обновления Django до 5.2.7 LTS на Production
# ==================================================
# Использование: sudo bash scripts/upgrade_django_5.2.sh
# Сервер: 91.218.245.178
# ==================================================

set -e  # Остановка при ошибке

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
info() { echo -e "${BLUE}[ℹ]${NC} $1"; }

echo "=============================================="
echo "   Django 5.2.7 LTS Upgrade"
echo "=============================================="
echo ""

PROJECT_DIR="/opt/lootlink"

if [ ! -d "$PROJECT_DIR" ]; then
    error "Проект не найден: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Шаг 1: Бекап
info "Шаг 1/6: Создание бекапа..."

BACKUP_DIR="/var/backups/lootlink/upgrade_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Бекап БД
log "Бекап базы данных..."
sudo -u postgres pg_dump lootlink_db | gzip > "$BACKUP_DIR/db_backup.sql.gz"

# Бекап кода
log "Бекап кода..."
tar -czf "$BACKUP_DIR/code_backup.tar.gz" --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' .

log "Бекап создан: $BACKUP_DIR"

# Шаг 2: Обновление requirements.txt
info "Шаг 2/6: Обновление requirements.txt..."

if grep -q "Django>=4.2" requirements.txt; then
    sed -i 's/Django>=4.2,<5.0/Django>=5.2,<6.0/' requirements.txt
    log "requirements.txt обновлен"
else
    warning "requirements.txt уже обновлен или имеет другой формат"
fi

# Шаг 3: Активация venv и установка Django 5.2
info "Шаг 3/6: Установка Django 5.2.7 LTS..."

source venv/bin/activate

# Показать текущую версию
CURRENT_VERSION=$(python -c "import django; print(django.get_version())")
info "Текущая версия Django: $CURRENT_VERSION"

# Обновление Django
python -m pip install --upgrade "Django>=5.2,<6.0"

# Проверка новой версии
NEW_VERSION=$(python -c "import django; print(django.get_version())")
log "Django обновлен до версии: $NEW_VERSION"

# Шаг 4: Проверка совместимости
info "Шаг 4/6: Проверка совместимости..."

python manage.py check

if [ $? -eq 0 ]; then
    log "Проверка совместимости пройдена успешно"
else
    error "Обнаружены проблемы совместимости!"
    warning "Откат изменений..."
    
    # Откат
    tar -xzf "$BACKUP_DIR/code_backup.tar.gz"
    python -m pip install --upgrade "Django>=4.2,<5.0"
    
    error "Обновление отменено. Восстановлена предыдущая версия."
    exit 1
fi

# Шаг 5: Применение миграций
info "Шаг 5/6: Применение миграций..."

python manage.py makemigrations

if [ $? -eq 0 ]; then
    log "Миграции созданы"
fi

python manage.py migrate

if [ $? -eq 0 ]; then
    log "Миграции применены успешно"
else
    error "Ошибка при применении миграций!"
    exit 1
fi

# Сборка статики
info "Сборка статических файлов..."
python manage.py collectstatic --noinput
log "Статика собрана"

# Шаг 6: Перезапуск сервисов
info "Шаг 6/6: Перезапуск сервисов..."

# Перезапуск Django
if systemctl is-active --quiet lootlink; then
    systemctl restart lootlink
    sleep 2
    
    if systemctl is-active --quiet lootlink; then
        log "LootLink успешно перезапущен"
    else
        error "LootLink не запустился!"
        journalctl -u lootlink -n 50
        exit 1
    fi
else
    warning "Сервис lootlink не был запущен"
fi

# Перезапуск Nginx
if systemctl is-active --quiet nginx; then
    systemctl restart nginx
    log "Nginx перезапущен"
fi

# Финальные проверки
echo ""
echo "=============================================="
echo "   Обновление завершено!"
echo "=============================================="
echo ""

log "Версия Django: $NEW_VERSION"
log "Бекап сохранен: $BACKUP_DIR"

# Проверка работы сайта
info "Проверяю работу сайта..."
sleep 3

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)

if [ "$HTTP_CODE" = "200" ]; then
    log "Сайт работает! (HTTP $HTTP_CODE)"
else
    warning "Сайт вернул код: HTTP $HTTP_CODE"
    warning "Проверьте логи: sudo journalctl -u lootlink -n 50"
fi

echo ""
info "Проверьте сайт в браузере: http://91.218.245.178"
info "Логи Django: sudo journalctl -u lootlink -f"
info "Логи Nginx: sudo tail -f /var/log/nginx/lootlink-error.log"

echo ""
log "✨ Обновление Django до 5.2.7 LTS завершено успешно! ✨"
echo ""

