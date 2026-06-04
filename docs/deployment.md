# Deployment Guide для LootLink

Развёртывание LootLink в production. Боевой стек — **Docker Compose + Caddy**
(автоматический TLS). Ручная установка через systemd/nginx больше не
поддерживается.

Связанные документы:

- **[Pre-deploy checklist](deployment/pre-deploy-checklist.md)** — пошаговый первый
  запуск на чистом сервере (DNS, `.env`, генерация секретов, первый `up`).
- **[Чеклист после деплоя](deployment/post-deploy-checklist.md)** — что проверить
  после каждого выката.

Этот файл описывает архитектуру стека, эксплуатацию и тюнинг. Процедура выката
обновлений и откат — в разделе «Обновление» ниже.

---

## Предварительные требования

- **Сервер**: Ubuntu 22.04+ / Debian 12+ (любой Linux с Docker)
- **RAM**: минимум 2 GB, рекомендуется 4 GB+
- **CPU**: минимум 2 ядра
- **Диск**: минимум 20 GB SSD
- **Домен**: с A/AAAA-записями на IP сервера (для Let's Encrypt)
- **Docker**: Docker Engine + Compose v2 (`docker compose`, не `docker-compose`)
- **Порты наружу**: только 22 (SSH), 80 и 443 (Caddy). Всё остальное —
  внутри docker-сети.

---

## Архитектура стека

Всё поднимается одним `docker compose up -d`. Публичный вход — только через
Caddy; `web` слушает `:8000` исключительно внутри docker-сети.

```
Интернет ──443/80──► caddy ──┬── /static/*, /media/*   → отдаёт файлы напрямую
                             ├── /flower/*             → reverse_proxy flower:5555
                             ├── /.env*, /metrics*, …  → 403
                             └── остальное             → reverse_proxy web:8000
                                                              │
   web (gunicorn + uvicorn ASGI workers)  ──DB──► pgbouncer ──► postgres:15
        │   ▲                                      (transaction pool)
        │   └── ждёт migrator (один раз migrate) и pgbouncer (healthy)
        └──────────────► redis ◄── celery_worker, celery_beat, channels, cache
```

| Сервис | Образ / запуск | Роль |
|--------|----------------|------|
| `caddy` | `caddy` | Reverse proxy, авто-TLS (Let's Encrypt), отдача static/media, www→apex 308 |
| `web` | `gunicorn config.asgi:application` с `uvicorn.workers.UvicornWorker` | Django (HTTP + WebSocket), `WEB_CONCURRENCY` воркеров |
| `migrator` | `python manage.py migrate --noinput` | Однократный init: применяет миграции напрямую в `db` (не через pgbouncer) и завершается |
| `pgbouncer` | `edoburu/pgbouncer` | Пул соединений в transaction-mode перед Postgres |
| `db` | `postgres:15-alpine` | Основная БД (FTS, GIN-индексы, CheckConstraint) |
| `redis` | `redis:7` | Cache, sessions (`cached_db`), Celery broker+result, Channels layer |
| `celery_worker` | `celery -A config worker` | Фоновые задачи (email, миниатюры, push, эскроу) |
| `celery_beat` | `celery -A config beat` | Планировщик: auto-release эскроу, очистка логов, прогрев кэша |
| `flower` | `flower` | Мониторинг Celery, доступен по `/flower/` |

**Порядок старта** (через healthcheck-зависимости): `db` → `pgbouncer` →
`migrator` (отрабатывает и выходит) → `web`, `celery_*`, `flower` → `caddy`
получает сертификат. `collectstatic` выполняется на этапе сборки образа
(`ManifestStaticFilesStorage`, `staticfiles.json` уже внутри образа), поэтому
отдельным шагом гонять его не нужно.

---

## Первый запуск

Полная процедура с генерацией секретов — в
**[pre-deploy checklist](deployment/pre-deploy-checklist.md)**. Кратко:

```bash
# 1. Код
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace

# 2. .env из примера, заполнить и сгенерировать секреты
cp .env.example .env
nano .env

# 3. Поднять стек
docker compose pull          # postgres, redis, caddy, pgbouncer
docker compose build         # web-образ (collectstatic зашивается в build)
docker compose up -d         # весь стек, migrator применит миграции сам

# 4. Первый администратор
docker exec -it lootlink_web python manage.py createsuperuser
```

### Критичные переменные `.env`

Обязательные (полный список и команды генерации — в pre-deploy checklist):

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=<get_random_secret_key()>
ALLOWED_HOSTS=lootlink.ru,www.lootlink.ru
CSRF_TRUSTED_ORIGINS=https://lootlink.ru,https://www.lootlink.ru

DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=<secrets.token_urlsafe(32)>
USE_REDIS=True
REDIS_URL=redis://redis:6379/1

ADMIN_URL=<непредсказуемая-строка>/        # production.py упадёт, если admin/
TRUSTED_PROXIES=172.16.0.0/12              # docker bridge — для доверия XFF
WEB_CONCURRENCY=4                          # или 2*CPU+1

# Безопасность платежей (P0-фиксы)
PAYMENT_DETAILS_KEY=<Fernet.generate_key()>
YOOKASSA_WEBHOOK_SECRET=<secrets.token_hex(32)>

# Наблюдаемость
METRICS_TOKEN=<secrets.token_urlsafe(32)>  # для Prometheus scrape
SENTRY_DSN=https://...                      # опционально
```

> `production.py` намеренно валит старт, если `ADMIN_URL=admin/` или
> `USE_REDIS=False` — это защита от деплоя с дефолтами.

---

## Обновление

Рекомендуемый путь — единый скрипт с post-deploy smoke:

```bash
cd /opt/lootlink
export GITHUB_DISPATCH_TOKEN="<github_token>"   # для авто-триггера smoke
bash scripts/deploy_with_smoke.sh
```

Вручную:

```bash
git fetch origin main && git reset --hard origin/main
docker compose build web celery_worker celery_beat flower
docker compose up -d --force-recreate web celery_worker celery_beat flower caddy
# Миграции применит сервис migrator при пересоздании; либо вручную:
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py check --deploy
curl -sI https://lootlink.ru/health/live/
```

### Откат

```bash
git reset --hard <предыдущий-SHA>          # SHA до проблемного выката
docker compose build web celery_worker celery_beat flower
docker compose up -d --force-recreate web celery_worker celery_beat flower caddy
# при необходимости — восстановить БД из дампа:
docker compose exec -T db psql -U postgres -d lootlink_db < backups/<dump>.sql
```

---

## Эксплуатация

### Health-checks и метрики

```bash
# Liveness (процесс жив)
docker exec lootlink_web curl -s http://localhost:8000/health/live/
# {"status": "ok", "check": "live"}

# Readiness (БД + кэш доступны)
docker exec lootlink_web curl -s http://localhost:8000/health/ready/
# {"status": "ok", "check": "ready", "checks": {"database": "ok", "cache": "ok"}}

# Prometheus-метрики (только из docker-сети; снаружи Caddy отдаёт 403)
docker exec lootlink_web curl -s -H "Authorization: Bearer $METRICS_TOKEN" \
  http://localhost:8000/metrics/ | head
```

`/metrics/` отдаёт django-prometheus (latency, БД/кэш-запросы, 5xx). Если
`METRICS_TOKEN` пуст — endpoint доступен только staff-пользователям.

### Логи

```bash
docker compose logs web --tail=100 -f
docker compose logs caddy --tail=50          # выдача сертификата, проксирование
docker compose logs celery_worker --tail=50

# Файловые логи Django внутри web-контейнера (RotatingFileHandler):
docker exec lootlink_web tail -f /app/logs/errors.log     # ERROR+
docker exec lootlink_web tail -f /app/logs/security.log   # брутфорс, 2FA, аудит
```

### Celery

Очереди и задачи — через Flower: `https://lootlink.ru/flower/`
(basic-auth настраивается самим Flower через `FLOWER_*` в `.env`).

### Доступ к БД

```bash
# Через pgbouncer (как ходит приложение)
docker exec -it lootlink_pgbouncer psql -h 127.0.0.1 -U postgres lootlink_db

# Напрямую в postgres (для DDL, обслуживания)
docker exec -it lootlink_db psql -U postgres lootlink_db

# Число активных соединений (если близко к max_connections=100 — растить пул)
docker exec lootlink_db psql -U postgres -c \
  "SELECT count(*) FROM pg_stat_activity;"
```

### Бэкапы

```bash
chmod +x scripts/auto_backup.sh
# crontab пользователя — ежедневный дамп в 3:00
echo "0 3 * * * cd $HOME/LootLink---Marketplace && ./scripts/auto_backup.sh" | crontab -
```

По умолчанию дамп пишется в `backups/` локально. Для прода добавьте заливку
в S3-совместимый bucket (`rclone copy` после `pg_dump`). Ручной бэкап:

```bash
docker compose exec -T db pg_dump -U postgres lootlink_db > backup_$(date +%F).sql
```

---

## Безопасность сервера

TLS, HSTS, security-заголовки и редиректы делает Caddy + Django middleware —
вручную сертификаты получать не нужно. На уровне ОС остаётся firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

Чеклист:

- [ ] `DEBUG=False`, сильный `SECRET_KEY`, корректный `ALLOWED_HOSTS`
- [ ] `ADMIN_URL` — непредсказуемый (не `admin/`)
- [ ] Секреты только в `.env` (никогда в git); `.env*` заблокирован в Caddy (403)
- [ ] UFW: открыты только 22/80/443
- [ ] SSH по ключу, fail2ban (опционально — поверх брутфорс-защиты Django)
- [ ] `PAYMENT_DETAILS_KEY`, `YOOKASSA_WEBHOOK_SECRET` заданы
- [ ] 2FA включена на staff-аккаунтах (иначе критичные admin-действия недоступны)
- [ ] Бэкапы в cron и проверены на восстановление

---

## Тюнинг производительности

### PgBouncer

Стоит в transaction-mode (`POOL_MODE=transaction`), `DEFAULT_POOL_SIZE=25`,
`MAX_CLIENT_CONN=500`. Это позволяет десяткам воркеров приложения работать
через ~25 реальных соединений к Postgres. Если в `pg_stat_activity` стабильно
близко к `max_connections` — поднимайте `DEFAULT_POOL_SIZE` (но суммарно
worker'ы × pool не должны превышать postgres `max_connections`).

### Gunicorn/uvicorn

`WEB_CONCURRENCY` в `.env`, формула `2*CPU + 1`. Воркеры — ASGI
(`uvicorn.workers.UvicornWorker`), один тип обслуживает и HTTP, и WebSocket.

### PostgreSQL

```ini
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
max_connections = 100
log_min_duration_statement = 1000   # лог запросов > 1s
```

### Redis

```ini
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`): линт (black, isort, flake8),
тесты (pytest), security-скан (bandit). Деплой — ручной (`deploy_with_smoke.sh`
с сервера), не из CI.

**Post-deploy smoke** (`.github/workflows/post-deploy-smoke.yml`) — Playwright-
проверки после выката: публичные сценарии (`scripts/playwright_smoke.py`) и
авторизованные user-journey (`scripts/playwright_user_journey.py`). Подробности
и нужные secrets — в [testing.md](testing.md).

---

## Troubleshooting

### Caddy не выдаёт сертификат

```bash
docker compose logs caddy 2>&1 | tail -50
```

Проверьте, что A-записи `lootlink.ru` и `www.lootlink.ru` указывают на IP
сервера и порты 80/443 открыты (ACME-challenge ходит по 80).

### `web` не стартует / 502 от Caddy

```bash
docker compose ps                       # web должен быть healthy
docker compose logs web --tail=80
docker exec lootlink_web python manage.py check --deploy
```

Частая причина — `migrator` упал (битая миграция): `docker compose logs migrator`.

### Упёрлись в лимит соединений Postgres

Растёт `pg_stat_activity`, в логах `web` — `too many connections`. Поднять
`DEFAULT_POOL_SIZE` у pgbouncer или снизить `WEB_CONCURRENCY`.

### Статика отдаёт старую версию

Образ собирается с `collectstatic` и manifest. После изменения CSS/JS нужен
`docker compose build web` (не только `up`), иначе в образе старый
`staticfiles.json`.

---

## Поддержка

- GitHub Issues: <https://github.com/reazonvan/LootLink---Marketplace/issues>
- Security (приватно): см. [SECURITY.md](../SECURITY.md)
