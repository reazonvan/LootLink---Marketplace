# 🚀 Развертывание LootLink на VPS - Краткая инструкция

## ⚡ Самый быстрый способ (3 команды)

### На вашем компьютере (Windows):

1. **Экспортируйте данные и запустите мастер развертывания:**
   ```cmd
   deploy_quick_start.bat
   ```
   Выберите пункт 1, затем пункт 3, затем пункт 5.

2. **Или вручную через PowerShell:**
   ```powershell
   # 1. Экспорт данных
   scripts\export_local_db.bat
   
   # 2. Загрузка проекта
   scp -r * root@91.218.245.178:/opt/lootlink/
   
   # 3. Подключение и деплой
   ssh root@91.218.245.178
   ```

### На сервере:

```bash
cd /opt/lootlink
chmod +x scripts/deploy_to_vps.sh
sudo bash scripts/deploy_to_vps.sh
```

**Готово!** Сайт будет доступен по адресу: http://91.218.245.178

---

## 📋 Что делает автоматический скрипт

✅ Устанавливает Python 3.11, PostgreSQL, Nginx, Redis  
✅ Создает и настраивает базу данных PostgreSQL  
✅ Устанавливает все Python зависимости  
✅ Генерирует SECRET_KEY и создает .env файл  
✅ Применяет миграции Django  
✅ Собирает статические файлы  
✅ Настраивает Gunicorn как systemd сервис  
✅ Настраивает Nginx как reverse proxy  
✅ Настраивает Celery Worker и Beat  
✅ Настраивает Firewall (UFW)  
✅ Настраивает Fail2ban для защиты  
✅ Запускает все сервисы  

---

## 🔧 После установки

### 1. Импорт ваших данных

```bash
cd /opt/lootlink
source venv/bin/activate

# Импорт базы данных
python manage.py loaddata lootlink_data_*.json

# Распаковка медиа файлов
tar -xzf lootlink_media_*.tar.gz
chown -R www-data:www-data media/
```

### 2. Создание администратора (если нужно)

```bash
cd /opt/lootlink
source venv/bin/activate
python manage.py createsuperuser
```

### 3. Настройка email (опционально)

Отредактируйте `/opt/lootlink/.env`:

```bash
sudo nano /opt/lootlink/.env
```

Измените строки:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password
```

Перезапустите:

```bash
sudo systemctl restart lootlink
```

---

## 🔐 Важные действия по безопасности

### 1. Смените пароль root СРАЗУ!

```bash
passwd
```

### 2. Создайте резервную копию

```bash
sudo -u postgres pg_dump lootlink_db > /var/backups/lootlink_backup.sql
```

---

## 🛠️ Полезные команды

```bash
# Перезапуск сервисов
sudo systemctl restart lootlink
sudo systemctl restart nginx

# Просмотр логов
sudo journalctl -u lootlink -f
sudo tail -f /var/log/nginx/lootlink-error.log

# Статус
sudo systemctl status lootlink nginx postgresql redis

# Обновление кода
cd /opt/lootlink
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart lootlink
```

---

## 📞 Проблемы?

Смотрите полную инструкцию: **DEPLOYMENT_INSTRUCTIONS.md**

---

**Данные вашего сервера:**

- IP: `91.218.245.178`
- ОС: Ubuntu 24.04
- Конфигурация: 4 vCore / 6GB RAM / 120GB SSD
- Панель управления: https://invapi.hostkey.ru/?id=174643

**Успешного развертывания! 🎉**

