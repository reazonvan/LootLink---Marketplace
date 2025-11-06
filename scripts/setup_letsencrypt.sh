#!/bin/bash

# ==========================================
# Setup Let's Encrypt Certificate
# ==========================================

set -e

echo "🔐 Установка Let's Encrypt сертификата для LootLink..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if domain is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Ошибка: Не указан домен${NC}"
    echo ""
    echo "Использование:"
    echo "  ./setup_letsencrypt.sh yourdomain.com"
    echo ""
    echo "Примеры:"
    echo "  ./setup_letsencrypt.sh lootlink.ru"
    echo "  ./setup_letsencrypt.sh lootlink.com www.lootlink.com"
    exit 1
fi

DOMAIN=$1
WWW_DOMAIN=$2

echo -e "${YELLOW}📋 Параметры:${NC}"
echo "   Основной домен: $DOMAIN"
if [ ! -z "$WWW_DOMAIN" ]; then
    echo "   Дополнительный: $WWW_DOMAIN"
fi
echo ""

# Step 1: Check DNS
echo -e "${YELLOW}Step 1:${NC} Проверка DNS..."
IP=$(dig +short $DOMAIN | tail -n1)
if [ -z "$IP" ]; then
    echo -e "${RED}❌ DNS не настроен для $DOMAIN${NC}"
    echo "   Настройте A-запись в панели управления доменом:"
    echo "   Тип: A, Имя: @, Значение: YOUR_SERVER_IP"
    exit 1
fi
echo -e "${GREEN}✅ DNS настроен: $DOMAIN → $IP${NC}"
echo ""

# Step 2: Install Certbot
echo -e "${YELLOW}Step 2:${NC} Установка Certbot..."
if ! command -v certbot &> /dev/null; then
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✅ Certbot установлен${NC}"
else
    echo -e "${GREEN}✅ Certbot уже установлен${NC}"
fi
echo ""

# Step 3: Stop nginx temporarily (optional, certbot can handle it)
echo -e "${YELLOW}Step 3:${NC} Подготовка Nginx..."
sudo systemctl reload nginx
echo -e "${GREEN}✅ Nginx готов${NC}"
echo ""

# Step 4: Get certificate
echo -e "${YELLOW}Step 4:${NC} Получение SSL сертификата от Let's Encrypt..."
echo "   (Это может занять минуту)"
echo ""

if [ ! -z "$WWW_DOMAIN" ]; then
    # With www subdomain
    sudo certbot --nginx \
        -d $DOMAIN \
        -d $WWW_DOMAIN \
        --non-interactive \
        --agree-tos \
        --redirect \
        --email admin@$DOMAIN
else
    # Without www subdomain
    sudo certbot --nginx \
        -d $DOMAIN \
        --non-interactive \
        --agree-tos \
        --redirect \
        --email admin@$DOMAIN
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Сертификат успешно получен!${NC}"
else
    echo ""
    echo -e "${RED}❌ Ошибка при получении сертификата${NC}"
    echo "   Проверьте:"
    echo "   1. DNS настроен правильно"
    echo "   2. Порты 80 и 443 открыты"
    echo "   3. Nginx работает"
    exit 1
fi
echo ""

# Step 5: Update Nginx config for domain
echo -e "${YELLOW}Step 5:${NC} Обновление конфигурации Nginx..."

# Backup old config
sudo cp /etc/nginx/sites-available/lootlink /etc/nginx/sites-available/lootlink.backup

# Update server_name in config
sudo sed -i "s/server_name 91.218.245.178;/server_name $DOMAIN;/g" /etc/nginx/sites-available/lootlink

if [ ! -z "$WWW_DOMAIN" ]; then
    sudo sed -i "s/server_name $DOMAIN;/server_name $DOMAIN $WWW_DOMAIN;/g" /etc/nginx/sites-available/lootlink
fi

sudo nginx -t && sudo systemctl reload nginx
echo -e "${GREEN}✅ Конфигурация обновлена${NC}"
echo ""

# Step 6: Setup auto-renewal
echo -e "${YELLOW}Step 6:${NC} Настройка автоматического обновления..."

# Test renewal
sudo certbot renew --dry-run

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Автообновление настроено (каждые 90 дней)${NC}"
else
    echo -e "${YELLOW}⚠️  Автообновление может не работать${NC}"
fi
echo ""

# Step 7: Update Django settings
echo -e "${YELLOW}Step 7:${NC} Обновление Django настроек..."

ENV_FILE="/opt/lootlink/.env"
if [ -f "$ENV_FILE" ]; then
    # Update SITE_URL
    if grep -q "^SITE_URL=" $ENV_FILE; then
        sudo sed -i "s|^SITE_URL=.*|SITE_URL=https://$DOMAIN|" $ENV_FILE
    else
        echo "SITE_URL=https://$DOMAIN" | sudo tee -a $ENV_FILE > /dev/null
    fi
    
    # Update ALLOWED_HOSTS
    if grep -q "^ALLOWED_HOSTS=" $ENV_FILE; then
        HOSTS="localhost,127.0.0.1,91.218.245.178,$DOMAIN"
        if [ ! -z "$WWW_DOMAIN" ]; then
            HOSTS="$HOSTS,$WWW_DOMAIN"
        fi
        sudo sed -i "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$HOSTS/" $ENV_FILE
    fi
    
    # Update CSRF_TRUSTED_ORIGINS
    if grep -q "^CSRF_TRUSTED_ORIGINS=" $ENV_FILE; then
        ORIGINS="https://$DOMAIN"
        if [ ! -z "$WWW_DOMAIN" ]; then
            ORIGINS="$ORIGINS,https://$WWW_DOMAIN"
        fi
        sudo sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=$ORIGINS|" $ENV_FILE
    fi
    
    echo -e "${GREEN}✅ Django настройки обновлены${NC}"
else
    echo -e "${YELLOW}⚠️  Файл .env не найден${NC}"
fi
echo ""

# Step 8: Restart services
echo -e "${YELLOW}Step 8:${NC} Перезапуск сервисов..."
sudo systemctl restart lootlink
sudo systemctl reload nginx
echo -e "${GREEN}✅ Сервисы перезапущены${NC}"
echo ""

# Final message
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Let's Encrypt успешно настроен!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}🎉 Поздравляем!${NC}"
echo ""
echo "   Ваш сайт теперь доступен по адресу:"
echo -e "   ${GREEN}https://$DOMAIN${NC}"
if [ ! -z "$WWW_DOMAIN" ]; then
    echo -e "   ${GREEN}https://$WWW_DOMAIN${NC}"
fi
echo ""
echo -e "${YELLOW}✅ Преимущества Let's Encrypt:${NC}"
echo "   • Доверенный сертификат (без предупреждений)"
echo "   • Автоматическое обновление каждые 90 дней"
echo "   • Бесплатно навсегда"
echo "   • Поддержка HTTP/2"
echo ""
echo -e "${YELLOW}📝 Важная информация:${NC}"
echo "   • Срок действия: 90 дней"
echo "   • Автообновление: настроено в cron"
echo "   • Проверка обновления: sudo certbot renew --dry-run"
echo ""
echo -e "${YELLOW}🔄 Следующее обновление:${NC}"
sudo certbot certificates | grep "Expiry Date" | head -1
echo ""
echo -e "${GREEN}Готово!${NC} 🎉"

