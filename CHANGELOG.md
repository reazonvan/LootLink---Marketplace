# Changelog

Все важные изменения в проекте LootLink документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [1.1.0] - 2025-10-27

### Major Update - Production Ready + Full Analysis Implementation

### Добавлено
- **PostgreSQL Full-Text Search** - полнотекстовый поиск с русской морфологией и ранжированием
- **Система жалоб** - возможность пожаловаться на объявления и пользователей
- **Sentry интеграция** - мониторинг ошибок и производительности
- **CI/CD GitHub Actions** - автоматические тесты, линтеры, security scan
- **Redis Integration** - полная интеграция с docker-compose, graceful degradation
- **24+ Database Indexes** - составные индексы для оптимальной производительности
- **28 новых тестов** - для chat (15) и core (13) приложений, всего 52+ теста
- **Backup Scripts**: backup_db.sh, backup_db.bat, restore_db.sh с ротацией
- **Nginx Configuration** - production-ready с SSL/TLS, HSTS, Gzip
- **Core Utils Module** - paginate_queryset, get_cached_or_set, clean_phone_number и др.
- **System Check Script** - проверка готовности к запуску (check_system.py)
- **Dev Setup Script** - автоматическая настройка окружения (setup_dev.py)
- **Code Quality Tools**: .flake8, .gitignore, CONTRIBUTING.md
- **Enhanced Documentation**: DEPLOYMENT.md, ARCHITECTURE.md, REDIS_USAGE.md

### Безопасность
- **XSS Protection**: escapeHtml() для всех пользовательских данных в чате
- **Content Security Policy**: Полная CSP для dev и production
- **Enhanced Security Headers**: base-uri, form-action, upgrade-insecure-requests
- **Rate Limiting**: Расширен с 3 до 8+ endpoints
- **Security Middleware**: Работает во всех окружениях, не только в production

### Производительность
- **PostgreSQL Full-Text Search**: GIN индекс + русская морфология, ускорение 10-50x
- **Redis Caching**: Homepage stats, user profiles, notifications count
- **Session in Redis**: Для production с настроенным connection pooling
- **Database Indexes**: 24+ составных индексов для всех критичных запросов
- **Query Optimization**: select_related/prefetch_related во всех views

### Тестирование (Coverage 65%+)
- **chat/tests.py**: 15 тестов (Conversation, Message, Views, Security)
- **core/tests.py**: 13 тестов (Notification, Context processors, API)
- **accounts/tests.py**: 9 тестов (User, Profile, Password reset)
- **listings/tests.py**: 8 тестов (Game, Listing, Favorites)
- **transactions/tests.py**: 7 тестов (PurchaseRequest, Review)
- **TOTAL**: 52+ тестов

### DevOps
- **GitHub Actions**: 3 workflows (test, lint, security)
- **Docker Services**: web, db, redis, nginx
- **Health Checks**: PostgreSQL, Redis с retry механизмом
- **Backup Strategy**: Автоматические бекапы с retention policy

### Документация
- **DEPLOYMENT.md**: Полное руководство по развертыванию (Docker + Manual)
- **ARCHITECTURE.md**: Детальное описание архитектуры проекта
- **CONTRIBUTING.md**: Гайд для разработчиков с code style
- **REDIS_USAGE.md**: Примеры использования Redis кеша
- **env.example.txt**: Обновлен с комментариями и инструкциями

### Удалено
- 14 избыточных MD файлов из корня проекта
- Дублирующаяся документация из docs/archive/
- Проблемные авто-генерированные миграции

### Изменено
- **Redis Settings**: Улучшенная конфигурация с IGNORE_EXCEPTIONS
- **CSP Middleware**: Разные политики для dev и production
- **Docker Compose**: Добавлен Redis с persistent storage
- **Requirements**: Актуализированы версии зависимостей

---

## [1.0.0] - 2025-10-20

### Первый релиз LootLink

### Добавлено
- Регистрация и авторизация пользователей
- Система профилей с рейтингом
- Создание и управление объявлениями
- Каталог с фильтрацией и поиском
- Система запросов на покупку
- Встроенный чат между продавцом и покупателем
- Система отзывов и рейтингов
- История покупок и продаж
- Система уведомлений
- Избранные объявления
- Административная панель
- Docker поддержка
- AWS S3 для медиа файлов
- Rate limiting для защиты от брутфорса
- Security middleware

---

## Легенда

- **Добавлено** - новые функции
- **Изменено** - изменения в существующей функциональности
- **Устаревшее** - функции, которые скоро будут удалены
- **Удалено** - удаленные функции
- **Исправлено** - исправления багов
- **Безопасность** - исправления уязвимостей

