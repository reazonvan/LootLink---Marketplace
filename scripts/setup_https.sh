#!/bin/bash

# ==========================================
# Setup HTTPS with Self-Signed Certificate
# ==========================================

set -e  # Exit on error

echo "🔐 Настройка HTTPS для LootLink..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Variables
SERVER_IP="91.218.245.178"
CERT_DIR="/etc/nginx/ssl"
CERT_DAYS=365
NGINX_CONF_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"

echo -e "${YELLOW}📋 Параметры:${NC}"
echo "   IP адрес: $SERVER_IP"
echo "   Срок сертификата: $CERT_DAYS дней"
echo "   Директория сертификатов: $CERT_DIR"
echo ""

# 1. Создание директории для сертификатов
echo -e "${YELLOW}Step 1:${NC} Создание директории для SSL сертификатов..."
sudo mkdir -p $CERT_DIR
echo -e "${GREEN}✅ Директория создана${NC}"
echo ""

# 2. Генерация самоподписанного сертификата
echo -e "${YELLOW}Step 2:${NC} Генерация самоподписанного SSL сертификата..."
echo "   (Это займет несколько секунд)"

sudo openssl req -x509 -nodes -days $CERT_DAYS \
    -newkey rsa:2048 \
    -keyout $CERT_DIR/lootlink.key \
    -out $CERT_DIR/lootlink.crt \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=LootLink/CN=$SERVER_IP" \
    -addext "subjectAltName=IP:$SERVER_IP" 2>/dev/null

echo -e "${GREEN}✅ Сертификат создан${NC}"
echo "   Приватный ключ: $CERT_DIR/lootlink.key"
echo "   Сертификат: $CERT_DIR/lootlink.crt"
echo ""

# 3. Установка правильных прав
echo -e "${YELLOW}Step 3:${NC} Установка прав доступа..."
sudo chmod 600 $CERT_DIR/lootlink.key
sudo chmod 644 $CERT_DIR/lootlink.crt
echo -e "${GREEN}✅ Права установлены${NC}"
echo ""

# 4. Создание конфигурации Nginx
echo -e "${YELLOW}Step 4:${NC} Создание конфигурации Nginx..."

sudo tee $NGINX_CONF_DIR/lootlink > /dev/null <<'EOF'
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name 91.218.245.178;
    
    # Redirect all HTTP traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name 91.218.245.178;
    
    # SSL Certificates
    ssl_certificate /etc/nginx/ssl/lootlink.crt;
    ssl_certificate_key /etc/nginx/ssl/lootlink.key;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Client body size
    client_max_body_size 5M;
    
    # Root directory
    root /opt/lootlink;
    
    # Static files
    location /static/ {
        alias /opt/lootlink/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/lootlink/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # WebSocket для чата
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    # Favicon
    location = /favicon.ico {
        alias /opt/lootlink/static/favicon.svg;
        log_not_found off;
        access_log off;
    }
    
    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

echo -e "${GREEN}✅ Конфигурация создана${NC}"
echo ""

# 5. Активация конфигурации
echo -e "${YELLOW}Step 5:${NC} Активация конфигурации..."
sudo rm -f $NGINX_ENABLED_DIR/lootlink
sudo ln -s $NGINX_CONF_DIR/lootlink $NGINX_ENABLED_DIR/lootlink
echo -e "${GREEN}✅ Конфигурация активирована${NC}"
echo ""

# 6. Проверка конфигурации Nginx
echo -e "${YELLOW}Step 6:${NC} Проверка конфигурации Nginx..."
if sudo nginx -t; then
    echo -e "${GREEN}✅ Конфигурация корректна${NC}"
else
    echo -e "${RED}❌ Ошибка в конфигурации Nginx${NC}"
    exit 1
fi
echo ""

# 7. Перезагрузка Nginx
echo -e "${YELLOW}Step 7:${NC} Перезагрузка Nginx..."
sudo systemctl reload nginx
echo -e "${GREEN}✅ Nginx перезагружен${NC}"
echo ""

# 8. Проверка статуса
echo -e "${YELLOW}Step 8:${NC} Проверка статуса Nginx..."
if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx работает${NC}"
else
    echo -e "${RED}❌ Nginx не запущен${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ HTTPS успешно настроен!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📝 Важная информация:${NC}"
echo ""
echo "1. Сайт теперь доступен по HTTPS:"
echo -e "   ${GREEN}https://91.218.245.178${NC}"
echo ""
echo "2. HTTP автоматически перенаправляется на HTTPS"
echo ""
echo "3. ⚠️  Используется самоподписанный сертификат"
echo "   Браузер покажет предупреждение о безопасности"
echo "   Это нормально для IP адреса"
echo ""
echo "4. Для удаления предупреждения необходимо:"
echo "   - Купить доменное имя (например, lootlink.ru)"
echo "   - Настроить DNS на IP $SERVER_IP"
echo "   - Установить Let's Encrypt сертификат"
echo ""
echo "5. Срок действия сертификата: $CERT_DAYS дней"
echo "   После истечения нужно будет перегенерировать"
echo ""
echo -e "${YELLOW}🔧 Обновите Django настройки:${NC}"
echo "   В файле .env установите:"
echo "   SECURE_SSL_REDIRECT=True"
echo "   SESSION_COOKIE_SECURE=True"
echo "   CSRF_COOKIE_SECURE=True"
echo ""
echo -e "${GREEN}Готово!${NC} 🎉"

