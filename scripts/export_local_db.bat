@echo off
REM ===========================================
REM Экспорт локальной базы данных для Windows
REM ===========================================

echo 📦 Экспорт данных из локальной базы данных...

REM Проверка наличия manage.py
if not exist "manage.py" (
    echo ❌ Ошибка: manage.py не найден. Запустите скрипт из корня проекта.
    pause
    exit /b 1
)

REM Проверка наличия db.sqlite3
if not exist "db.sqlite3" (
    echo ❌ Ошибка: db.sqlite3 не найден.
    pause
    exit /b 1
)

REM Создание директории для экспорта
if not exist "exports" mkdir exports

REM Имя файла с датой
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set EXPORT_FILE=exports\lootlink_data_%datetime:~0,8%_%datetime:~8,6%.json

echo 📤 Экспортируем данные в %EXPORT_FILE%...

REM Экспорт данных Django
python manage.py dumpdata --natural-foreign --natural-primary --indent 2 --exclude auth.permission --exclude contenttypes --exclude admin.logentry --exclude sessions.session > "%EXPORT_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo ✅ Данные экспортированы: %EXPORT_FILE%
) else (
    echo ❌ Ошибка при экспорте данных
    pause
    exit /b 1
)

echo.
echo 📋 Для импорта на сервере выполните:
echo    1. Скопируйте файл на сервер:
echo       scp %EXPORT_FILE% root@91.218.245.178:/opt/lootlink/
echo.
echo    2. На сервере выполните:
echo       cd /opt/lootlink
echo       source venv/bin/activate
echo       python manage.py loaddata lootlink_data_*.json
echo.

REM Создание архива медиа файлов (если есть tar)
where tar >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if exist "media" (
        set MEDIA_ARCHIVE=exports\lootlink_media_%datetime:~0,8%_%datetime:~8,6%.tar.gz
        echo 📸 Создание архива медиа файлов...
        tar -czf "!MEDIA_ARCHIVE!" media\
        echo ✅ Медиа файлы архивированы: !MEDIA_ARCHIVE!
        echo.
        echo 📋 Для загрузки медиа на сервер:
        echo    scp !MEDIA_ARCHIVE! root@91.218.245.178:/opt/lootlink/
    )
) else (
    echo ⚠️  tar не найден, архив медиа не создан
    echo    Установите Git for Windows для использования tar
)

echo.
echo ✅ Экспорт завершен!
echo.
pause

