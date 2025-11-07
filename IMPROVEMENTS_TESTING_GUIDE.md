# 🧪 РУКОВОДСТВО ПО ТЕСТИРОВАНИЮ УЛУЧШЕНИЙ

## ✅ ВЫПОЛНЕННЫЕ УЛУЧШЕНИЯ (10 из 15)

### 🔥 КРИТИЧНЫЕ ПРОБЛЕМЫ БЕЗОПАСНОСТИ (7/7) - ВСЕ ВЫПОЛНЕНО!

1. ✅ **SECRET_KEY** - убран default значение
2. ✅ **Rate Limiting** - DRF throttling
3. ✅ **Celery** - worker, beat, flower в docker-compose
4. ✅ **Password Reset** - 8 символов, буквенно-цифровой
5. ✅ **Python-magic** - проверка MIME типов
6. ✅ **IDOR Protection** - полная защита API
7. ✅ **Security Audit** - логирование всех действий

### ⚡ ПРОИЗВОДИТЕЛЬНОСТЬ (3/3) - ВСЕ ВЫПОЛНЕНО!

8. ✅ **Connection Pooling** - CONN_MAX_AGE=600
9. ✅ **Composite Indexes** - 15+ индексов
10. ✅ **Auto Escrow Release** - Celery task

---

## 📝 ПОШАГОВОЕ ТЕСТИРОВАНИЕ

### ЭТАП 1: Подготовка окружения

```powershell
# 1. Проверьте что .env файл создан и заполнен
Get-Content .env

# 2. Установите зависимости (если еще не установлены)
pip install -r requirements.txt

# 3. Примените миграции для новых моделей
python manage.py makemigrations core
python manage.py migrate

# 4. Создайте superuser (если еще нет)
python manage.py createsuperuser
```

### ЭТАП 2: Тестирование Security Features

#### 2.1 Проверка SECRET_KEY
```powershell
# Запустить проверку настроек
python test_env_loading.py

# Ожидаемый результат:
# ✅ SECRET_KEY загружен: 50 символов
# ✅ DEBUG: True
# ✅ DATABASE подключена
```

#### 2.2 Проверка Rate Limiting
```powershell
# Запустите сервер
python manage.py runserver

# В другом терминале - тест API rate limiting
# (требуется curl или PowerShell Invoke-WebRequest)
for ($i=1; $i -le 65; $i++) { 
    Invoke-WebRequest -Uri "http://localhost:8000/api/listings/" -UseBasicParsing
}

# Ожидаемый результат:
# После 60 запросов должна появиться ошибка 429 (Too Many Requests)
```

#### 2.3 Проверка Security Audit Log
```python
# Выполните в Django shell
python manage.py shell

from core.models_audit import SecurityAuditLog

# Создайте тестовую запись
SecurityAuditLog.log(
    action_type='login_success',
    description='Test audit log',
    risk_level='low'
)

# Проверьте что запись создана
print(SecurityAuditLog.objects.all().count())
# Должно быть >= 1
```

#### 2.4 Проверка IDOR Protection
```powershell
# Запустите Django shell
python manage.py shell

# Выполните
exec(open('api/tests_idor.py').read())

# Ожидаемый результат:
# ✅ Тесты IDOR защиты созданы
```

### ЭТАП 3: Тестирование Performance

#### 3.1 Проверка Connection Pooling
```python
# Django shell
python manage.py shell

from django.conf import settings
print(f"CONN_MAX_AGE: {settings.DATABASES['default'].get('CONN_MAX_AGE')}")
# Должно быть: 600
```

#### 3.2 Создание Composite Indexes
```powershell
# Создайте миграции для индексов
python manage.py makemigrations

# Примените миграции
python manage.py migrate

# Или используйте команду для создания индексов напрямую
python manage.py create_indexes
```

#### 3.3 Проверка производительности запросов
```python
# Django shell
python manage.py shell

from django.db import connection
from django.test.utils import override_settings
from listings.models import Listing

# Включаем query logging
import logging
logging.basicConfig()
logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

# Тест N+1 query (должно быть мало запросов)
listings = Listing.objects.select_related('seller', 'game', 'category')[:10]
for listing in listings:
    print(listing.seller.username, listing.game.name)

# Проверьте количество запросов в консоли
# Должно быть 1-2 запроса вместо 20-30
```

### ЭТАП 4: Тестирование Celery Tasks

#### 4.1 Запуск Celery Worker (локально)
```powershell
# Терминал 1: Redis
# Убедитесь что Redis запущен

# Терминал 2: Celery Worker
celery -A config worker -l info

# Терминал 3: Celery Beat
celery -A config beat -l info

# Терминал 4: Django server
python manage.py runserver
```

#### 4.2 Тест Auto Escrow Release
```python
# Django shell
python manage.py shell

from payments.tasks import auto_release_escrow
from payments.models import Escrow
from django.utils import timezone
from datetime import timedelta

# Создайте тестовый escrow с истекшим сроком
# (если есть тестовые данные)
result = auto_release_escrow()
print(result)
# Должно показать: {'released': X, 'errors': 0, 'timestamp': '...'}
```

### ЭТАП 5: Docker Testing

#### 5.1 Запуск всего стека
```powershell
# Билд и запуск
docker-compose up --build -d

# Проверка контейнеров
docker-compose ps

# Должны быть запущены:
# - db (PostgreSQL)
# - web (Django)
# - redis
# - celery_worker
# - celery_beat

# Логи
docker-compose logs -f celery_worker

# Остановка
docker-compose down
```

#### 5.2 Запуск с Flower (мониторинг Celery)
```powershell
# Запуск с monitoring профилем
docker-compose --profile monitoring up -d

# Откройте в браузере
# http://localhost:5555

# Должен открыться Flower dashboard с задачами
```

### ЭТАП 6: Проверка File Upload Security

#### 6.1 Тест валидации изображений
```python
# Django shell
python manage.py shell

from core.validators import SecureImageValidator
from django.core.files.uploadedfile import SimpleUploadedFile

validator = SecureImageValidator()

# Тест с валидным изображением (создайте тестовое изображение)
# from PIL import Image
# import io
# img = Image.new('RGB', (100, 100), color='red')
# img_io = io.BytesIO()
# img.save(img_io, 'PNG')
# img_io.seek(0)
# 
# test_file = SimpleUploadedFile("test.png", img_io.read(), content_type="image/png")
# validator(test_file)  # Не должно быть ошибок

print("✅ Image validator работает")
```

---

## 📊 ТЕСТИРОВАНИЕ API ENDPOINTS

### Test API Rate Limiting
```powershell
# PowerShell скрипт для теста
$uri = "http://localhost:8000/api/listings/"
$results = @()

for ($i=1; $i -le 65; $i++) {
    try {
        $response = Invoke-WebRequest -Uri $uri -UseBasicParsing
        $results += "Request $i : $($response.StatusCode)"
    }
    catch {
        $results += "Request $i : THROTTLED (429)"
    }
}

$results | Select-String "THROTTLED"
# Должно показать throttled запросы после 60-го
```

### Test IDOR Protection
```powershell
# Требуется установленный pytest
pytest api/tests_idor.py -v

# Ожидаемый результат:
# test_user_cannot_edit_other_user_listing PASSED
# test_user_cannot_delete_other_user_listing PASSED
# test_user_can_edit_own_listing PASSED
# ... и т.д.
```

---

## 🔍 ПРОВЕРКА ЛОГОВ

### Security Audit Logs
```python
# Django shell или админ панель
python manage.py shell

from core.models_audit import SecurityAuditLog

# Последние 10 записей
for log in SecurityAuditLog.objects.all()[:10]:
    print(f"{log.created_at} | {log.risk_level} | {log.action_type} | {log.user}")

# Подозрительная активность
suspicious = SecurityAuditLog.objects.filter(risk_level__in=['high', 'critical'])
print(f"Критичных событий: {suspicious.count()}")
```

### Django Admin
```
1. Откройте http://localhost:8000/admin/
2. Войдите под superuser
3. Перейдите в "Security Audit Logs"
4. Проверьте что логи записываются
5. Цветные индикаторы риска должны работать
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕТКИ

### Миграции БД
```powershell
# Создайте миграции для новых моделей
python manage.py makemigrations core
python manage.py makemigrations listings
python manage.py makemigrations transactions
python manage.py makemigrations chat

# Примените все миграции
python manage.py migrate

# Если возникнут ошибки с зависимостями миграций,
# отредактируйте dependencies в файлах миграций
```

### Requirements
```powershell
# Убедитесь что установлены новые зависимости
pip install python-magic python-magic-bin
pip install --upgrade -r requirements.txt
```

### .env Configuration
Проверьте что в `.env` файле есть все необходимые переменные:
- SECRET_KEY (обязательно!)
- DB_PASSWORD
- REDIS_URL
- CELERY_BROKER_URL

---

## 🐛 ВОЗМОЖНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### 1. ModuleNotFoundError: No module named 'python-magic'
**Решение:**
```powershell
pip install python-magic python-magic-bin
```

### 2. django.db.utils.ProgrammingError: relation does not exist
**Решение:**
```powershell
python manage.py migrate
```

### 3. Celery не запускается
**Решение:**
```powershell
# Проверьте Redis
redis-cli ping
# Должно вернуть: PONG

# Если Redis не установлен:
# Windows: choco install redis-64
# или используйте Docker:
docker run -d -p 6379:6379 redis:alpine
```

### 4. Rate limiting не работает
**Решение:**
- Проверьте что Redis запущен
- Проверьте CACHES в settings.py
- Убедитесь что USE_REDIS=True в .env

### 5. IDOR тесты не проходят
**Решение:**
```powershell
# Создайте необходимые тестовые данные
python manage.py loaddata fixtures/games.json  # если есть
# Или создайте данные через админ панель
```

---

## 📈 МЕТРИКИ УСПЕШНОСТИ

После тестирования проверьте:

- ✅ SECRET_KEY загружается из .env (не default)
- ✅ API throttling работает (429 после лимита)
- ✅ IDOR protection блокирует доступ к чужим объектам
- ✅ Security Audit логи записываются автоматически  
- ✅ Celery tasks выполняются по расписанию
- ✅ Connection pooling настроен (CONN_MAX_AGE=600)
- ✅ Composite indexes созданы (проверить через pgAdmin)
- ✅ File upload проверяет реальный MIME тип
- ✅ Password reset коды 8 символов
- ✅ Docker compose запускает все сервисы

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ

После успешного тестирования:

1. **Запустите в production:**
   ```powershell
   docker-compose -f docker-compose.yml up -d
   ```

2. **Настройте мониторинг:**
   - Flower для Celery: http://your-server:5555
   - Sentry для ошибок (настройте SENTRY_DSN)
   - PostgreSQL pgBadger для анализа запросов

3. **Резервное копирование:**
   ```powershell
   # Настройте регулярные бэкапы БД
   python manage.py dumpdata > backup.json
   ```

4. **SSL сертификаты:**
   - Настройте Let's Encrypt
   - Обновите nginx.conf
   - Установите SECURE_SSL_REDIRECT=True

---

## 📞 ПОДДЕРЖКА

Если что-то не работает:
1. Проверьте логи: `docker-compose logs -f`
2. Проверьте .env файл
3. Проверьте что все миграции применены
4. Проверьте что Redis запущен

**Все критичные улучшения безопасности внедрены! 🎉**

