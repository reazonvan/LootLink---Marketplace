#!/bin/bash
#
# PostgreSQL Database Restore Script for LootLink
# Восстановление БД из бекапа
#

set -e  # Exit on error

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Конфигурация
DB_NAME="${DB_NAME:-lootlink_db}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/lootlink}"

echo -e "${GREEN}=== LootLink Database Restore ===${NC}"

# Проверяем аргумент (файл бекапа)
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <backup_file>${NC}"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/lootlink_backup_*.sql.gz 2>/dev/null || echo "No backups found in $BACKUP_DIR"
    exit 1
fi

BACKUP_FILE="$1"

# Проверяем существование файла
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}✗ Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME"
echo ""

# Предупреждение
echo -e "${RED}⚠️  WARNING: This will DESTROY all data in database '$DB_NAME'${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Если файл сжат, распаковываем во временный файл
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}Decompressing backup...${NC}"
    TEMP_FILE="/tmp/lootlink_restore_$$.sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    RESTORE_FILE="$TEMP_FILE"
    echo -e "${GREEN}✓ Backup decompressed${NC}"
else
    RESTORE_FILE="$BACKUP_FILE"
fi

# Удаляем существующую БД и создаём новую
echo -e "${YELLOW}Dropping existing database...${NC}"
dropdb -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" 2>/dev/null || echo "Database doesn't exist"

echo -e "${YELLOW}Creating new database...${NC}"
createdb -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME"
echo -e "${GREEN}✓ New database created${NC}"

# Восстанавливаем данные
echo -e "${YELLOW}Restoring data...${NC}"
if psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" < "$RESTORE_FILE"; then
    echo -e "${GREEN}✓ Data restored successfully${NC}"
else
    echo -e "${RED}✗ Failed to restore data${NC}"
    
    # Удаляем временный файл
    if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
        rm "$TEMP_FILE"
    fi
    
    exit 1
fi

# Удаляем временный файл
if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
    rm "$TEMP_FILE"
    echo -e "${GREEN}✓ Temporary file cleaned${NC}"
fi

echo ""
echo -e "${GREEN}=== Restore completed successfully! ===${NC}"
echo ""
echo "Next steps:"
echo "1. Run migrations: python manage.py migrate"
echo "2. Collect static files: python manage.py collectstatic --noinput"
echo "3. Restart application server"

exit 0
