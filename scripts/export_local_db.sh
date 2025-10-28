#!/bin/bash
# ===========================================
# Экспорт локальной базы данных SQLite в PostgreSQL dump
# ===========================================

set -e

echo "📦 Экспорт данных из локальной базы данных..."

# Проверка наличия manage.py
if [ ! -f "manage.py" ]; then
    echo "❌ Ошибка: manage.py не найден. Запустите скрипт из корня проекта."
    exit 1
fi

# Проверка наличия db.sqlite3
if [ ! -f "db.sqlite3" ]; then
    echo "❌ Ошибка: db.sqlite3 не найден."
    exit 1
fi

# Создание директории для экспорта
mkdir -p exports

# Имя файла с датой
EXPORT_FILE="exports/lootlink_data_$(date +%Y%m%d_%H%M%S).json"

echo "📤 Экспортируем данные в $EXPORT_FILE..."

# Экспорт данных Django
python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    --exclude auth.permission \
    --exclude contenttypes \
    --exclude admin.logentry \
    --exclude sessions.session \
    > "$EXPORT_FILE"

echo "✅ Данные экспортированы: $EXPORT_FILE"
echo ""
echo "📋 Для импорта на сервере выполните:"
echo "   1. Скопируйте файл на сервер:"
echo "      scp $EXPORT_FILE root@91.218.245.178:/opt/lootlink/"
echo ""
echo "   2. На сервере выполните:"
echo "      cd /opt/lootlink"
echo "      source venv/bin/activate"
echo "      python manage.py loaddata $(basename $EXPORT_FILE)"
echo ""

# Создание SQL дампа для медиа файлов
echo "📸 Создание архива медиа файлов..."
if [ -d "media" ]; then
    MEDIA_ARCHIVE="exports/lootlink_media_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$MEDIA_ARCHIVE" media/
    echo "✅ Медиа файлы архивированы: $MEDIA_ARCHIVE"
    echo ""
    echo "📋 Для загрузки медиа на сервер:"
    echo "   scp $MEDIA_ARCHIVE root@91.218.245.178:/opt/lootlink/"
    echo "   ssh root@91.218.245.178 'cd /opt/lootlink && tar -xzf $(basename $MEDIA_ARCHIVE) && chown -R www-data:www-data media/'"
else
    echo "⚠️  Папка media не найдена, пропускаем"
fi

echo ""
echo "✅ Экспорт завершен!"

