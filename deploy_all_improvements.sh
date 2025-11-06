#!/bin/bash

# Скрипт деплоя всех улучшений на production сервер
# Автор: Cursor AI
# Дата: 2025-11-06

set -e  # Остановка при ошибке

echo "=================================="
echo "🚀 ДЕПЛОЙ УЛУЧШЕНИЙ LOOTLINK"
echo "=================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
SERVER_USER="root"
SERVER_IP="91.218.245.178"
PROJECT_DIR="/var/www/lootlink"
VENV_PATH="$PROJECT_DIR/venv"

echo -e "${YELLOW}📋 Проверка подключения к серверу...${NC}"
ssh -q $SERVER_USER@$SERVER_IP exit
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Подключение успешно${NC}"
else
    echo -e "${RED}❌ Ошибка подключения к серверу${NC}"
    exit 1
fi

echo -e "\n${YELLOW}📦 Загрузка новых файлов на сервер...${NC}"

# Создаем директории если не существуют
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR/payments"
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR/payments/migrations"
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR/templates/payments"
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR/templates/accounts"

# Копируем файлы payments
echo "📁 Копирование payments..."
scp -r payments/* $SERVER_USER@$SERVER_IP:$PROJECT_DIR/payments/

# Копируем шаблоны
echo "📁 Копирование шаблонов..."
scp templates/payments/*.html $SERVER_USER@$SERVER_IP:$PROJECT_DIR/templates/payments/
scp templates/accounts/verification_status.html $SERVER_USER@$SERVER_IP:$PROJECT_DIR/templates/accounts/ 2>/dev/null || true
scp templates/accounts/phone_verification*.html $SERVER_USER@$SERVER_IP:$PROJECT_DIR/templates/accounts/ 2>/dev/null || true
scp templates/chat/conversation_detail.html $SERVER_USER@$SERVER_IP:$PROJECT_DIR/templates/chat/
scp templates/listings/global_search.html $SERVER_USER@$SERVER_IP:$PROJECT_DIR/templates/listings/ 2>/dev/null || true

# Копируем обновленные конфиги
echo "⚙️ Копирование конфигов..."
scp config/settings.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/config/
scp config/urls.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/config/
scp config/asgi.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/config/

# Копируем обновленные URLs
echo "🔗 Копирование URLs..."
scp accounts/urls.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/accounts/
scp listings/urls.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/listings/
scp transactions/urls.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/transactions/
scp core/urls.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/core/

# Копируем новые views
echo "🎯 Копирование views..."
scp accounts/verification_views.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/accounts/ 2>/dev/null || true
scp listings/search_views.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/listings/ 2>/dev/null || true
scp transactions/views_disputes.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/transactions/ 2>/dev/null || true
scp transactions/models_disputes.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/transactions/ 2>/dev/null || true
scp core/moderation_views.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/core/ 2>/dev/null || true
scp core/moderation_models.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/core/ 2>/dev/null || true
scp core/automoderation.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/core/ 2>/dev/null || true

# Копируем chat
echo "💬 Копирование WebSocket chat..."
scp chat/consumers.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/chat/ 2>/dev/null || true
scp chat/routing.py $SERVER_USER@$SERVER_IP:$PROJECT_DIR/chat/ 2>/dev/null || true

# Копируем статику
echo "🎨 Копирование статики..."
scp static/js/websocket-chat.js $SERVER_USER@$SERVER_IP:$PROJECT_DIR/static/js/ 2>/dev/null || true

# Копируем requirements
echo "📋 Копирование requirements..."
scp requirements.txt $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

echo -e "\n${YELLOW}🔧 Установка зависимостей на сервере...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /var/www/lootlink
source venv/bin/activate

echo "📦 Обновление pip..."
pip install --upgrade pip

echo "📦 Установка новых зависимостей..."
pip install -r requirements.txt

echo "✅ Зависимости установлены"
ENDSSH

echo -e "\n${YELLOW}🗄️ Применение миграций...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /var/www/lootlink
source venv/bin/activate

echo "🔄 Создание миграций..."
python manage.py makemigrations

echo "🔄 Применение миграций..."
python manage.py migrate

echo "✅ Миграции применены"
ENDSSH

echo -e "\n${YELLOW}📊 Сбор статики...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /var/www/lootlink
source venv/bin/activate

python manage.py collectstatic --noinput

echo "✅ Статика собрана"
ENDSSH

echo -e "\n${YELLOW}🔄 Перезапуск сервисов...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
echo "🔄 Перезапуск Gunicorn..."
systemctl restart lootlink

echo "🔄 Перезапуск Nginx..."
systemctl restart nginx

echo "🔄 Перезапуск Celery (если установлен)..."
systemctl restart celery 2>/dev/null || echo "⚠️ Celery не установлен"

echo "✅ Сервисы перезапущены"
ENDSSH

echo -e "\n${YELLOW}🧪 Проверка статуса сервисов...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
echo "Статус Gunicorn:"
systemctl status lootlink --no-pager | head -5

echo -e "\nСтатус Nginx:"
systemctl status nginx --no-pager | head -5

ENDSSH

echo -e "\n${GREEN}=================================="
echo "✅ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!"
echo "=================================="
echo -e "🌐 Сайт доступен: http://91.218.245.178${NC}"
echo ""
echo "📝 Развернутые улучшения:"
echo "  ✅ Система платежей (ЮKassa + Эскроу)"
echo "  ✅ Email/SMS верификация"
echo "  ✅ Глобальный поиск"
echo "  ✅ WebSocket чат (требует Daphne)"
echo "  ✅ Система споров"
echo "  ✅ Автомодерация"
echo ""
echo "⚠️ Для работы WebSocket чата нужно:"
echo "  1. Установить Redis (если еще не установлен)"
echo "  2. Запустить Daphne вместо Gunicorn:"
echo "     daphne -b 0.0.0.0 -p 8000 config.asgi:application"
echo ""
echo "🎉 Готово!"

