# LootLink Marketplace

P2P маркетплейс для торговли внутриигровыми предметами между игроками.

[![Live Demo](https://img.shields.io/badge/demo-lootlink.ru-blue)](https://lootlink.ru)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)

**Демо:** [lootlink.ru](https://lootlink.ru)

## Что это

Веб-приложение для прямой торговли игровыми предметами. Пользователи создают объявления, общаются через встроенный чат, проводят сделки. Есть система репутации, отзывы, модерация.

## Стек

- **Backend:** Python 3.10+, Django 4.2, DRF, Celery, Channels (WebSockets)
- **БД:** PostgreSQL 15, Redis
- **Frontend:** Django templates, Bootstrap 5, JavaScript ES6+
- **Деплой:** Docker, Nginx, Gunicorn, Systemd

## Установка

```bash
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements/development.txt
cp env.example.txt .env      # отредактировать
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

Скопируйте `env.example.txt` в `.env` и заполните:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=your-password
REDIS_URL=redis://localhost:6379/1
```

Полный список переменных — в `env.example.txt`.

## Структура

```
accounts/        — Пользователи, профили, аутентификация
listings/        — Объявления, категории, игры, избранное
chat/            — Чат (WebSocket)
transactions/    — Сделки, отзывы
payments/        — Платежи (в разработке)
api/             — REST API
admin_panel/     — Кастомная админка
core/            — Утилиты, middleware, уведомления
config/          — Настройки Django
```

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
python manage.py test
coverage run --source='.' manage.py test && coverage report
```

## Деплой

```bash
bash scripts/deploy_with_smoke.sh
```

Подробности в `docs/DEPLOYMENT.md`.

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Контакты

Иван Петров — ivanpetrov20066.ip@gmail.com
