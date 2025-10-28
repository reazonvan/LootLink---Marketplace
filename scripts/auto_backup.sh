#!/bin/bash
# Автоматический бекап базы данных и медиа файлов LootLink
# Использование: добавить в crontab для ежедневного запуска
# Пример: 0 2 * * * /opt/lootlink/scripts/auto_backup.sh

# Настройки
BACKUP_DIR="/var/backups/lootlink"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="lootlink_db"
DB_USER="lootlink_user"
MEDIA_DIR="/opt/lootlink/media"
RETENTION_DAYS=30  # Хранить бекапы 30 дней

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция вывода с временной меткой
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Создание директории для бекапов
log "Создание директории для бекапов..."
mkdir -p "$BACKUP_DIR"

if [ ! -d "$BACKUP_DIR" ]; then
    error "Не удалось создать директорию $BACKUP_DIR"
    exit 1
fi

# Бекап базы данных PostgreSQL
log "Начало бекапа базы данных..."
DB_BACKUP="$BACKUP_DIR/db_${DATE}.sql"
DB_BACKUP_GZ="${DB_BACKUP}.gz"

sudo -u postgres pg_dump "$DB_NAME" > "$DB_BACKUP" 2>&1

if [ $? -eq 0 ]; then
    # Сжатие бекапа
    gzip "$DB_BACKUP"
    log "База данных успешно сохранена: $DB_BACKUP_GZ"
    
    # Вывод размера бекапа
    BACKUP_SIZE=$(du -h "$DB_BACKUP_GZ" | cut -f1)
    log "Размер бекапа БД: $BACKUP_SIZE"
else
    error "Ошибка при создании бекапа базы данных"
fi

# Бекап медиа файлов (если существуют)
if [ -d "$MEDIA_DIR" ]; then
    log "Начало бекапа медиа файлов..."
    MEDIA_BACKUP="$BACKUP_DIR/media_${DATE}.tar.gz"
    
    tar -czf "$MEDIA_BACKUP" -C "$(dirname $MEDIA_DIR)" "$(basename $MEDIA_DIR)" 2>&1
    
    if [ $? -eq 0 ]; then
        log "Медиа файлы успешно сохранены: $MEDIA_BACKUP"
        
        # Вывод размера бекапа
        MEDIA_SIZE=$(du -h "$MEDIA_BACKUP" | cut -f1)
        log "Размер бекапа медиа: $MEDIA_SIZE"
    else
        error "Ошибка при создании бекапа медиа файлов"
    fi
else
    warning "Директория медиа не найдена: $MEDIA_DIR"
fi

# Удаление старых бекапов
log "Удаление бекапов старше $RETENTION_DAYS дней..."
DELETED_COUNT=$(find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ $DELETED_COUNT -gt 0 ]; then
    log "Удалено старых бекапов: $DELETED_COUNT"
else
    log "Старых бекапов не найдено"
fi

# Статистика по бекапам
TOTAL_BACKUPS=$(ls -1 "$BACKUP_DIR" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

log "Статистика бекапов:"
log "  - Всего файлов: $TOTAL_BACKUPS"
log "  - Общий размер: $TOTAL_SIZE"
log "  - Директория: $BACKUP_DIR"

log "Бекап завершен успешно!"

# Отправка уведомления (опционально)
# Раскомментируйте если настроен mail
# echo "Бекап LootLink завершен: $DATE" | mail -s "LootLink Backup Success" admin@example.com

exit 0

