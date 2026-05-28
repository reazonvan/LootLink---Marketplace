# LootLink Marketplace

P2P маркетплейс для торговли внутриигровыми предметами с депонированием средств, WebSocket-чатом и соответствием 152-ФЗ.

[![Live Demo](https://img.shields.io/badge/demo-lootlink.ru-blue)](https://lootlink.ru)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**Демо:** [lootlink.ru](https://lootlink.ru)

## Что это

Веб-приложение для прямой торговли игровыми предметами между игроками. Платформа объединяет:

- **Эскроу-сделки** с атомарным депонированием через `SELECT FOR UPDATE`
- **2FA** (TOTP) и KYC через документы
- **Audit log** по требованиям 152-ФЗ и ФСТЭК-21
- **WebSocket-чат** в реальном времени через Django Channels
- **REST API** с throttling и permissions (DRF)
- **Полнотекстовый поиск** с русской морфологией (PostgreSQL FTS)

## Стек

- **Backend:** Python 3.13, Django 5.2, DRF, Celery, Channels (WebSockets)
- **БД:** PostgreSQL 15 (FTS, GIN-индекс), SQLite (dev fallback)
- **Кэш/брокер:** Redis 7 (cache, sessions, Celery, Channels)
- **Frontend:** Django templates, custom CSS (lootlink.css), vanilla JS ES6+, Lucide Icons
- **Деплой:** Docker, Caddy (auto-TLS), Daphne (ASGI), Gunicorn (WSGI), Systemd
- **Безопасность:** Argon2id, 2FA TOTP, BruteForceProtection, audit log
- **Мониторинг:** Sentry с request-id трассировкой
- **CI/CD:** GitHub Actions (lint + test + bandit + smoke)

## Установка

```bash
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements/development.txt
cp .env.example .env         # отредактировать
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Через Docker:
```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Конфигурация

Скопируйте `.env.example` в `.env` и заполните:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=your-password
REDIS_URL=redis://localhost:6379/1
```

Полный список переменных — в `.env.example`.

## Структура (HackSoft styleguide)

```
accounts/        — Пользователи, профили, 2FA, KYC, security audit
listings/        — Объявления, категории, игры, поиск (FTS), избранное
chat/            — WebSocket-чат через Django Channels
transactions/    — Сделки, отзывы, диспуты
payments/        — Кошелёк, эскроу, YooKassa, выводы
api/             — REST API (DRF) с throttling
admin_panel/     — Кастомная админка с модерацией
core/            — Уведомления, middleware, audit log, telegram, email
config/          — Settings, urls, ASGI/WSGI, Celery
```

**Слоистая архитектура** в каждом app:
- `views.py` — тонкий HTTP-слой (валидация форм, redirect, messages)
- `services.py` — бизнес-логика (атомарные операции, side-effects через `transaction.on_commit`)
- `selectors.py` — запросы к БД (`select_related`, `prefetch_related`)
- `models.py` + `signals.py` — данные и сигналы
- `tasks.py` — Celery-задачи (идемпотентные, с retry)

**Метрики кода (28.05.2026):**
- ~265 Python-файлов, ~1.5 МБ исходников
- ~88 моделей, ~53 миграции
- HTML-шаблоны Django + custom CSS

## API

```
GET    /api/listings/          — все объявления
GET    /api/listings/{id}/     — детали
POST   /api/listings/          — создать (auth)
GET    /api/games/             — список игр
GET    /api/conversations/     — диалоги
GET    /api/transactions/      — сделки
```

Session-based аутентификация + CSRF.

## Тесты

```bash
pytest                                   # все тесты
pytest --cov=. --cov-report=html         # с отчётом о покрытии
pytest -m "not slow"                     # быстрые тесты
pytest payments/                         # тесты конкретного app
```

**Состояние покрытия (28.05.2026):**
- Общее покрытие: ~21% — низкое, есть план по доращиванию
- Слабее всего: `admin_panel` (1%), `api` (13%), `core` (14%)
- Лучше: `config` (64%), `chat`/`listings`/`payments` (22-26%)
- Mock'и для внешних API (YooKassa, Telegram, push)
- Фикстуры в `conftest.py` — `verified_user`, `seller`, `buyer`, `listing_factory` и др.

## Деплой

```bash
bash scripts/deploy_with_smoke.sh
```

Подробности в `docs/DEPLOYMENT.md`.

## Вклад в проект

См. [CONTRIBUTING.md](CONTRIBUTING.md) — гайд для разработчиков.

## Безопасность

Нашли уязвимость? См. [SECURITY.md](SECURITY.md) — как сообщить приватно.

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Контакты

Вопросы и баг-репорты — через [GitHub Issues](https://github.com/reazonvan/LootLink---Marketplace/issues).
