# Настройка Celery для LootLink

## Что такое Celery?

Celery - это распределенная очередь задач для Python, которая позволяет выполнять задачи асинхронно в фоновом режиме.

## Зачем нужен Celery в LootLink?

1. **Асинхронная отправка email** - не блокирует HTTP запросы
2. **Периодические задачи** - очистка старых данных, обновление рейтингов
3. **Масштабируемость** - можно запустить несколько воркеров

## Установка

### 1. Установите Redis (если еще не установлен)

**Windows:**
```bash
# Скачайте Redis для Windows с https://github.com/microsoftarchive/redis/releases
# Или используйте Docker:
docker run -d -p 6379:6379 redis:alpine
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Mac
brew install redis
```

### 2. Установите зависимости Python

```bash
pip install celery[redis]>=5.3.0
```

### 3. Настройте переменные окружения

Добавьте в `.env`:
```env
# Celery Settings
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Запуск

### Development (локально)

Откройте 3 терминала:

**Терминал 1 - Django сервер:**
```bash
python manage.py runserver
```

**Терминал 2 - Celery worker:**
```bash
celery -A config worker -l info --pool=solo
```

**Терминал 3 - Celery beat (периодические задачи):**
```bash
celery -A config beat -l info
```

### Production

Используйте supervisor или systemd для управления процессами.

**Пример systemd service (celery-worker.service):**
```ini
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/lootlink
ExecStart=/path/to/venv/bin/celery -A config worker -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

**Пример systemd service (celery-beat.service):**
```ini
[Unit]
Description=Celery Beat
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/lootlink
ExecStart=/path/to/venv/bin/celery -A config beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

## Доступные задачи

### core.tasks.send_email_async
Асинхронная отправка email.

```python
from core.tasks import send_email_async

send_email_async.delay(
    subject='Тема',
    message='Текст письма',
    recipient='user@example.com'
)
```

### core.tasks.cleanup_old_data
Очистка старых данных (запускается автоматически раз в день).

Удаляет:
- Истекшие коды сброса пароля (>24 часа)
- Неиспользованные токены верификации (>7 дней)
- Старые прочитанные уведомления (>30 дней)

### core.tasks.update_user_ratings
Обновление рейтингов пользователей (запускается автоматически раз в час).

## Мониторинг

### Flower - Web UI для Celery

Установка:
```bash
pip install flower
```

Запуск:
```bash
celery -A config flower
```

Откройте браузер: `http://localhost:5555`

### Проверка состояния

```bash
# Проверить активные задачи
celery -A config inspect active

# Проверить зарегистрированные задачи
celery -A config inspect registered

# Статистика
celery -A config inspect stats
```

## Troubleshooting

### Redis не запускается
```bash
# Проверьте статус
redis-cli ping
# Должно вернуть: PONG
```

### Celery worker не видит задачи
1. Убедитесь что Redis запущен
2. Проверьте CELERY_BROKER_URL в .env
3. Перезапустите worker

### Задачи не выполняются
1. Проверьте логи worker: `celery -A config worker -l debug`
2. Убедитесь что task зарегистрирован: `celery -A config inspect registered`

## Рекомендации

1. **Development**: Используйте `--pool=solo` на Windows
2. **Production**: Используйте supervisor/systemd для автозапуска
3. **Мониторинг**: Установите Flower для визуального мониторинга
4. **Безопасность**: Используйте пароль для Redis в production

## Дополнительная информация

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/documentation)
- [Django + Celery Best Practices](https://docs.celeryq.dev/en/stable/django/)

