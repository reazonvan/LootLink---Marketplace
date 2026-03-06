# 💾 Настройка Автоматических Бекапов

## 📋 Описание

Скрипт `scripts/auto_backup.sh` создает автоматические бекапы:
- База данных PostgreSQL (сжатый SQL dump)
- Медиа файлы (аватары, изображения объявлений)
- Автоматическое удаление старых бекапов (по умолчанию старше 30 дней)

---

## 🚀 Установка

### Шаг 1: Подготовка скрипта

```bash
# Перейти в директорию проекта
cd /opt/lootlink

# Сделать скрипт исполняемым
chmod +x scripts/auto_backup.sh

# Создать директорию для бекапов
sudo mkdir -p /var/backups/lootlink
sudo chown $USER:$USER /var/backups/lootlink
```

### Шаг 2: Тестовый запуск

```bash
# Запустить скрипт вручную для проверки
./scripts/auto_backup.sh
```

Вывод должен показать:
```
[2025-10-28 12:00:00] Создание директории для бекапов...
[2025-10-28 12:00:01] Начало бекапа базы данных...
[2025-10-28 12:00:05] База данных успешно сохранена: /var/backups/lootlink/db_20251028_120001.sql.gz
[2025-10-28 12:00:05] Размер бекапа БД: 1.2M
[2025-10-28 12:00:05] Начало бекапа медиа файлов...
[2025-10-28 12:00:08] Медиа файлы успешно сохранены: /var/backups/lootlink/media_20251028_120005.tar.gz
[2025-10-28 12:00:08] Размер бекапа медиа: 5.3M
[2025-10-28 12:00:08] Статистика бекапов:
[2025-10-28 12:00:08]   - Всего файлов: 2
[2025-10-28 12:00:08]   - Общий размер: 6.5M
[2025-10-28 12:00:08]   - Директория: /var/backups/lootlink
[2025-10-28 12:00:08] Бекап завершен успешно!
```

### Шаг 3: Настройка автоматического запуска (Cron)

```bash
# Открыть crontab для редактирования
crontab -e

# Добавить строку (запуск каждый день в 2 ночи):
0 2 * * * /opt/lootlink/scripts/auto_backup.sh >> /var/log/lootlink-backup.log 2>&1
```

**Другие варианты расписания:**

```bash
# Каждый день в 3 ночи
0 3 * * * /opt/lootlink/scripts/auto_backup.sh

# Каждые 12 часов (в 2 ночи и 2 дня)
0 2,14 * * * /opt/lootlink/scripts/auto_backup.sh

# Каждый понедельник в 1 ночи
0 1 * * 1 /opt/lootlink/scripts/auto_backup.sh

# Дважды в день (2 ночи и 14:00)
0 2 * * * /opt/lootlink/scripts/auto_backup.sh
0 14 * * * /opt/lootlink/scripts/auto_backup.sh
```

---

## Настройка

Откройте `scripts/auto_backup.sh` и измените переменные:

```bash
# Директория для хранения бекапов
BACKUP_DIR="/var/backups/lootlink"

# Имя базы данных
DB_NAME="lootlink_db"

# Пользователь PostgreSQL
DB_USER="lootlink_user"

# Путь к медиа файлам
MEDIA_DIR="/opt/lootlink/media"

# Сколько дней хранить бекапы
RETENTION_DAYS=30  # По умолчанию 30 дней
```

---

## 📊 Мониторинг бекапов

### Проверка последнего бекапа

```bash
# Список всех бекапов
ls -lh /var/backups/lootlink/

# Последние 5 бекапов
ls -lt /var/backups/lootlink/ | head -5

# Размер всех бекапов
du -sh /var/backups/lootlink/
```

### Проверка логов

```bash
# Просмотр логов бекапов
tail -f /var/log/lootlink-backup.log

# Последние 50 строк логов
tail -50 /var/log/lootlink-backup.log
```

### Проверка запланированных задач

```bash
# Просмотр текущего расписания cron
crontab -l

# Проверка запущенных заданий cron
sudo systemctl status cron
```

---

## 🔄 Восстановление из бекапа

### Восстановление базы данных

```bash
# 1. Найти нужный бекап
ls -lt /var/backups/lootlink/db_*.sql.gz

# 2. Распаковать бекап
gunzip -c /var/backups/lootlink/db_20251028_120001.sql.gz > restore.sql

# 3. Остановить приложение
sudo systemctl stop lootlink

# 4. Восстановить базу данных
sudo -u postgres psql lootlink_db < restore.sql

# 5. Запустить приложение
sudo systemctl start lootlink

# 6. Проверить что все работает
sudo systemctl status lootlink
```

### Восстановление медиа файлов

```bash
# 1. Найти бекап медиа
ls -lt /var/backups/lootlink/media_*.tar.gz

# 2. Создать резервную копию текущих медиа (на всякий случай)
mv /opt/lootlink/media /opt/lootlink/media_old

# 3. Распаковать бекап
cd /opt/lootlink
tar -xzf /var/backups/lootlink/media_20251028_120005.tar.gz

# 4. Установить правильные права
sudo chown -R www-data:www-data /opt/lootlink/media/

# 5. Перезапустить приложение
sudo systemctl restart lootlink
```

---

## 🚨 Устранение проблем

### Ошибка: permission denied

```bash
# Проверить права на директорию
ls -ld /var/backups/lootlink

# Установить правильные права
sudo chown -R $USER:$USER /var/backups/lootlink
sudo chmod 755 /var/backups/lootlink
```

### Ошибка: pg_dump command not found

```bash
# Установить PostgreSQL client
sudo apt update
sudo apt install postgresql-client
```

### Ошибка: database does not exist

```bash
# Проверить существующие базы данных
sudo -u postgres psql -l

# Проверить имя базы в скрипте
grep "DB_NAME=" scripts/auto_backup.sh
```

### Бекапы не запускаются по расписанию

```bash
# Проверить что cron работает
sudo systemctl status cron

# Проверить логи cron
sudo tail -f /var/log/syslog | grep CRON

# Убедиться что путь к скрипту полный
crontab -l
# Должно быть: /opt/lootlink/scripts/auto_backup.sh
# НЕ: scripts/auto_backup.sh
```

---

## 📦 Хранение бекапов в облаке

### Вариант 1: S3 (AWS/DigitalOcean Spaces/etc)

```bash
# Установить AWS CLI
sudo apt install awscli

# Настроить credentials
aws configure

# Добавить в конец скрипта auto_backup.sh:
aws s3 sync /var/backups/lootlink/ s3://your-bucket/lootlink-backups/
```

### Вариант 2: rsync на удаленный сервер

```bash
# Настроить SSH ключи
ssh-keygen
ssh-copy-id user@backup-server.com

# Добавить в конец скрипта:
rsync -avz /var/backups/lootlink/ user@backup-server.com:/backups/lootlink/
```

---

## 📝 Рекомендации

### Хранение бекапов

1. **Локальные бекапы:** Хранить последние 7-30 дней на сервере
2. **Удаленные бекапы:** Копировать на внешний сервер или облако
3. **Архивные бекапы:** Сохранять ежемесячные бекапы отдельно

### Тестирование восстановления

```bash
# Рекомендуется раз в месяц проверять что бекапы работают:
# 1. Скачать последний бекап
# 2. Развернуть на тестовом сервере
# 3. Проверить что данные корректны
```

### Безопасность

```bash
# Ограничить доступ к директории бекапов
sudo chmod 700 /var/backups/lootlink

# Зашифровать бекапы (опционально)
gpg --encrypt --recipient your-email@example.com db_backup.sql.gz
```

---

## Чеклист настройки

- [ ] Скрипт исполняемый (`chmod +x`)
- [ ] Директория для бекапов создана
- [ ] Тестовый запуск успешен
- [ ] Cron настроен
- [ ] Логи проверяются
- [ ] Восстановление протестировано
- [ ] Удаленное хранение настроено (опционально)
- [ ] Уведомления настроены (опционально)

---

**Автор:** LootLink Team  
**Дата:** 28 Октября 2025  
**Версия:** 1.0

