# Redis Usage Guide for LootLink

## Что кешируется

### 1. **Статистика главной страницы** (5 минут)
```python
# listings/views.py - landing_page
cache_key = 'homepage_stats'
stats = cache.get(cache_key)
if stats is None:
    stats = {...}  # Вычисляем статистику
    cache.set(cache_key, stats, 300)  # 5 минут
```

### 2. **Список игр** (1 час)
```python
from django.core.cache import cache

cache_key = 'active_games'
games = cache.get(cache_key)
if games is None:
    games = Game.objects.filter(is_active=True)
    cache.set(cache_key, games, 3600)  # 1 час
```

### 3. **Количество непрочитанных уведомлений** (1 минута)
```python
# core/context_processors.py
cache_key = f'unread_notif_count_{user.id}'
unread_count = cache.get(cache_key)
if unread_count is None:
    unread_count = Notification.objects.filter(
        user=user, is_read=False
    ).count()
    cache.set(cache_key, unread_count, 60)  # 1 минута
```

### 4. **Профиль пользователя** (5 минут)
```python
cache_key = f'user_profile_{username}'
profile_data = cache.get(cache_key)
if profile_data is None:
    profile_data = {...}  # Загружаем профиль
    cache.set(cache_key, profile_data, 300)  # 5 минут
```

### 5. **Rate Limiting** (по времени окна)
```python
# core/middleware.py - SimpleRateLimitMiddleware
cache_key = f'rate_limit:{path}:{ip}'
attempts = cache.get(cache_key, [])
cache.set(cache_key, attempts, time_window)
```

## Инвалидация кеша

### При создании/обновлении объявления
```python
from django.core.cache import cache

def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    # Инвалидируем кеш каталога
    cache.delete('homepage_stats')
    cache.delete_pattern('catalog:*')
```

### При изменении игры
```python
def save(self, *args, **kwargs):
    super().save(*args, **kwargs)
    cache.delete('active_games')
```

### При прочтении уведомления
```python
def mark_as_read(self):
    self.is_read = True
    self.save()
    # Инвалидируем кеш счетчика
    cache.delete(f'unread_notif_count_{self.user.id}')
```

## Команды Redis CLI

### Мониторинг
```bash
# Подключиться к Redis
docker exec -it lootlink_redis redis-cli

# Просмотр всех ключей
KEYS *

# Просмотр ключей LootLink
KEYS lootlink:*

# Информация о Redis
INFO

# Статистика памяти
INFO memory

# Количество ключей
DBSIZE

# Мониторинг в реальном времени
MONITOR
```

### Управление кешем
```bash
# Удалить конкретный ключ
DEL lootlink:1:homepage_stats

# Удалить все ключи с паттерном
KEYS lootlink:*:user_profile_* | xargs redis-cli DEL

# Очистить весь кеш
FLUSHDB

# TTL ключа (время до удаления)
TTL lootlink:1:homepage_stats

# Установить время жизни ключа
EXPIRE lootlink:1:homepage_stats 600
```

## Настройки Production

В `.env` файле:
```env
USE_REDIS=True
REDIS_URL=redis://redis:6379/1
```

Для внешнего Redis (например, AWS ElastiCache):
```env
USE_REDIS=True
REDIS_URL=redis://your-redis-instance.aws.com:6379/1
```

## Производительность

### Преимущества Redis
- **Скорость**: 10,000+ операций/сек
- **Масштабируемость**: Горизонтальное масштабирование через Redis Cluster
- **Персистентность**: AOF (Append Only File) для сохранения данных
- **Экономия БД**: Снижение нагрузки на PostgreSQL на 40-60%

### Рекомендации
1. Кешировать часто запрашиваемые данные (статистика, рейтинги)
2. Не кешировать данные требующие строгой консистентности (баланс, транзакции)
3. Использовать короткое TTL для динамичных данных (1-5 минут)
4. Использовать длинное TTL для статичных данных (1-24 часа)

### Мониторинг
```python
# Проверка подключения к Redis
from django.core.cache import cache

try:
    cache.set('test_key', 'test_value', 10)
    value = cache.get('test_key')
    if value == 'test_value':
        print('✅ Redis работает!')
    else:
        print('❌ Redis не отвечает')
except Exception as e:
    print(f'❌ Ошибка Redis: {e}')
```

## Graceful Degradation

Если Redis недоступен, приложение продолжает работать:
- `IGNORE_EXCEPTIONS = True` в настройках
- Данные загружаются напрямую из БД
- Пользователь не видит ошибок
- В логах фиксируется недоступность Redis

## Best Practices

1. **Префикс ключей**: Всегда используйте префикс `lootlink:`
2. **Versioning**: Включайте версию в ключ при изменении структуры: `v2:user_profile`
3. **Compression**: Включена Zlib компрессия для больших объектов
4. **Monitoring**: Используйте `django-redis` метрики для мониторинга
5. **Memory**: Настроено `maxmemory-policy=allkeys-lru` (удаление старых ключей)

## Troubleshooting

### Redis не подключается
```bash
# Проверить статус контейнера
docker ps | grep redis

# Проверить логи
docker logs lootlink_redis

# Перезапустить Redis
docker restart lootlink_redis
```

### Медленные запросы
```bash
# Включить slow log
CONFIG SET slowlog-log-slower-than 10000  # 10ms
SLOWLOG GET 10  # Показать 10 медленных команд
```

### Очистка памяти
```bash
# Посмотреть использование памяти
INFO memory

# Очистить expired ключи
KEYS * | xargs -L 1 TTL
```

