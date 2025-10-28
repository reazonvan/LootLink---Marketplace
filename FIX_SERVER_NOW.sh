#!/bin/bash
# СРОЧНОЕ ИСПРАВЛЕНИЕ КЭША И СЕССИЙ НА ПРОДАКШЕН СЕРВЕРЕ

echo "🚨 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ - Очистка кэша и сессий"
echo "=================================================="

cd /opt/lootlink
source venv/bin/activate

echo ""
echo "1️⃣ Обновление кода..."
git pull origin main

echo ""
echo "2️⃣ КРИТИЧНО: Очистка кэша Django..."
python scripts/clear_cache.py

echo ""
echo "3️⃣ КРИТИЧНО: Очистка всех сессий..."
python scripts/clear_sessions.py

echo ""
echo "4️⃣ Сборка статических файлов..."
python manage.py collectstatic --noinput --clear

echo ""
echo "5️⃣ Перезапуск Gunicorn..."
sudo systemctl restart lootlink

echo ""
echo "6️⃣ Перезагрузка Nginx..."
sudo systemctl reload nginx

echo ""
echo "✅ ГОТОВО!"
echo ""
echo "⚠️  ВАЖНО: Откройте браузер в РЕЖИМЕ ИНКОГНИТО и перейдите на:"
echo "   http://91.218.245.178"
echo ""
echo "   Теперь НЕ должно быть профиля reazonvan!"
echo ""

