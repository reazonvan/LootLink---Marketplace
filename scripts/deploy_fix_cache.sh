#!/bin/bash
# Скрипт для срочного исправления проблемы с кэшированием на сервере

set -e  # Остановка при ошибке

echo "🚀 Начало срочного обновления для исправления проблемы с кэшем..."

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Директория проекта
PROJECT_DIR="/opt/lootlink"
VENV_DIR="$PROJECT_DIR/venv"

echo -e "${YELLOW}📂 Переход в директорию проекта...${NC}"
cd $PROJECT_DIR

echo -e "${YELLOW}🔄 Обновление кода из репозитория...${NC}"
git pull origin main

echo -e "${YELLOW}🐍 Активация виртуального окружения...${NC}"
source $VENV_DIR/bin/activate

echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
pip install -r requirements.txt --quiet

echo -e "${YELLOW}🗄️ Применение миграций...${NC}"
python manage.py migrate --noinput

echo -e "${YELLOW}📁 Сбор статических файлов...${NC}"
python manage.py collectstatic --noinput --clear

echo -e "${YELLOW}🧹 КРИТИЧНО: Очистка кэша Django...${NC}"
python scripts/clear_cache.py

echo -e "${YELLOW}🔄 Перезапуск Gunicorn...${NC}"
sudo systemctl restart lootlink

echo -e "${YELLOW}🔄 Перезагрузка Nginx...${NC}"
sudo systemctl reload nginx

echo -e "${GREEN}✅ Обновление завершено успешно!${NC}"
echo ""
echo -e "${GREEN}🔍 Проверка статуса сервисов:${NC}"
sudo systemctl status lootlink --no-pager | head -n 5
sudo systemctl status nginx --no-pager | head -n 5

echo ""
echo -e "${GREEN}✅ Проблема с кэшированием исправлена!${NC}"
echo -e "${GREEN}   Теперь каждый пользователь будет видеть свой профиль.${NC}"

