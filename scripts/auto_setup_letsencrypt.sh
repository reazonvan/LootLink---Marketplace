#!/bin/bash

# ==========================================
# Автоматическая установка Let's Encrypt
# Ожидает DNS и устанавливает сертификат
# ==========================================

set -e

DOMAIN="lootlink.ru"
WWW_DOMAIN="www.lootlink.ru"
EXPECTED_IP="91.218.245.178"
MAX_WAIT=7200  # 2 часа максимум
CHECK_INTERVAL=120  # Проверка каждые 2 минуты

echo "🤖 Автоматическая установка Let's Encrypt для $DOMAIN"
echo "════════════════════════════════════════════════════"
echo ""
echo "📋 Параметры:"
echo "   Домен: $DOMAIN, $WWW_DOMAIN"
echo "   Ожидаемый IP: $EXPECTED_IP"
echo "   Проверка каждые: $CHECK_INTERVAL секунд"
echo "   Максимальное время ожидания: $((MAX_WAIT/60)) минут"
echo ""
echo "⏰ Начато: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Установка необходимых утилит
echo "📦 Проверка утилит..."
if ! command -v dig &> /dev/null; then
    apt-get update -qq
    apt-get install -y dnsutils > /dev/null 2>&1
fi
if ! command -v certbot &> /dev/null; then
    apt-get install -y certbot python3-certbot-nginx > /dev/null 2>&1
fi
echo "✅ Утилиты готовы"
echo ""

# Функция проверки DNS
check_dns() {
    dig @8.8.8.8 +short $DOMAIN | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1
}

# Ожидание DNS
echo "⏳ Ожидание распространения DNS..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

elapsed=0
attempt=1

while [ $elapsed -lt $MAX_WAIT ]; do
    CURRENT_IP=$(check_dns)
    CURRENT_TIME=$(date '+%H:%M:%S')
    
    if [ "$CURRENT_IP" == "$EXPECTED_IP" ]; then
        echo ""
        echo "✅ DNS распространился!"
        echo "   $DOMAIN → $CURRENT_IP"
        echo "   Время: $CURRENT_TIME"
        echo ""
        break
    fi
    
    # Прогресс бар
    progress=$((elapsed * 100 / MAX_WAIT))
    bar_filled=$((progress / 5))
    bar_empty=$((20 - bar_filled))
    
    printf "\r🔄 Попытка #%d | %s | [" "$attempt" "$CURRENT_TIME"
    printf "%${bar_filled}s" | tr ' ' '█'
    printf "%${bar_empty}s" | tr ' ' '░'
    printf "] %d%% | IP: %s" "$progress" "${CURRENT_IP:-не найден}"
    
    if [ $elapsed -ge $MAX_WAIT ]; then
        echo ""
        echo ""
        echo "⚠️  Превышено время ожидания DNS"
        echo "   DNS может распространяться до 24 часов"
        echo "   Попробуйте запустить скрипт позже вручную"
        exit 1
    fi
    
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
    attempt=$((attempt + 1))
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Установка Let's Encrypt
echo "🔐 Установка Let's Encrypt сертификата..."
echo ""

certbot --nginx \
    -d $DOMAIN \
    -d $WWW_DOMAIN \
    --non-interactive \
    --agree-tos \
    --redirect \
    --email admin@$DOMAIN

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Let's Encrypt установлен успешно!"
else
    echo ""
    echo "❌ Ошибка установки Let's Encrypt"
    exit 1
fi

# Обновление Nginx конфигурации
echo ""
echo "⚙️  Обновление конфигурации Nginx..."

# Обновляем server_name в конфиге
if [ -f /etc/nginx/sites-available/lootlink ]; then
    sed -i "s/server_name 91.218.245.178;/server_name $DOMAIN $WWW_DOMAIN;/g" /etc/nginx/sites-available/lootlink
    nginx -t && systemctl reload nginx
    echo "✅ Nginx обновлен"
fi

# Обновление Django настроек
echo ""
echo "⚙️  Обновление Django настроек..."

ENV_FILE="/opt/lootlink/.env"
if [ -f "$ENV_FILE" ]; then
    # Backup
    cp $ENV_FILE ${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)
    
    # Update SITE_URL
    if grep -q "^SITE_URL=" $ENV_FILE; then
        sed -i "s|^SITE_URL=.*|SITE_URL=https://$DOMAIN|" $ENV_FILE
    else
        echo "SITE_URL=https://$DOMAIN" >> $ENV_FILE
    fi
    
    # Update ALLOWED_HOSTS
    HOSTS="localhost,127.0.0.1,91.218.245.178,$DOMAIN,$WWW_DOMAIN"
    if grep -q "^ALLOWED_HOSTS=" $ENV_FILE; then
        sed -i "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$HOSTS/" $ENV_FILE
    else
        echo "ALLOWED_HOSTS=$HOSTS" >> $ENV_FILE
    fi
    
    # Update CSRF_TRUSTED_ORIGINS
    ORIGINS="https://$DOMAIN,https://$WWW_DOMAIN,http://91.218.245.178,https://91.218.245.178"
    if grep -q "^CSRF_TRUSTED_ORIGINS=" $ENV_FILE; then
        sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=$ORIGINS|" $ENV_FILE
    else
        echo "CSRF_TRUSTED_ORIGINS=$ORIGINS" >> $ENV_FILE
    fi
    
    echo "✅ Django настройки обновлены"
fi

# Перезапуск сервисов
echo ""
echo "🔄 Перезапуск сервисов..."
systemctl restart lootlink
systemctl reload nginx

echo "✅ Сервисы перезапущены"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ГОТОВО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Ваш сайт теперь доступен:"
echo "   🌐 https://$DOMAIN"
echo "   🌐 https://$WWW_DOMAIN"
echo ""
echo "✅ SSL сертификат: Let's Encrypt (доверенный)"
echo "✅ Предупреждение безопасности: УДАЛЕНО"
echo "✅ Автообновление: Каждые 90 дней"
echo ""
echo "⏰ Завершено: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

