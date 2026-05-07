# Changelog

Все важные изменения в проекте LootLink документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [1.3.0] - 2026-05-08

### Major Update — Phase 9-14: hardening, целостность данных, оптимизация

### Безопасность (Phase 10)
- **Argon2id** для хеширования паролей (соответствие нефункциональному
  требованию диплома 1.3, рекомендация OWASP). Старые PBKDF2-хеши работают
  через fallback. `requirements/base.txt` + `argon2-cffi>=23.1.0`.
- **Кастомный путь админки** через `ADMIN_URL` env (защита от автоматических
  сканеров). По умолчанию `admin/` для dev, в prod — непредсказуемая строка.
- **`CSRF_COOKIE_HTTPONLY=True`** — защита от XSS-кражи CSRF-токена.
  WebSocket-клиент берёт токен из `<meta name="csrf-token">` или header.
- **`DATA_UPLOAD_MAX_NUMBER_FIELDS=1000`** — защита от DoS через хеш-коллизии.
- **`USE_REDIS=False` в production выдаёт RuntimeWarning** — предотвращает
  фиктивный rate-limit при многих воркерах Daphne.
- **Удалён `X-XSS-Protection` header** (deprecated, может включать уязвимости
  в IE/старом Safari). Защита от XSS — через CSP и escape в шаблонах.
- **`Wallet.balance/frozen_balance` readonly в админке** — финансы только
  через `Transaction`/`Escrow` (атомарно, с audit log).
- **`Wallet.has_add_permission/has_delete_permission = False`** — кошелёк
  создаётся только сигналом, удалить нельзя.

### Целостность данных (Phase 11)
- **Удалено мёртвое поле `Profile.balance`** — единый источник истины
  для финансов теперь `payments.Wallet.balance` (через миграцию
  `accounts.0020_remove_profile_balance`).
- **БД-уровневые `CheckConstraint` на Wallet:**
  `wallet_balance_non_negative` и `wallet_frozen_consistent`
  (frozen в `[0, balance]`). Защита от багов в коде, нарушающих
  целостность финансов.
- **Условные `UniqueConstraint` для Conversation** вместо `unique_together` —
  `unique_together` не работает с `NULL`, поэтому два constraint:
  один с listing, один без.

### Производительность БД (Phase 11)
Добавлены композитные индексы под горячие запросы:
- `chat.Message`: `(conversation, -created_at)`, `(conversation, is_read, sender)`
  — ранее у Message не было ни одного индекса.
- `chat.Conversation`: `(participant1, -updated_at)`, `(participant2, -updated_at)`
  — список бесед пользователя.
- `core.Notification`: `(user, is_read, -created_at)` — главный запрос badge.
- `listings.Listing`: `(seller, status, -created_at)`, `(game, category, status)`
  — каталог и профиль продавца.
- `payments.Escrow`: `(status, release_deadline)`, `(buyer, -created_at)`,
  `(seller, -created_at)` — auto_release_escrow и история.
- `payments.Withdrawal`: `(status, -created_at)`, `(user, -created_at)`
  — админ-очередь и история.
- `payments.Transaction`: `(user, transaction_type, -created_at)`
  — фильтр истории по типу.

### Frontend (Phase 14)
- **`alt`-теги** добавлены на все `<img>` в payments/transactions
  (раньше 3 без alt — `escrow_detail.html`, `purchase_request_create.html`,
  `purchase_request_detail.html`).
- **`loading="lazy"`** на listing-thumbnails в тех же шаблонах.
- **`favorites.js` icon-fix** — раньше переключал `bi-heart`/`bi-heart-fill`
  (Bootstrap Icons) на Lucide-проекте, иконка не менялась.
  Теперь через CSS-класс `.active` (см. `.favorite-btn-detail.active` в lootlink.css).

### Чистка репозитория (Phase 9)
- Удалены лишние виртуальные окружения (`.venv`, `.venv-codex`,
  `.venv-dev`, `.venv-local`) — оставлен один `venv/`.
- Удалены AI/IDE-артефакты: `.agents/`, `.kilo/`, `.serena/`, `.obsidian/`,
  `.cursor/`, `.playwright-mcp/`, `LootLink/`, `__pycache__/` в корне.
- Удалены кэши: `.coverage`, `htmlcov/`, `.pytest_cache/`.
- Очищены логи (770 КБ): `errors.log`, `lootlink.log`, `security.log`.
- Удалены распакованные ZIP-бинарники (Redis 12 МБ, GitHub MCP 7 МБ).
- В `.gitignore` добавлены: `tools/` (целиком), `diploma_text.txt`.

### Метрики
- Тесты: **388 passed, 1 skipped** (без изменений после рефакторинга).
- Coverage: **66%** (база для Phase 15).
- Python LOC: 52 540 в 339 файлах (без venv/migrations).
- Миграций добавлено: 5 (accounts, core, listings, chat, payments).

---

## [1.2.0] - 2026-04-17

### Major Update — антифрод, модерация, production-стабилизация

### Добавлено
- **Антифрод и диспуты** — система обнаружения подозрительных сделок, логи входов,
  инструменты для модераторов по разрешению споров.
- **Healthcheck и SEO** — эндпоинты здоровья, канонические URL, редиректы,
  PostgreSQL full-text search.
- **Post-deploy smoke** — workflow с Playwright для проверки продакшена после деплоя,
  включая авторизованные пользовательские сценарии.
- **Скрипт деплоя одной командой** — `scripts/deploy_with_smoke.sh` с автоматическим
  триггером smoke-проверок через `repository_dispatch`.
- **Страница настроек аккаунта** — управление профилем и предпочтениями.
- **Изображения в чате** — загрузка и отображение картинок в диалогах.
- **Система анимаций появления** — на 9 ключевых страницах.
- **Автоматический TLS в Caddy** — без ручного управления сертификатами.
- **django-celery-beat** — планировщик периодических задач.
- **Dependabot, SECURITY.md, CODE_OF_CONDUCT.md, шаблоны issue/PR** — приведено
  к стандартам community health.

### Безопасность
- Устранены критические уязвимости, найденные в глубоком аудите бэкенда и фронтенда.
- Усилена серверная конфигурация: заголовки, лимиты, валидация.
- Улучшена доступность и безопасность фронтенда (CSP, XSS-защита).

### Изменено
- **Единая дизайн-система LootLink** — полная переработка визуального языка.
- **Каталог** — несколько итераций редизайна (Cyberpunk Arcade → Channel Shelf → glassmorphism).
- **Адаптивность** — полная переработка мобильной вёрстки и полноэкранного меню.
- **Авторизация** — сохранение `next`, вход по email, корректные алерты.
- **Редирект 308** на канонический www-хост с сохранением POST.
- **Счётчики платформы** унифицированы между главной и страницей входа.
- **Серверные улучшения** — кеширование, мониторинг, email, polling.
- **Совместимость с Django 5.x** — `CheckConstraint`, устаревшие API.

### Исправлено
- QA-багфикс: поиск, профили, CSP, мобильная вёрстка, FAQ.
- Фейковая статистика удалена, `views_count` считается корректно.
- Адаптивная раскладка уведомлений для мобильных и планшетов.
- Недостающие CSS-стили страницы кошелька.
- Роутинг Flower (удалён `strip_prefix`, обрабатывается `url_prefix`).
- Скрыт декоративный элемент `orb3` на мобильных.
- Импорты модели `Report`.

### CI / инфраструктура
- Удалён дублирующий workflow `django.yml` (задачи перекрывались `ci-cd.yml`).
- `ci-cd.yml` обновлён до `actions/checkout@v5`, `setup-python@v6`, `upload-artifact@v4`,
  `codecov-action@v5` — старые v3-действия, снятые с поддержки 30.01.2025, убраны.
- Job деплоя вынесен на ручной процесс, чтобы убрать нерабочий плейсхолдер пути.

### Документация
- README приведён в соответствие с реальными версиями Python 3.11+ и Django 5.2.
- Добавлены `LICENSE` (MIT), `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- CONTRIBUTING обновлён: корректное имя репозитория, пути, ссылки на Issues и SECURITY.
- `.env.example` вместо нестандартного `env.example.txt`.

### Удалено
- Повторяющиеся и мусорные файлы из корня проекта (отчёты, дубликаты).
- Устаревшие ссылки в документации.

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

