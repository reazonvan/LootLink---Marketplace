# LootLink Marketplace

> P2P маркетплейс для торговли внутриигровыми предметами между игроками

[![Live Demo](https://img.shields.io/badge/demo-lootlink.ru-blue)](https://lootlink.ru)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

LootLink — это full-stack веб-приложение для прямой торговли игровыми предметами между игроками. Построено на Django и PostgreSQL, предоставляет безопасную платформу для покупки, продажи и обмена виртуальных предметов без посредников.

**Демо:** [lootlink.ru](https://lootlink.ru)

---

## Содержание

- [Возможности](#возможности)
- [Технологии](#технологии)
- [Требования](#требования)
- [Установка](#установка)
- [Конфигурация](#конфигурация)
- [Использование](#использование)
- [Структура проекта](#структура-проекта)
- [API документация](#api-документация)
- [Тестирование](#тестирование)
- [Развертывание](#развертывание)
- [Производительность](#производительность)
- [Безопасность](#безопасность)
- [Участие в разработке](#участие-в-разработке)
- [Лицензия](#лицензия)
- [Контакты](#контакты)

---

## Возможности

### Основной функционал
- **Маркетплейс**: Создание, просмотр и поиск объявлений с расширенной фильтрацией
- **Чат в реальном времени**: Прямой обмен сообщениями между покупателями и продавцами
- **Система транзакций**: Формализованные запросы на покупку с отслеживанием статуса
- **Профили пользователей**: Система репутации на основе завершенных сделок
- **Система отзывов**: Рейтинги и отзывы о пользователях
- **Верификация email**: Подтверждение аккаунта через электронную почту
- **Панель администратора**: Кастомный интерфейс администратора для модерации

### Технические возможности
- RESTful API на Django REST Framework
- Уведомления в реальном времени
- Загрузка и оптимизация изображений
- Полнотекстовый поиск с PostgreSQL
- Кэширование с Redis для производительности
- Адаптивный дизайн на Bootstrap 5
- CSRF защита и заголовки безопасности
- Rate limiting и защита от brute-force атак
- Комплексное покрытие тестами

---

## Технологии

**Backend:**
- Python 3.10+
- Django 4.2
- Django REST Framework 3.16
- PostgreSQL 15
- Redis 7.0
- Celery 5.5 (асинхронные задачи)
- Django Channels 4.0 (WebSockets)

**Frontend:**
- Bootstrap 5.2
- JavaScript ES6+
- jQuery 3.6
- HTML5/CSS3

**Инфраструктура:**
- Docker & Docker Compose
- Nginx 1.24
- Gunicorn
- Systemd (production)

**Разработка:**
- Git
- pytest
- flake8, black, isort
- pre-commit hooks

---

## Требования

Перед установкой убедитесь, что у вас установлено:

- Python 3.10 или выше
- PostgreSQL 15+
- Redis 7.0+ (опционально, для кэширования)
- Git
- Инструмент для виртуального окружения (venv или virtualenv)

Для развертывания через Docker:
- Docker 20.10+
- Docker Compose 2.0+

---

## Установка

### Локальная разработка

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace
```

2. **Создайте и активируйте виртуальное окружение**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Установите зависимости**
```bash
pip install -r requirements/development.txt
```

4. **Настройте переменные окружения**
```bash
cp env.example.txt .env
# Отредактируйте .env с вашими настройками
```

5. **Создайте базу данных**
```bash
# PostgreSQL
createdb lootlink_db
```

6. **Выполните миграции**
```bash
python manage.py migrate
```

7. **Создайте суперпользователя**
```bash
python manage.py createsuperuser
```

8. **Запустите сервер разработки**
```bash
python manage.py runserver
```

Откройте `http://localhost:8000` в браузере.

### Развертывание через Docker

```bash
# Соберите и запустите контейнеры
docker-compose up -d

# Выполните миграции
docker-compose exec web python manage.py migrate

# Создайте суперпользователя
docker-compose exec web python manage.py createsuperuser

# Соберите статические файлы
docker-compose exec web python manage.py collectstatic --noinput
```

---

## Конфигурация

### Переменные окружения

Создайте файл `.env` в корне проекта со следующими переменными:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# База данных
DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis (опционально)
USE_REDIS=True
REDIS_URL=redis://localhost:6379/1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AWS S3 (опционально)
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=

# Безопасность (только для production)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

Полный список настроек смотрите в `env.example.txt`.

---

## Использование

### Панель администратора
Доступ к Django admin по адресу `http://localhost:8000/admin/` с учетными данными суперпользователя.

### Создание объявлений
1. Зарегистрируйте аккаунт или войдите
2. Перейдите в "Создать объявление"
3. Заполните детали предмета и загрузите изображение
4. Отправьте на публикацию

### Совершение покупок
1. Просматривайте объявления или используйте поиск/фильтры
2. Нажмите на предмет для просмотра деталей
3. Отправьте запрос на покупку продавцу
4. Общайтесь через встроенный чат
5. Завершите транзакцию

### Доступ к API
API endpoints доступны по адресу `/api/`. Подробности в разделе [API документация](#api-документация).

---

## Структура проекта

```
LootLink---Marketplace/
├── accounts/           # Аутентификация и профили пользователей
├── listings/           # Объявления маркетплейса и категории
├── chat/              # Система обмена сообщениями в реальном времени
├── transactions/      # Запросы на покупку и отзывы
├── payments/          # Обработка платежей (в разработке)
├── api/               # REST API endpoints
├── admin_panel/       # Кастомный интерфейс администратора
├── core/              # Общие утилиты и middleware
├── config/            # Настройки и конфигурация Django
├── static/            # Статические файлы (CSS, JS, изображения)
├── templates/         # HTML шаблоны
├── nginx/             # Конфигурационные файлы Nginx
├── scripts/           # Скрипты развертывания и утилиты
├── tests/             # Набор тестов
├── docs/              # Документация
├── requirements/      # Python зависимости
│   ├── base.txt       # Основные зависимости
│   ├── development.txt # Инструменты разработки
│   └── production.txt  # Production зависимости
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── README.md
```

### Django приложения

- **accounts**: Регистрация пользователей, аутентификация, профили, верификация
- **listings**: Объявления о предметах, категории, игры, избранное
- **chat**: Диалоги и сообщения между пользователями
- **transactions**: Запросы на покупку, история транзакций, отзывы
- **payments**: Интеграция платежей (планируется)
- **api**: RESTful API на DRF
- **admin_panel**: Расширенный интерфейс администратора
- **core**: Middleware, утилиты, уведомления

---

## API документация

REST API предоставляет программный доступ к функционалу маркетплейса.

**Базовый URL:** `https://lootlink.ru/api/`

### Аутентификация
API использует session-based аутентификацию. Включайте CSRF токен в POST запросы.

### Endpoints

```
GET    /api/listings/              # Список всех объявлений
GET    /api/listings/{id}/         # Детали объявления
POST   /api/listings/              # Создать объявление (требуется авторизация)
PUT    /api/listings/{id}/         # Обновить объявление (только владелец)
DELETE /api/listings/{id}/         # Удалить объявление (только владелец)

GET    /api/games/                 # Список игр
GET    /api/categories/            # Список категорий

GET    /api/conversations/         # Список диалогов пользователя
POST   /api/conversations/         # Создать диалог
GET    /api/messages/              # Список сообщений

GET    /api/transactions/          # Список транзакций пользователя
POST   /api/transactions/          # Создать запрос на покупку
```

Полная документация API доступна в `docs/API_DOCUMENTATION.md`.

---

## Тестирование

### Запуск тестов

```bash
# Все тесты
python manage.py test

# Конкретное приложение
python manage.py test accounts

# С покрытием кода
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Структура тестов

```
tests/
├── test_models.py
├── test_views.py
├── test_api.py
├── test_security.py
└── test_integration.py
```

### Линтеры

```bash
# Flake8
flake8 . --exclude=migrations,venv

# Black форматирование
black . --exclude="migrations|venv"

# Сортировка импортов
isort . --skip migrations --skip venv
```

---

## Развертывание

### Production чеклист

- [ ] Установить `DEBUG=False`
- [ ] Сгенерировать надежный `SECRET_KEY`
- [ ] Настроить `ALLOWED_HOSTS`
- [ ] Настроить SSL/TLS сертификаты
- [ ] Настроить production базу данных
- [ ] Настроить Redis для кэширования
- [ ] Настроить email backend
- [ ] Настроить раздачу статических файлов
- [ ] Настроить Nginx/Apache
- [ ] Настроить мониторинг (Sentry)
- [ ] Настроить автоматические бэкапы
- [ ] Настроить правила firewall

### Руководство по развертыванию

Подробные инструкции по production развертыванию смотрите в `docs/DEPLOYMENT.md`, включая:
- Настройка сервера
- Конфигурация Nginx
- SSL с Let's Encrypt
- Конфигурация Systemd сервиса
- Оптимизация базы данных
- Усиление безопасности

### Быстрое развертывание

```bash
# Используя предоставленный скрипт
bash scripts/deploy_with_smoke.sh
```

---

## Производительность

### Техники оптимизации

- **База данных**: Оптимизация запросов с `select_related` и `prefetch_related`
- **Кэширование**: Redis кэширование для часто запрашиваемых данных
- **Статические файлы**: CDN доставка и минификация
- **Изображения**: Автоматическое сжатие и оптимизация
- **Индексы**: Индексы базы данных на часто запрашиваемых полях
- **Connection Pooling**: Постоянные соединения с базой данных

### Бенчмарки

- Среднее время загрузки страницы: < 200ms
- Время ответа API: < 100ms
- Одновременные пользователи: 1000+
- Запросов к БД на страницу: < 10

---

## Безопасность

### Реализованные меры безопасности

- **CSRF защита**: Django CSRF токены на всех формах
- **SQL инъекции**: ORM-запросы предотвращают SQL инъекции
- **XSS защита**: Автоматическое экранирование шаблонов и CSP заголовки
- **Безопасность паролей**: PBKDF2 хэширование с солью
- **Безопасность сессий**: Secure, HttpOnly cookies
- **Rate Limiting**: Защита от brute-force атак на login/регистрацию
- **Верификация Email**: Требуется для активации аккаунта
- **HTTPS**: SSL/TLS шифрование в production
- **Заголовки безопасности**: X-Frame-Options, X-Content-Type-Options и др.

### Аудит безопасности

Запуск проверок безопасности:
```bash
python manage.py check --deploy
bandit -r . -x ./venv
safety check
```

---

## Участие в разработке

Мы приветствуем вклад в проект! Пожалуйста, следуйте этим шагам:

1. Сделайте Fork репозитория
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Закоммитьте ваши изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте изменения в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Рекомендации по разработке

- Следуйте PEP 8 style guide
- Пишите тесты для новых функций
- Обновляйте документацию при необходимости
- Запускайте линтеры перед коммитом
- Делайте атомарные и хорошо описанные коммиты

Подробные рекомендации смотрите в `CONTRIBUTING.md`.

---

## Лицензия

Этот проект распространяется под лицензией MIT License - подробности смотрите в файле [LICENSE](LICENSE).

---

## Контакты

**Разработчик:** Иван Петров
**Email:** ivanpetrov20066.ip@gmail.com
**Демо:** [lootlink.ru](https://lootlink.ru)
**Issues:** [GitHub Issues](https://github.com/reazonvan/LootLink---Marketplace/issues)

---

## Благодарности

- Django сообществу за отличную документацию
- Команде Bootstrap за UI фреймворк
- Всем участникам и тестировщикам

---

**[⬆ Вернуться к началу](#lootlink-marketplace)**
