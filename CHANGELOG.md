# Changelog

Все важные изменения в проекте LootLink документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [1.4.0] - 2026-06-01

### Production-readiness, безопасность, наблюдаемость, покрытие тестами

### Безопасность
- **88 P0–P3 фиксов** по итогам глубокого security-аудита (escrow, авторизация,
  IDOR, секреты, валидация). Подробности применения — в `DEPLOY_NOW.md`.
- **Шифрование `Withdrawal.payment_details`** через Fernet (`PAYMENT_DETAILS_KEY`).
  В админке видна только маска `**** 1234` (P0-4, PCI-DSS).
- **HMAC-верификация webhook ЮKassa** (`YOOKASSA_WEBHOOK_SECRET`, P0-3).
- **Комиссия платформы** (`PLATFORM_COMMISSION_PERCENT`) удерживается с продавца
  при release эскроу (P0-11).
- **Завершение сделки только покупателем** (`confirm_received`) или авто-release
  по дедлайну — продавец больше не финализирует сделку в одностороннем порядке.
- **Приватный storage** для KYC/dispute-evidence (`media_private`) — раздача
  только через Django serve view с проверкой прав, в обход Caddy (P0-17).
- **Доверие `X-Forwarded-For` только от `TRUSTED_PROXIES`** (P0-14).
- **2FA обязательна для staff** на критических действиях (ban_user,
  delete_listing, cancel_transaction, resolve_dispute).
- **`production.py` валит старт** при `ADMIN_URL=admin/` или `USE_REDIS=False`.

### Инфраструктура
- **PgBouncer** — пул соединений (transaction-mode) перед Postgres: десятки
  воркеров работают через ~25 реальных коннектов.
- **Сервис `migrator`** — однократный init, применяет миграции напрямую в `db`
  (не через pgbouncer); `web`/`celery` ждут его завершения. Убирает race
  condition при нескольких репликах.
- **gunicorn + uvicorn workers** (ASGI) вместо раздельных Daphne/Gunicorn —
  один тип воркера обслуживает HTTP и WebSocket. `collectstatic` вынесен
  в build образа.
- **Сессии `cached_db`**, `ManifestStaticFilesStorage` (cache-busting),
  verbose-логи в stdout для docker/loki.

### Наблюдаемость
- **`/metrics/`** — django-prometheus с авторизацией по Bearer-токену
  (`METRICS_TOKEN`), снаружи закрыт Caddy.
- **Гранулярные health-проверки**: `/health/live/` (liveness) и `/health/ready/`
  (БД + кэш) — для k8s/docker probes.
- **Покрывающее логирование** во всех приложениях (api, accounts, listings,
  transactions, chat, payments, core, admin_panel) с request-id трассировкой.

### Добавлено
- **Импорт каталога FunPay** — игры и таксономия категорий.
- **Курируемые фильтры** для топовых игр в каталоге.
- **Нагрузочные сценарии Locust** (`tests/locust/`).

### Производительность
- **Каталог: HTML 1.55 МБ → ~200 КБ**, FCP −65%.
- **Кэш каталога игр в Redis** + прогрев через Celery beat (каждые 4 минуты).

### Тестирование
- Масштабный пасс по слоям services/selectors/tasks/consumers, GDPR-экспорт,
  автомодерация, image optimization, SMS.ru, WebSocket-консьюмеры через
  `WebsocketCommunicator`.
- Тестовые настройки самодостаточны: `InMemoryChannelLayer`, eager Celery,
  SQLite, in-memory cache — Redis для тестов не нужен.

### Исправлено
- `Decimal * float` TypeError в антифрод-проверке подозрительной цены.
- Sitemap: `order_by('pk')` на пагинированных queryset'ах.
- Ремонт сломанного дашборда аналитики, hardening-фиксы аудита.

### DevOps
- `scripts/deploy_p0_fixes.sh` — идемпотентный деплой P0-фиксов.
- `PRE_DEPLOY_CHECKLIST.md`, `DEPLOY_NOW.md` — процедуры первого запуска и выката.
- Docker-compose: сервисы `pgbouncer`, `migrator`, `flower`; `web` слушает
  только внутри сети, наружу — только Caddy.
- pre-commit: pydocstyle переведён в defect-only режим.

### Документация
- `docs/DEPLOYMENT.md` переписан под реальный стек (Docker + Caddy + pgbouncer),
  убраны устаревшие nginx/certbot/systemd-инструкции.
- Актуализированы README, ARCHITECTURE, API_DOCUMENTATION, TESTING_GUIDE,
  quickstart и чеклисты; метрики приведены к фактическим значениям.

### Метрики
- 21 модель, 70 миграций, 162 endpoint, 98 HTML-шаблонов.
- ~160 Python-файлов приложения (~24 800 строк, без миграций/тестов).
- Тесты: **716 passed, 1 skipped**, покрытие **80%** (`pytest --cov`).

---

## [1.3.0] - 2026-05-08

### Безопасность, целостность данных, индексы

### Безопасность
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

### Целостность данных
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

### Производительность БД
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

### Интерфейс
- **`alt`-теги** добавлены на все `<img>` в payments/transactions
  (раньше 3 без alt — `escrow_detail.html`, `purchase_request_create.html`,
  `purchase_request_detail.html`).
- **`loading="lazy"`** на listing-thumbnails в тех же шаблонах.
- **`favorites.js` icon-fix** — раньше переключал `bi-heart`/`bi-heart-fill`
  (Bootstrap Icons) на Lucide-проекте, иконка не менялась.
  Теперь через CSS-класс `.active` (см. `.favorite-btn-detail.active` в lootlink.css).

### Чистка репозитория
- Удалены лишние виртуальные окружения (`.venv`, `.venv-codex`,
  `.venv-dev`, `.venv-local`) — оставлен один `venv/`.
- Удалены лишние локальные конфиги редакторов и временные `__pycache__/`
  в корне репозитория.
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

### Антифрод, модерация, стабилизация production

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

### Переход в production-режим

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

### Тестирование (покрытие ~65%)
- `chat/tests.py`: 15 тестов (Conversation, Message, views, security)
- `core/tests.py`: 13 тестов (Notification, context processors, API)
- `accounts/tests.py`: 9 тестов (User, Profile, password reset)
- `listings/tests.py`: 8 тестов (Game, Listing, Favorites)
- `transactions/tests.py`: 7 тестов (PurchaseRequest, Review)
- всего около 52 тестов

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

### Первый публичный релиз

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
