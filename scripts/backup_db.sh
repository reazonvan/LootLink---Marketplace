#!/bin/bash
#
# PostgreSQL Database Backup Script for LootLink
# Автоматическое резервное копирование БД с ротацией старых бекапов
#

set -e  # Exit on error

# Конфигурация
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/var/backups/lootlink}"
DB_NAME="${DB_NAME:-lootlink_db}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS=${RETENTION_DAYS:-30}  # Хранить бекапы 30 дней

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LootLink Database Backup ===${NC}"
echo "Timestamp: $TIMESTAMP"
echo "Database: $DB_NAME"
echo "Backup directory: $BACKUP_DIR"

# Создаем директорию для бекапов если её нет
mkdir -p "$BACKUP_DIR"

# Имя файла бекапа
BACKUP_FILE="$BACKUP_DIR/lootlink_backup_$TIMESTAMP.sql"
BACKUP_FILE_GZ="$BACKUP_FILE.gz"

# Создаём бекап
echo -e "${YELLOW}Creating backup...${NC}"
if pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$BACKUP_FILE"; then
    echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
    
    # Сжимаем бекап
    echo -e "${YELLOW}Compressing backup...${NC}"
    if gzip "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Backup compressed: $BACKUP_FILE_GZ${NC}"
        
        # Показываем размер файла
        FILESIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
        echo -e "${GREEN}Backup size: $FILESIZE${NC}"
    else
        echo -e "${RED}✗ Failed to compress backup${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Failed to create backup${NC}"
    exit 1
fi

# Удаляем старые бекапы (старше RETENTION_DAYS дней)
echo -e "${YELLOW}Cleaning old backups (older than $RETENTION_DAYS days)...${NC}"
DELETED_COUNT=$(find "$BACKUP_DIR" -name "lootlink_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Deleted $DELETED_COUNT old backup(s)${NC}"
else
    echo -e "${GREEN}✓ No old backups to delete${NC}"
fi

# Показываем список всех бекапов
echo -e "\n${GREEN}=== All backups ===${NC}"
ls -lh "$BACKUP_DIR"/lootlink_backup_*.sql.gz 2>/dev/null || echo "No backups found"

echo -e "\n${GREEN}=== Backup completed successfully! ===${NC}"

# Опционально: отправить уведомление (раскомментируйте если нужно)
# echo "Backup completed: $BACKUP_FILE_GZ" | mail -s "LootLink Backup Success" admin@lootlink.com

exit 0
