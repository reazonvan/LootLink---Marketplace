# Архитектура LootLink

Описание серверной и клиентской части проекта, без маркетинговых обёрток.
Цель документа — дать новому разработчику представление о том, как устроен
код, какие у приложений границы ответственности и где искать бизнес-логику.

## Общая схема

```
Клиент (браузер)
    │ HTTPS
    ▼
Caddy        (terminate TLS, gzip, reverse proxy, auto-cert, отдача static/media)
    │
    └── HTTP+WS ──► gunicorn + uvicorn workers ──► Django (ASGI, Channels)
                       │
                       ├── PgBouncer ──► PostgreSQL 15 (FTS, GIN-индексы)
                       └── Redis 7        (cache, sessions, Channels layer,
                                          Celery broker и result backend)

Celery worker и Celery beat подключены к тому же Redis и БД
(идемпотентные задачи, retry с exponential backoff).
```

## Стек

- Python 3.13, Django 5.2, DRF, Django Channels, Celery 5.x.
- Прод-сервер: gunicorn + uvicorn workers (ASGI, обслуживает и HTTP, и
  WebSocket единым воркером). Прокси: Caddy. Dev: `runserver` (daphne для ASGI).
- БД: PostgreSQL 15 (prod), SQLite (dev по умолчанию через `DB_ENGINE=sqlite`).
- Redis 7 в четырёх ролях: cache, sessions, Celery broker, Channels layer.
- Frontend: Django templates, custom CSS (`static/css/lootlink.css`),
  vanilla JS ES6+, иконки Lucide. React не используется.

## Метрики кода (на 2026-06-01)

- ~160 Python-файлов приложения, ~24 800 строк (без `venv`, `migrations`, тестов).
- 21 модель, 70 миграций, 162 endpoint, 98 HTML-шаблонов.
- 716 тестов в pytest (716 passed, 1 skipped), 80% покрытия (`pytest --cov`).

## Структура приложений

В каждом app слои разнесены по принципу HackSoft styleguide:

- `views.py` — тонкий HTTP-слой: парсинг параметров, вызов сервиса, redirect,
  `messages.add_message`. Никакой бизнес-логики и сырых ORM-запросов.
- `services.py` — бизнес-логика и операции, меняющие состояние.
  Денежные операции — атомарно через `transaction.atomic` и
  `select_for_update()`. Внешние вызовы (email, Telegram, push) запускаются
  через `transaction.on_commit`.
- `selectors.py` — функции чтения. Здесь живут `select_related`,
  `prefetch_related`, аннотации, фильтры по правам.
- `models.py` + `signals.py` — данные, индексы, ограничения, сигналы.
- `tasks.py` — Celery: идемпотентные, с `bind=True` и `self.retry`.

### accounts

Пользователи, профили, верификация, 2FA, экспорт по 152-ФЗ, security audit.

Ключевые модели:

- `CustomUser` — переопределённый `AbstractUser`, удаление запрещено
  (мягкая деактивация через `is_active=False`).
- `Profile` — аватар, био, рейтинг, счётчики сделок, флаги верификации.
- `TOTPDevice` — 2FA через приложение-аутентификатор.
- `LoginAttempt`, `SecurityEvent` — журнал входов и подозрительной активности.

Безопасность: пароли хешируются Argon2id (`argon2-cffi`), с fallback на
PBKDF2 для старых учёток. Rate limit на `/accounts/login/` и
`/accounts/register/` — через `core.middleware`.

### listings

Каталог объявлений и игр, поиск, избранное, жалобы.

- `Game` — справочник игр с `slug` для URL.
- `Listing` — объявление с `status` (`active`/`reserved`/`sold`/`cancelled`),
  изображением (валидация размера и MIME), полем `search_vector` для
  PostgreSQL FTS и GIN-индексом по нему.
- `Favorite`, `Report` — избранное и жалобы соответственно.

Поиск — `SearchQuery(..., config='russian')` с `SearchRank`. На SQLite в dev
работает упрощённый `icontains`-fallback. Каталог использует
`select_related('seller', 'game')` и `prefetch_related('images')`,
кэширование счётчиков на 5 минут.

### chat

WebSocket-чат через Django Channels с Redis-layer.

- `Conversation` — две стороны и опциональная привязка к объявлению.
  `unique_together` написан как два условных `UniqueConstraint` (с listing
  и без), потому что `unique_together` не работает с NULL.
- `Message` — содержимое до 5000 символов, `is_read`, `created_at`.
  Композитные индексы: `(conversation, -created_at)` и
  `(conversation, is_read, sender)`.

Подключение клиента — `chat/consumers.py`. Аутентификация через сессионный
cookie. CSRF-токен передаётся через `<meta name="csrf-token">` или header,
потому что `CSRF_COOKIE_HTTPONLY=True`.

### transactions

Запросы на покупку, отзывы, диспуты.

- `PurchaseRequest` — конечный автомат: `pending → accepted → completed`
  (или `rejected`/`cancelled`). `unique_together = (listing, buyer)`.
- `Review` — оценка 1–5, `unique_together = (purchase_request, reviewer)`,
  пересчёт `Profile.rating` через сигнал.
- `Dispute` — открывается, если стороны не пришли к завершению.

Жизненный цикл сделки контролируется `transactions/services.py`. Любое
изменение `Listing.status` идёт через сервис, а не из view.

### payments

Кошелёк, эскроу, выводы, интеграция с ЮKassa.

- `Wallet` — баланс пользователя. На уровне БД действуют `CheckConstraint`:
  `wallet_balance_non_negative` и `wallet_frozen_consistent`
  (`frozen_balance ∈ [0, balance]`). В админке поля `balance` и
  `frozen_balance` readonly, ручное изменение запрещено.
- `Transaction` — атомарные операции пополнения, заморозки, списания.
- `Escrow` — депонирование. Меняется только через сервис с
  `select_for_update`. Авто-релиз по дедлайну делает Celery beat.
- `Withdrawal` — заявки на вывод; обрабатывает админ-очередь.

### api

REST API на DRF. Session-based auth + CSRF. Throttling через
`UserRateThrottle` и `AnonRateThrottle`. Сериализаторы тонкие, основная
логика — в `services.py` соответствующих app.

### admin_panel

Кастомная админка для модерации, отдельная от `/admin/`. Дашборд с
очередями (объявления, жалобы, диспуты, выводы), фильтры, массовые действия.

### core

Уведомления, middleware, audit log по 152-ФЗ, telegram-bot, email-утилиты.

- `Notification` — типизированные уведомления, индекс
  `(user, is_read, -created_at)` для запроса бейджа.
- `AuditLog` — записи аудита. Удалять записи нельзя.
- `BruteForceProtectionMiddleware`, `SecurityHeadersMiddleware`,
  `RateLimitMiddleware` — глобальные защиты.

### config

`settings.py`, `urls.py`, `asgi.py`, `wsgi.py`, `celery.py`.
ASGI-приложение оборачивает Channels-router.

## База данных

### Связи (упрощённо)

```
CustomUser ─1:1─ Profile
   │
   ├─1:N─ Listing ─1:N─ PurchaseRequest ─1:N─ Review
   │         └─1:N─ Favorite
   │
   ├─1:N─ Conversation ─1:N─ Message
   ├─1:1─ Wallet ─1:N─ Transaction
   ├─1:N─ Escrow (как buyer и как seller)
   ├─1:N─ Withdrawal
   └─1:N─ Notification
```

### Композитные индексы под горячие запросы

- `Message`: `(conversation, -created_at)`, `(conversation, is_read, sender)`.
- `Conversation`: `(participant1, -updated_at)`, `(participant2, -updated_at)`.
- `Notification`: `(user, is_read, -created_at)`.
- `Listing`: `(seller, status, -created_at)`, `(game, category, status)`,
  GIN по `search_vector`.
- `Escrow`: `(status, release_deadline)`, `(buyer, -created_at)`,
  `(seller, -created_at)`.
- `Withdrawal`: `(status, -created_at)`, `(user, -created_at)`.
- `Transaction`: `(user, transaction_type, -created_at)`.

### Ограничения целостности

```
Wallet:           balance >= 0
                  frozen_balance >= 0
                  frozen_balance <= balance
Conversation:     UniqueConstraint(p1, p2, listing) WHERE listing IS NOT NULL
                  UniqueConstraint(p1, p2)          WHERE listing IS NULL
PurchaseRequest:  UniqueConstraint(listing, buyer)
Review:           UniqueConstraint(purchase_request, reviewer)
Favorite:         UniqueConstraint(user, listing)
```

## Поток сделки

```
1. Покупатель открывает Listing и нажимает «Купить».
2. POST /transactions/purchase-request/<listing_id>/create/
   ↓ transactions.views.purchase_request_create
   ↓ transactions.services.create_purchase_request
3. Сервис в одной транзакции:
     - проверяет права и доступность listing
     - создаёт PurchaseRequest(status=pending)
     - блокирует средства покупателя в Wallet (frozen_balance)
     - создаёт Escrow со статусом pending
4. on_commit: уведомление продавца (Notification + email + telegram).
5. Продавец принимает → status=accepted, listing.status=reserved.
6. Передача предмета и подтверждение покупателя:
     status=completed, listing.status=sold
     Escrow.release: средства уходят продавцу, frozen_balance снимается.
7. Стороны оставляют Review, Profile.rating пересчитывается сигналом.
```

## Безопасность

- CSRF: `{% csrf_token %}` на всех POST. AJAX берёт токен из
  `<meta name="csrf-token">`. Cookie `httponly`.
- XSS: автоэкранирование шаблонов; пользовательский ввод в JS пропускается
  через `escapeHtml`. Inline-обработчики в шаблонах не используются.
- SQL: только ORM. Сырых запросов в репозитории нет.
- Rate limit: `accounts:login` 5/5 мин, `accounts:register` 3/10 мин,
  `listings:listing_create` 10/час.
- CSP, HSTS, `Referrer-Policy`, `X-Content-Type-Options` настроены в
  `core.middleware.SecurityHeadersMiddleware`.
- Загрузка файлов: размер до 5 МБ, проверка MIME через `imghdr`,
  расширение whitelist (`jpeg`, `png`, `webp`, `gif`).
- 152-ФЗ: согласие на обработку, экспорт данных в ZIP, журнал доступа
  к ПДн в `core.AuditLog`.

## Производительность

- Везде, где это уместно, `select_related` для FK и `prefetch_related`
  для обратных и M2M связей.
- Пагинация — Django `Paginator`, по умолчанию 12 элементов на страницу.
- Кэш в Redis с явными TTL: статистика главной — 5 минут, список игр —
  1 час, счётчик уведомлений на пользователя — 1 минута.
- PostgreSQL FTS с русским словарём для каталога. На SQLite — `icontains`.
- Тяжёлые операции (email, миниатюры, рассылка push, очистка истории)
  делегированы Celery.

## Шаблоны и фронтенд

```
templates/
├── base.html                   общий layout
├── 404.html, 500.html
├── accounts/                   регистрация, логин, профиль, 2FA, KYC
├── chat/                       список диалогов и чат
├── core/                       уведомления, FAQ, модерация
├── emails/                     текстовые email-шаблоны
├── listings/                   landing, каталог, детальная, создание
├── pages/                      about, faq, rules
├── payments/                   кошелёк, эскроу, выводы
└── transactions/               запросы на покупку, отзывы, диспуты
```

CSS — один файл `static/css/lootlink.css`, mobile-first, design tokens
через CSS-переменные в `:root`. Тёмная и светлая темы переключаются через
`data-theme` на `<html>`.

JS — модули в `static/js/`, без сборщика. Загружаются с `defer`. Прогрессив
енхансмент: страница работает без JS, скрипты добавляют интерактивность
(чат-консьюмер, автокомплит поиска, галерея, кропер аватара, push).

## Конфигурация окружения

`config/settings.py` читает значения из `.env` через `django-environ`.
Ключевые переменные:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`.
- `DB_ENGINE` (`postgres` или `sqlite`), `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
  `DB_HOST`, `DB_PORT`.
- `REDIS_URL`, `USE_REDIS`. В production `USE_REDIS=False` выдаёт
  `RuntimeWarning` — это намеренно, иначе rate limit становится фиктивным.
- `ADMIN_URL` — путь к стандартной Django-админке. В prod подменяется на
  непредсказуемую строку, чтобы автосканеры не находили `/admin/`.
- `SENTRY_DSN`, `YOOKASSA_*`, `TELEGRAM_BOT_TOKEN`, `VAPID_*`.

## Деплой

Прод — Docker compose. Публичный вход только через Caddy; `web` слушает
`:8000` внутри сети. Сервисы:

- `caddy` — reverse proxy, auto-TLS, отдача static/media, www→apex 308.
- `web` — Django под gunicorn + uvicorn workers (HTTP + WebSocket).
- `migrator` — однократный init: `migrate` напрямую в `db`, затем выходит.
- `pgbouncer` — пул соединений (transaction-mode) перед Postgres.
- `db` — PostgreSQL 15.
- `redis` — Redis 7.
- `celery_worker`, `celery_beat` — фоновые и периодические задачи.
- `flower` — мониторинг Celery (`/flower/`).

Первый запуск — `deployment/pre-deploy-checklist.md`, выкат обновлений и откат —
`deployment.md` (раздел «Обновление»). Скрипт `scripts/deploy_with_smoke.sh`
делает выкат и триггерит smoke-тесты
через `repository_dispatch` на GitHub Actions.

## Логирование и мониторинг

- Sentry с request-id трассировкой и Django-интеграцией.
- `/metrics/` — django-prometheus (latency, БД/кэш-запросы, 5xx), авторизация
  по Bearer-токену (`METRICS_TOKEN`); снаружи закрыт Caddy.
- Health-пробы: `/health/live/` (liveness) и `/health/ready/` (БД + кэш).
- Логи Django пишутся в `logs/`: `lootlink.log` (INFO+), `errors.log`
  (ERROR+), `security.log` (WARNING+ из `django.security`); verbose-копия
  в stdout для docker/loki.
- Метрики, за которыми смотрим: время отклика (p50/p95/p99), доля 5xx,
  длина очереди Celery, hit rate Redis, число активных WebSocket-соединений.

## Архитектурные решения

ADR (Architecture Decision Records) хранятся в `.planning/adr/` по мере
накопления. Существующие решения, зафиксированные неформально:

- PostgreSQL вместо MongoDB — нужны транзакции и строгие constraint.
- Channels вместо отдельного WS-сервера — единый код-база и сессии.
- Custom CSS вместо Tailwind/Bootstrap — уникальная типографика и темизация
  без класс-инфляции в шаблонах.
- Без React SPA — Django templates с прогрессивным enhancement дешевле
  поддерживать и индексируются поисковиками без SSR.
