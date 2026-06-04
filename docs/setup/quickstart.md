# Быстрый старт (разработка)

Поднять LootLink локально за несколько минут. Для самого быстрого старта —
на SQLite, без установки PostgreSQL. Полная установка с Postgres и всеми
сервисами — в [setup.md](../setup.md).

## Требования

- Python 3.13+
- Git

## Шаги

```bash
# 1. Клонировать и зайти в проект
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace

# 2. Виртуальное окружение
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 3. Зависимости для разработки
pip install -r requirements/development.txt

# 4. .env из примера
cp .env.example .env
```

Минимальный `.env` для запуска на SQLite (без Postgres и Redis):

```env
SECRET_KEY=dev-insecure-key-change-me
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.development
DB_ENGINE=sqlite
USE_REDIS=False
ALLOWED_HOSTS=localhost,127.0.0.1
```

```bash
# 5. Миграции и суперпользователь
python manage.py migrate
python manage.py createsuperuser

# 6. Запуск
python manage.py runserver
```

Открыть <http://127.0.0.1:8000/>.

## Что проверить

| URL | Что это |
|-----|---------|
| `/` | Главная (лендинг) |
| `/catalog/` | Каталог объявлений |
| `/accounts/register/` | Регистрация |
| `/accounts/login/` | Вход |
| `/admin/` | Django-админка (в dev `ADMIN_URL` по умолчанию `admin/`) |
| `/custom-admin/` | Кастомная админ-панель (для staff) |
| `/health/` | Healthcheck |

## Наполнить тестовыми данными

В админке добавьте пару игр (`Игры → Добавить`), затем создайте объявление
через `/listing/create/`. Либо используйте management-команды из `scripts/`,
если нужен seed.

## Дальше

- Полная установка с PostgreSQL, Redis, Celery — [setup.md](../setup.md)
- Архитектура и слои приложений — [architecture.md](../architecture.md)
- Как писать и запускать тесты — [testing.md](../testing.md)
- Гайд для контрибьюторов — [CONTRIBUTING.md](../../CONTRIBUTING.md)

## Если не запускается

- **Ошибка `SECRET_KEY not found`** — нет `.env` или в нём не задан `SECRET_KEY`.
- **Ошибка БД** — при `DB_ENGINE=sqlite` Postgres не нужен; проверьте, что
  переменная действительно `sqlite`. Для Postgres см. setup.md.
- **Не активировано окружение** — в начале строки должно быть `(venv)`.
- **Проблемы с venv на Windows** — см. [troubleshooting/venv.md](../troubleshooting/venv.md).
