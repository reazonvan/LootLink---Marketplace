#!/bin/bash
# =====================================================================
# АВТОМАТИЧЕСКАЯ ОЧИСТКА БАЗЫ ДАННЫХ
# Выполняет проверку, затем очистку
# =====================================================================

set -e  # Остановка при ошибке

echo "======================================================================="
echo "  АВТОМАТИЧЕСКАЯ ОЧИСТКА БАЗЫ ДАННЫХ"
echo "======================================================================="
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка что скрипт запущен в правильной директории
if [ ! -f "manage.py" ]; then
    echo -e "${RED}[ERROR] manage.py не найден!${NC}"
    echo "Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Проверка наличия PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${RED}[ERROR] psql не найден!${NC}"
    echo "Установите PostgreSQL client"
    exit 1
fi

# Получаем настройки БД из .env или используем дефолтные
if [ -f ".env" ]; then
    source .env
fi

DB_NAME="${DB_NAME:-lootlink_db}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo -e "${YELLOW}[INFO] Настройки подключения:${NC}"
echo "  База данных: $DB_NAME"
echo "  Пользователь: $DB_USER"
echo "  Хост: $DB_HOST"
echo "  Порт: $DB_PORT"
echo ""

# Шаг 1: Проверка БД
echo "======================================================================="
echo "ШАГ 1: ПРОВЕРКА БАЗЫ ДАННЫХ"
echo "======================================================================="
echo ""

if [ -f "scripts/check_db.sql" ]; then
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f scripts/check_db.sql
else
    echo -e "${RED}[ERROR] scripts/check_db.sql не найден!${NC}"
    exit 1
fi

echo ""
echo "======================================================================="
echo "АНАЛИЗ ЗАВЕРШЕН"
echo "======================================================================="
echo ""

# Спрашиваем подтверждение
echo -e "${YELLOW}[WARNING] ВНИМАНИЕ!${NC}"
echo "Сейчас будут УДАЛЕНЫ все тестовые пользователи и их данные."
echo "Владелец 'reazonvan' и реальные пользователи будут СОХРАНЕНЫ."
echo ""
read -p "Продолжить очистку? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}[CANCELLED] Отменено пользователем${NC}"
    exit 0
fi

echo ""
echo "======================================================================="
echo "ШАГ 2: ОЧИСТКА БАЗЫ ДАННЫХ"
echo "======================================================================="
echo ""

if [ -f "scripts/cleanup_db.sql" ]; then
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f scripts/cleanup_db.sql
else
    echo -e "${RED}[ERROR] scripts/cleanup_db.sql не найден!${NC}"
    exit 1
fi

echo ""
echo "======================================================================="
echo "ШАГ 3: ОЧИСТКА КЕША DJANGO"
echo "======================================================================="
echo ""

if [ -f "manage.py" ]; then
    python manage.py shell << EOF
from django.core.cache import cache
cache.clear()
print('[OK] Кеш Django очищен')
EOF
else
    echo -e "${YELLOW}[WARNING] manage.py не найден, кеш не очищен${NC}"
fi

echo ""
echo "======================================================================="
echo "ШАГ 4: ФИНАЛЬНАЯ ПРОВЕРКА"
echo "======================================================================="
echo ""

# Проверяем результат
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << EOF
SELECT COUNT(*) as users_left FROM accounts_customuser;
SELECT username, email FROM accounts_customuser WHERE LOWER(username) = 'reazonvan';
EOF

echo ""
echo "======================================================================="
echo -e "${GREEN}ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО!${NC}"
echo "======================================================================="
echo ""
echo "Что сделано:"
echo "  [OK] Удалены тестовые пользователи"
echo "  [OK] Удалены их объявления"
echo "  [OK] Удалены их транзакции"
echo "  [OK] Кеш очищен"
echo "  [OK] Владелец reazonvan сохранен"
echo ""
echo "Следующие шаги:"
echo "  1. Обновите .env: DEFAULT_FROM_EMAIL=ivanpetrov20066.ip@gmail.com"
echo "  2. Перезапустите сервис: sudo systemctl restart lootlink"
echo "  3. Проверьте сайт: http://91.218.245.178"
echo ""
echo "======================================================================="

