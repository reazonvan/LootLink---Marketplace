# 🔌 Инструкция по настройке WebSocket чата

## Текущий статус
✅ Чат работает в **polling режиме** (обновления каждые 3 секунды)  
⚠️ Для **real-time** WebSocket нужно запустить Daphne

## Быстрая настройка WebSocket (5 минут)

### Шаг 1: Проверка Redis
```bash
redis-cli ping
# Должно вернуть: PONG
```

Если Redis не установлен:
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

### Шаг 2: Остановка Gunicorn
```bash
sudo systemctl stop lootlink
```

### Шаг 3: Создание Daphne service
```bash
sudo nano /etc/systemd/system/daphne.service
```

Вставьте:
```ini
[Unit]
Description=Daphne ASGI Server for LootLink
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/lootlink
Environment="PATH=/opt/lootlink/venv/bin"
ExecStart=/opt/lootlink/venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application

Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### Шаг 4: Запуск Daphne
```bash
sudo systemctl daemon-reload
sudo systemctl start daphne
sudo systemctl enable daphne
sudo systemctl status daphne
```

### Шаг 5: Обновление Nginx
В `/etc/nginx/sites-available/lootlink` добавьте:
```nginx
# WebSocket support
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Перезапустите Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Шаг 6: Проверка
Откройте чат на сайте и проверьте консоль браузера:
- Должно быть: `✅ WebSocket подключен`
- Индикатор "печатает..." должен работать мгновенно

---

## Альтернатива: Продолжить с Polling

Если не хотите настраивать WebSocket, чат будет продолжать работать через polling (текущий режим).  
Rate limit увеличен до 200 запросов/минуту - этого достаточно для комфортной работы.

**Преимущества polling:**
- ✅ Работает из коробки
- ✅ Не требует дополнительной настройки
- ✅ Совместимо с любым веб-сервером

**Недостатки:**
- ⚠️ Задержка 3 секунды (вместо мгновенной доставки)
- ⚠️ Нет индикатора "печатает..."

---

## Текущее состояние
🟢 **Чат работает** через polling  
🟡 **WebSocket** требует настройки Daphne  
✅ **Fallback** автоматический

