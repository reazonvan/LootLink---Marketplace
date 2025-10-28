@echo off
echo.
echo ======================================================
echo   ЗАПУСК УСТАНОВКИ НА СЕРВЕРЕ
echo ======================================================
echo.
echo Подключаемся к серверу и запускаем установку...
echo Пароль: BWJ_1anRP0
echo.

ssh -t root@91.218.245.178 "cd /opt/lootlink && chmod +x scripts/deploy_to_vps.sh && bash scripts/deploy_to_vps.sh"

echo.
echo ======================================================
echo   УСТАНОВКА ЗАВЕРШЕНА!
echo ======================================================
echo.
echo Импортируем данные...
ssh -t root@91.218.245.178 "cd /opt/lootlink && source venv/bin/activate && python manage.py loaddata lootlink_data_backup.json && unzip -o lootlink_media_backup.zip && chown -R www-data:www-data media/"

echo.
echo ======================================================
echo   ВСЁ ГОТОВО!
echo ======================================================
echo.
echo Ваш сайт доступен: http://91.218.245.178
echo.
pause

