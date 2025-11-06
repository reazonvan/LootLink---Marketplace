#!/bin/bash

# Ожидание распространения DNS
DOMAIN=$1
EXPECTED_IP=$2
MAX_WAIT=1800  # 30 минут максимум
INTERVAL=30     # Проверка каждые 30 секунд

echo "⏳ Ожидание распространения DNS для $DOMAIN..."
echo "   Ожидаемый IP: $EXPECTED_IP"
echo ""

# Установка dig если нет
if ! command -v dig &> /dev/null; then
    echo "📦 Установка dnsutils..."
    apt-get update -qq
    apt-get install -y dnsutils > /dev/null 2>&1
    echo "✅ dnsutils установлен"
    echo ""
fi

elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    # Проверка DNS через Google DNS
    CURRENT_IP=$(dig @8.8.8.8 +short $DOMAIN | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1)
    
    if [ "$CURRENT_IP" == "$EXPECTED_IP" ]; then
        echo "✅ DNS распространился!"
        echo "   $DOMAIN → $CURRENT_IP"
        exit 0
    fi
    
    echo "⏳ DNS еще не обновился (текущий: $CURRENT_IP, нужен: $EXPECTED_IP)"
    echo "   Подождите еще $INTERVAL секунд... (прошло: ${elapsed}s)"
    
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

echo "⚠️  Превышено время ожидания"
echo "   DNS может распространяться до 24 часов"
exit 1

