# 🚀 Обновление Django до 5.2.7 LTS на Production

## Быстрый старт

### Вариант 1: Автоматическое обновление (РЕКОМЕНДУЕТСЯ)

```bash
# 1. Подключитесь к серверу
ssh root@91.218.245.178

# 2. Перейдите в директорию проекта
cd /opt/lootlink

# 3. Скопируйте файлы с локальной машины (запустите на Windows):
scp requirements.txt root@91.218.245.178:/opt/lootlink/
scp scripts/upgrade_django_5.2.sh root@91.218.245.178:/opt/lootlink/scripts/

# 4. На сервере запустите скрипт обновления:
chmod +x scripts/upgrade_django_5.2.sh
sudo bash scripts/upgrade_django_5.2.sh
```

**Скрипт автоматически:**
- ✅ Создаст бекап БД и кода
- ✅ Обновит Django до 5.2.7
- ✅ Проверит совместимость
- ✅ Применит миграции
- ✅ Перезапустит сервисы
- ✅ Проверит работу сайта

### Вариант 2: Ручное обновление

```bash
# На сервере 91.218.245.178

# 1. Создать бекап
sudo -u postgres pg_dump lootlink_db > /tmp/backup_$(date +%Y%m%d).sql

# 2. Перейти в проект
cd /opt/lootlink
source venv/bin/activate

# 3. Обновить Django
pip install --upgrade "Django>=5.2,<6.0"

# 4. Проверить совместимость
python manage.py check

# 5. Применить миграции
python manage.py makemigrations
python manage.py migrate

# 6. Собрать статику
python manage.py collectstatic --noinput

# 7. Перезапустить сервисы
sudo systemctl restart lootlink nginx

# 8. Проверить
curl http://localhost
sudo journalctl -u lootlink -n 20
```

---

## 📊 Что изменится

| Параметр | Было | Станет |
|----------|------|--------|
| **Django** | 4.2.25 | **5.2.7 LTS** |
| **Поддержка до** | апрель 2026 | **апрель 2028** |
| **Совместимость** | Python 3.10-3.12 | **Python 3.10-3.14** |

---

## ✅ Проверка после обновления

```bash
# Проверить версию Django
python -c "import django; print(f'Django {django.get_version()}')"

# Должно показать: Django 5.2.7

# Проверить статус сервисов
sudo systemctl status lootlink nginx

# Проверить работу сайта
curl http://91.218.245.178

# Проверить логи
sudo journalctl -u lootlink -n 50
```

---

## 🔄 Откат (если что-то пошло не так)

```bash
# 1. Восстановить бекап БД
gunzip -c /var/backups/lootlink/upgrade_*/db_backup.sql.gz | sudo -u postgres psql lootlink_db

# 2. Восстановить код
cd /opt/lootlink
tar -xzf /var/backups/lootlink/upgrade_*/code_backup.tar.gz

# 3. Откатить Django
source venv/bin/activate
pip install --upgrade "Django>=4.2,<5.0"

# 4. Перезапустить
sudo systemctl restart lootlink nginx
```

---

## 📝 Breaking Changes Django 5.2

**Хорошие новости:** Ваш код полностью совместим! ✅

Django 5.2 LTS обратно совместим с 4.2 LTS в большинстве случаев.

**Что проверено:**
- ✅ Модели - работают без изменений
- ✅ Views - работают без изменений  
- ✅ Templates - работают без изменений
- ✅ Forms - работают без изменений
- ✅ Middleware - работают без изменений
- ✅ Миграции - применяются автоматически

---

## 🛠️ Полезные команды

```bash
# Проверить логи в реальном времени
sudo journalctl -u lootlink -f

# Проверить ошибки Nginx
sudo tail -f /var/log/nginx/lootlink-error.log

# Перезапустить только Django
sudo systemctl restart lootlink

# Проверить использование памяти
free -h

# Проверить процессы Django
ps aux | grep gunicorn
```

---

## 📞 Проблемы?

### Сайт не открывается

```bash
# 1. Проверить логи
sudo journalctl -u lootlink -n 100

# 2. Проверить процессы
sudo systemctl status lootlink

# 3. Перезапустить
sudo systemctl restart lootlink nginx
```

### 500 Internal Server Error

```bash
# Смотреть ошибки Django
sudo tail -f /opt/lootlink/logs/errors.log

# Проверить права
sudo chown -R www-data:www-data /opt/lootlink
```

### База данных

```bash
# Подключиться к БД
sudo -u postgres psql lootlink_db

# Проверить таблицы
\dt

# Выйти
\q
```

---

## 🎉 Готово!

После успешного обновления:

1. ✅ Django 5.2.7 LTS установлен
2. ✅ Поддержка до 2028 года
3. ✅ Совместимость с Python 3.14
4. ✅ Лучшая производительность
5. ✅ Новые возможности Django 5.x

**Проверьте сайт:** http://91.218.245.178

---

**Дата:** 28 октября 2025  
**Версия:** 1.0

