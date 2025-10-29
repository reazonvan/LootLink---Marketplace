#!/bin/bash
# Скрипт перезапуска продакшн сервера на Linux

cd /opt/lootlink
source venv/bin/activate

echo "1. Обновление кода..."
git fetch origin
git reset --hard origin/main

echo "2. Сборка статики..."
python manage.py collectstatic --noinput --clear

echo "3. Применение миграций..."
python manage.py migrate

echo "4. Очистка кэша..."
python scripts/clear_cache.py

echo "5. Перезапуск Gunicorn..."
sudo systemctl restart lootlink

echo "6. Перезагрузка Nginx..."
sudo systemctl reload nginx

echo "7. Проверка статуса..."
sudo systemctl status lootlink --no-pager | head -20

echo ""
echo "ГОТОВО!"

