#!/bin/bash

# ==========================================
# Enable HTTPS settings in Django
# ==========================================

set -e

echo "🔧 Обновление Django настроек для HTTPS..."
echo ""

ENV_FILE="/opt/lootlink/.env"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Файл .env не найден: $ENV_FILE"
    exit 1
fi

# Backup .env
echo "📦 Создание резервной копии .env..."
sudo cp $ENV_FILE ${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup создан"
echo ""

# Function to update or add setting
update_setting() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" $ENV_FILE; then
        sudo sed -i "s/^${key}=.*/${key}=${value}/" $ENV_FILE
        echo "  ✅ Обновлено: ${key}=${value}"
    else
        echo "${key}=${value}" | sudo tee -a $ENV_FILE > /dev/null
        echo "  ✅ Добавлено: ${key}=${value}"
    fi
}

echo "🔐 Включение HTTPS настроек..."

# Update HTTPS settings
update_setting "SECURE_SSL_REDIRECT" "True"
update_setting "SESSION_COOKIE_SECURE" "True"
update_setting "CSRF_COOKIE_SECURE" "True"

echo ""
echo "✅ Настройки обновлены!"
echo ""
echo "🔄 Перезапуск сервисов..."

# Restart services
sudo systemctl restart lootlink
sudo systemctl reload nginx

echo "✅ Сервисы перезапущены"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Django настроен для работы с HTTPS!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Сайт доступен: https://91.218.245.178"
echo ""

