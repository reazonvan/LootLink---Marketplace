# LootLink Marketplace

P2P-маркетплейс для торговли внутриигровыми предметами: эскроу-сделки с депонированием средств, WebSocket-чат и соответствие 152-ФЗ.

[![Live Demo](https://img.shields.io/badge/demo-lootlink.ru-blue)](https://lootlink.ru)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![Tests](https://img.shields.io/badge/tests-716%20passed-brightgreen.svg)](#тестирование)
[![Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](#тестирование)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**Демо:** [lootlink.ru](https://lootlink.ru)

---

## Содержание

- [Что это](#что-это)
- [Возможности](#возможности)
- [Стек](#стек)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Структура проекта](#структура-проекта)
- [Метрики кода](#метрики-кода)
- [API](#api)
- [Тестирование](#тестирование)
- [Документация](#документация)
- [Деплой](#деплой)
- [Вклад, безопасность, лицензия](#вклад-в-проект)

## Что это

Веб-приложение для прямой торговли игровыми предметами между игроками, с упором на безопасность сделки. Продавец выставляет объявление, покупатель оплачивает, деньги замораживаются в эскроу и уходят продавцу только после подтверждения получения. Спорные ситуации разбираются через диспуты с участием модератора.

## Возможности

**Сделки и платежи**
- Эскроу с атомарным депонированием через `SELECT FOR UPDATE` — двойного списания не случится даже при гонке запросов.
- Авто-release эскроу по дедлайну (Celery beat), если покупатель не подтвердил и не открыл спор.
- Кошелёк, вывод средств, интеграция с YooKassa, удержание комиссии платформы.
- Реквизиты выводов шифруются в БД через Fernet — в админке видна только маска карты.

**Безопасность**
- Argon2id для паролей, 2FA по TOTP (обязательна для критичных admin-действий).
- KYC через загрузку документов, верификация телефона и email.
- BruteForceProtection, rate limiting, audit log по требованиям 152-ФЗ и ФСТЭК-21.

**Общение и поиск**
- WebSocket-чат в реальном времени через Django Channels.
- Полнотекстовый поиск с русской морфологией (PostgreSQL FTS, `SearchVector` с `config='russian'`).
- Уведомления: на сайте, email, Telegram, браузерные web-push.

**Интерфейсы**
- REST API (DRF) с токен/сессионной авторизацией, throttling и пагинацией.
- Кастомная админ-панель с модерацией объявлений, разрешением споров и графиками — отдельно от Django Admin.

## Стек

| Слой | Технологии |
|------|-----------|
| **Backend** | Python 3.13, Django 5.2, Django REST Framework, Celery, Channels (ASGI/WebSocket) |
| **БД** | PostgreSQL 15 (FTS, GIN-индексы), SQLite — fallback для разработки |
| **Кэш/брокер** | Redis 7 (cache, sessions, Celery, Channels layer) |
| **Frontend** | Django templates, custom CSS (`lootlink.css`), vanilla JS ES6+, Lucide Icons |
| **Деплой** | Docker Compose, Caddy (auto-TLS), gunicorn + uvicorn workers, PgBouncer |
| **Безопасность** | Argon2id, 2FA TOTP (django-otp), Fernet, BruteForceProtection, audit log |
| **Мониторинг** | Sentry (request-id), Prometheus `/metrics`, health-пробы, Flower |
| **CI/CD** | GitHub Actions: black, isort, flake8, bandit, pytest, post-deploy smoke |

## Быстрый старт

Самый быстрый путь — на SQLite, без PostgreSQL и Redis:

```bash
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements/development.txt
cp .env.example .env           # отредактировать (см. ниже)

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Открыть <http://127.0.0.1:8000/>. Подробнее — [docs/setup/quickstart.md](docs/setup/quickstart.md), для Windows — [docs/setup/windows.md](docs/setup/windows.md).

Через Docker (весь стек с PostgreSQL, Redis, Caddy):

```bash
docker compose up -d
docker compose exec web python manage.py createsuperuser
```

## Конфигурация

Скопируйте `.env.example` в `.env`. Минимум для локального запуска на SQLite:

```env
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=dev-insecure-key-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=sqlite
USE_REDIS=False
```

Для PostgreSQL и Redis заполните `DB_NAME`/`DB_USER`/`DB_PASSWORD` и `REDIS_URL`. Полный список из 55 переменных с комментариями — в [`.env.example`](.env.example), боевые настройки — в [docs/deployment.md](docs/deployment.md).

## Структура проекта

Раскладка по приложениям (стиль [HackSoft styleguide](https://github.com/HackSoftware/Django-Styleguide)):

```
accounts/      — Пользователи, профили, 2FA, KYC, security audit
listings/      — Объявления, категории, игры, поиск (FTS), избранное
chat/          — WebSocket-чат через Django Channels
transactions/  — Сделки, отзывы, диспуты
payments/      — Кошелёк, эскроу, YooKassa, выводы
api/           — REST API (DRF) с throttling
admin_panel/   — Кастомная админка с модерацией
core/          — Уведомления, middleware, audit log, telegram, email
config/        — Settings, urls, ASGI/WSGI, Celery
```

Внутри приложений — слоистая архитектура (в основных бизнес-модулях, где это оправдано):

- `views.py` — тонкий HTTP-слой (валидация форм, redirect, messages)
- `services.py` — бизнес-логика (атомарные операции, side-effects через `transaction.on_commit`)
- `selectors.py` — запросы к БД (`select_related`, `prefetch_related`)
- `models.py` + `signals.py` — данные и сигналы
- `tasks.py` — Celery-задачи (идемпотентные, с retry)

## Метрики кода

- 161 Python-файл приложения (~24 900 строк, без миграций и тестов)
- 21 модель, 70 миграций, 162 маршрута
- 98 HTML-шаблонов
- 716 тестов, покрытие 80%

## API

```
GET    /api/listings/          — объявления (POST/PUT/DELETE — владелец)
GET    /api/games/             — игры (read-only)
GET    /api/categories/        — категории (read-only)
GET    /api/reviews/           — отзывы (POST — авторизованные)
GET    /api/conversations/     — диалоги пользователя
POST   /api/auth/token/        — получить токен
```

Session- или Token-аутентификация, throttling (anon 100/час, user 1000/час), пагинация по 20. Полное описание — [docs/api.md](docs/api.md).

## Тестирование

```bash
pytest                                   # все 716 тестов (~8 мин)
pytest --cov=. --cov-report=html         # HTML-отчёт о покрытии (htmlcov/)
pytest -m "not slow"                     # быстрые тесты
pytest payments/                         # тесты конкретного приложения
```

- 716 passed, 1 skipped (`config.settings.test`, прогон ~8 мин)
- покрытие 80% (`pytest --cov`)
- мок-объекты для внешних API (YooKassa, Telegram, push)
- фикстуры в `conftest.py`: `verified_user`, `seller`, `buyer`, `listing_factory` и др.

Подробнее — [docs/testing.md](docs/testing.md).

## Документация

| Раздел | Документ |
|--------|----------|
| Полный индекс | [docs/README.md](docs/README.md) |
| Быстрый старт | [docs/setup/quickstart.md](docs/setup/quickstart.md) |
| Полная установка | [docs/setup.md](docs/setup.md) |
| Архитектура | [docs/architecture.md](docs/architecture.md) |
| REST API | [docs/api.md](docs/api.md) |
| Тестирование | [docs/testing.md](docs/testing.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |

Настройка отдельных компонентов (Celery, Redis, email, Telegram, web-push, админка) — в [docs/setup/](docs/setup/).

## Деплой

Боевой стек — Docker Compose + Caddy (автоматический TLS). Выкат с post-deploy smoke-тестами:

```bash
bash scripts/deploy_with_smoke.sh
```

Архитектура стека, эксплуатация, обновление и откат — в [docs/deployment.md](docs/deployment.md). Чеклисты: [первый запуск](docs/deployment/pre-deploy-checklist.md), [после выката](docs/deployment/post-deploy-checklist.md).

## Вклад в проект

См. [CONTRIBUTING.md](CONTRIBUTING.md) — гайд для разработчиков.

## Безопасность

Нашли уязвимость? См. [SECURITY.md](SECURITY.md) — как сообщить приватно.

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Контакты

Вопросы и баг-репорты — через [GitHub Issues](https://github.com/reazonvan/LootLink---Marketplace/issues).
