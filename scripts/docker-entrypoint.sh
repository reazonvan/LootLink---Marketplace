#!/bin/bash
# Docker entrypoint скрипт для LootLink

set -e

echo "🚀 Запуск LootLink..."

# Ожидание готовности PostgreSQL
echo "⏳ Ожидание PostgreSQL..."
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
  echo "⏳ PostgreSQL еще не готов - ожидание..."
  sleep 2
done
echo "✅ PostgreSQL готов!"

# Применение миграций
echo "📦 Применение миграций базы данных..."
python manage.py migrate --noinput

# Сборка статических файлов
echo "🎨 Сборка статических файлов..."
python manage.py collectstatic --noinput --clear

# Создание суперпользователя (если не существует)
if [ "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "👤 Создание суперпользователя..."
    python manage.py createsuperuser \
        --noinput \
        --username $DJANGO_SUPERUSER_USERNAME \
        --email $DJANGO_SUPERUSER_EMAIL \
        2>/dev/null || echo "Суперпользователь уже существует"
fi

echo "✅ Инициализация завершена!"
echo "🌐 Запуск веб-сервера..."

# Запуск приложения
exec "$@"

