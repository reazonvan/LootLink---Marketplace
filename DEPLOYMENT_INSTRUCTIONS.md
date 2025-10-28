# 🚀 Инструкция по развертыванию LootLink на VPS

## 📋 Информация о сервере

- **IP адрес**: 91.218.245.178
- **Пользователь**: root
- **Пароль**: BWJ_1anRP0 (⚠️ СМЕНИТЕ СРАЗУ ПОСЛЕ ВХОДА!)
- **ОС**: Ubuntu 24.04
- **Конфигурация**: 4 vCore / 6GB RAM / 120GB SSD

---

## 🎯 Быстрый старт (3 шага)

### Шаг 1: Экспорт локальных данных

На вашем компьютере (Windows):

```bash
cd C:\Users\ivanp\Desktop\LootLink
scripts\export_local_db.bat
```

Это создаст файлы в папке `exports/`:
- `lootlink_data_*.json` - данные базы
- `lootlink_media_*.tar.gz` - медиа файлы

### Шаг 2: Подключение к серверу и загрузка проекта

```bash
# Подключитесь к серверу
ssh root@91.218.245.178
# Пароль: BWJ_1anRP0

# СРАЗУ СМЕНИТЕ ПАРОЛЬ!
passwd

# Создайте директорию для проекта
mkdir -p /opt/lootlink
cd /opt/lootlink
```

**Загрузите проект одним из способов:**

#### Вариант А: Через SCP (с вашего компьютера)

Откройте PowerShell на своем компьютере:

```powershell
cd C:\Users\ivanp\Desktop\LootLink

# Загрузить весь проект (без node_modules, __pycache__ и т.д.)
scp -r * root@91.218.245.178:/opt/lootlink/

# Загрузить экспортированные данные
scp exports\lootlink_data_*.json root@91.218.245.178:/opt/lootlink/
scp exports\lootlink_media_*.tar.gz root@91.218.245.178:/opt/lootlink/
```

#### Вариант Б: Через Git (если проект в репозитории)

На сервере:

```bash
cd /opt/lootlink
git clone https://github.com/ваш-username/LootLink.git .
```

### Шаг 3: Запуск автоматического деплоя

На сервере:

```bash
cd /opt/lootlink
chmod +x scripts/deploy_to_vps.sh
sudo bash scripts/deploy_to_vps.sh
```

Скрипт автоматически:
- ✅ Установит все необходимое (Python, PostgreSQL, Nginx, Redis)
- ✅ Настроит базу данных
- ✅ Создаст виртуальное окружение
- ✅ Установит зависимости
- ✅ Настроит Nginx и Gunicorn
- ✅ Настроит firewall
- ✅ Запустит все сервисы

### Шаг 4: Импорт данных (если есть)

```bash
cd /opt/lootlink
source venv/bin/activate

# Импорт данных
python manage.py loaddata lootlink_data_*.json

# Распаковка медиа (если есть)
tar -xzf lootlink_media_*.tar.gz
chown -R www-data:www-data media/
```

---

## 🎉 Готово!

Ваш сайт доступен по адресу: **http://91.218.245.178**

---

## 🛠️ Полезные команды

### Управление сервисами

```bash
# Перезапуск Django
sudo systemctl restart lootlink

# Перезапуск Nginx
sudo systemctl restart nginx

# Просмотр логов Django
sudo journalctl -u lootlink -f

# Просмотр логов Nginx
sudo tail -f /var/log/nginx/lootlink-error.log

# Статус всех сервисов
sudo systemctl status lootlink nginx postgresql redis
```

### Работа с Django

```bash
cd /opt/lootlink
source venv/bin/activate

# Создание суперпользователя
python manage.py createsuperuser

# Применение миграций
python manage.py migrate

# Сбор статики
python manage.py collectstatic --noinput

# Django shell
python manage.py shell
```

### Проверка работоспособности

```bash
# Проверка открытых портов
sudo netstat -tlnp | grep -E ':(80|443|8000|5432|6379)'

# Проверка процессов
ps aux | grep gunicorn

# Проверка Nginx конфигурации
sudo nginx -t

# Тест подключения к БД
sudo -u postgres psql -d lootlink_db -c "SELECT version();"
```

---

## 🔒 Дополнительная настройка безопасности

### 1. Настройка SSH ключей (рекомендуется)

На вашем компьютере:

```powershell
# Генерация SSH ключа (если нет)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Копирование ключа на сервер
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@91.218.245.178 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

На сервере отключите вход по паролю:

```bash
sudo nano /etc/ssh/sshd_config
# Найдите и измените:
# PasswordAuthentication no

sudo systemctl restart sshd
```

### 2. Настройка домена (когда будет)

```bash
# Обновите /opt/lootlink/.env
sudo nano /opt/lootlink/.env
# Измените ALLOWED_HOSTS=ваш-домен.ru,www.ваш-домен.ru

# Обновите Nginx конфиг
sudo nano /etc/nginx/sites-available/lootlink
# Измените server_name на ваш домен

# Получите SSL сертификат
sudo certbot --nginx -d ваш-домен.ru -d www.ваш-домен.ru

# Перезапустите сервисы
sudo systemctl restart lootlink nginx
```

### 3. Настройка email уведомлений

Отредактируйте `/opt/lootlink/.env`:

```bash
sudo nano /opt/lootlink/.env
```

Измените:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-app-password
DEFAULT_FROM_EMAIL=noreply@ваш-домен.ru
```

Перезапустите:

```bash
sudo systemctl restart lootlink
```

---

## 📊 Мониторинг

### Просмотр использования ресурсов

```bash
# CPU и память
htop

# Диск
df -h

# Сетевая активность
sudo iftop
```

### Бэкап базы данных

```bash
# Ручной бэкап
sudo -u postgres pg_dump lootlink_db > /var/backups/lootlink/backup_$(date +%Y%m%d).sql

# Автоматический бэкап (добавьте в crontab)
sudo crontab -e
# Добавьте: 0 2 * * * /opt/lootlink/scripts/backup_db.sh
```

---

## 🆘 Устранение проблем

### Сайт не открывается

```bash
# 1. Проверьте статус сервисов
sudo systemctl status lootlink nginx

# 2. Проверьте логи
sudo journalctl -u lootlink -n 50
sudo tail -f /var/log/nginx/lootlink-error.log

# 3. Проверьте сокет
ls -la /opt/lootlink/lootlink.sock

# 4. Перезапустите
sudo systemctl restart lootlink nginx
```

### 500 Internal Server Error

```bash
# Просмотр ошибок Django
sudo tail -f /var/log/lootlink/gunicorn-error.log

# Просмотр ошибок приложения
sudo tail -f /opt/lootlink/logs/errors.log

# Проверка прав
sudo chown -R www-data:www-data /opt/lootlink
```

### База данных недоступна

```bash
# Проверка PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -d lootlink_db -c "SELECT 1;"

# Проверка настроек подключения
cat /opt/lootlink/.env | grep DB_
```

---

## 📞 Поддержка

Если что-то пошло не так:

1. Проверьте логи (команды выше)
2. Перезапустите сервисы
3. Проверьте конфигурацию .env
4. Убедитесь, что все порты открыты

---

**Успешного деплоя! 🚀**

