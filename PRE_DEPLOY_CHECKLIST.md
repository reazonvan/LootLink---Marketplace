# Pre-deploy checklist (LootLink → production)

Используется один раз перед первым стартом контейнеров на боевом сервере.
После — ориентируйтесь на `DEPLOY_NOW.md` для текущих обновлений.

## 1. На сервере (один раз)

```bash
# Минимум: docker, docker compose v2, git, ufw
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git ufw
sudo systemctl enable --now docker
sudo usermod -aG docker $USER  # перелогиниться

# Файрвол: только 22/80/443
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443
sudo ufw enable
```

## 2. DNS

- `lootlink.ru A` → IP сервера
- `www.lootlink.ru A` → IP сервера (Caddyfile сделает 308 → apex)

Проверить:
```bash
dig +short lootlink.ru     # должен вернуть IP сервера
dig +short www.lootlink.ru # тот же IP
```

## 3. Код

```bash
git clone https://github.com/<owner>/LootLink---Marketplace.git
cd LootLink---Marketplace
git checkout main
git pull
```

## 4. .env

```bash
cp .env.example .env
```

**Обязательно сгенерировать новые случайные значения** (нельзя оставлять из примера):

| Переменная | Команда генерации |
|------------|-------------------|
| `SECRET_KEY` | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DB_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `PAYMENT_DETAILS_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `YOOKASSA_WEBHOOK_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `METRICS_TOKEN` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `FLOWER_PASSWORD` | `python -c "import secrets; print(secrets.token_urlsafe(24))"` |

**Обязательно проставить (не пустыми):**

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `DEBUG=False`
- `USE_REDIS=True`
- `ALLOWED_HOSTS=lootlink.ru,www.lootlink.ru`
- `CSRF_TRUSTED_ORIGINS=https://lootlink.ru,https://www.lootlink.ru`
- `ADMIN_URL=<непредсказуемый>/` (НЕ `admin/` — проверяется `production.py`)
- `TRUSTED_PROXIES=172.16.0.0/12` (docker default bridge)
- `WEB_CONCURRENCY=4` (или `2*CPU+1`)

**Опционально, но рекомендую:**

- `SENTRY_DSN=https://...` — мониторинг ошибок
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
  + `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `SMS_RU_API_KEY=...` + `SMS_ENABLED=True`
- `YOOKASSA_SHOP_ID=...` + `YOOKASSA_SECRET_KEY=...`

## 5. Первый запуск

```bash
docker compose pull            # подтянуть postgres, redis, caddy, pgbouncer
docker compose build           # собрать web-образ (collectstatic зашьётся в build)
docker compose up -d           # запустить весь стек
```

Что произойдёт в правильном порядке:

1. `db` (postgres) поднимается и ждёт healthy
2. `pgbouncer` цепляется к `db`, ждёт healthy
3. `migrator` запускает `python manage.py migrate --noinput` через `db`
   напрямую (не pgbouncer — для DDL это важно), завершается
4. `redis` поднимается параллельно
5. `web` стартует gunicorn + uvicorn workers через `pgbouncer`
6. `celery_worker`, `celery_beat`, `flower` подключаются
7. `caddy` получает Let's Encrypt сертификат для `lootlink.ru`

## 6. Проверка после старта

```bash
# Внутри docker network
docker exec lootlink_web curl -s http://localhost:8000/health/live/
# Ответ: {"status": "ok", "check": "live"}

docker exec lootlink_web curl -s http://localhost:8000/health/ready/
# Ответ: {"status": "ok", "check": "ready", "checks": {"database":"ok","cache":"ok"}}

# Снаружи (после Let's Encrypt — может занять 1-3 мин)
curl -I https://lootlink.ru/health/live/
# HTTP/2 200, Strict-Transport-Security: max-age=...

# Логи
docker compose logs web --tail=50
docker compose logs caddy --tail=20

# Метрики (только из docker network — извне 403)
docker exec lootlink_web curl -s -H "Authorization: Bearer $METRICS_TOKEN" \
  http://localhost:8000/metrics/ | head -20
```

## 7. Создать первого администратора

```bash
docker exec -it lootlink_web python manage.py createsuperuser
# username, email, пароль
```

Зайти на `https://lootlink.ru/<ADMIN_URL>` (тот, что задал в .env).
В админке сразу включить себе 2FA — иначе требующие 2FA админ-действия
(ban_user, delete_listing, cancel_transaction, resolve_dispute) недоступны.

## 8. Backups (на сервере отдельно)

```bash
chmod +x scripts/auto_backup.sh
# Добавить в crontab пользователя
echo "0 3 * * * cd $HOME/LootLink---Marketplace && ./scripts/auto_backup.sh" \
  | crontab -
```

По умолчанию `auto_backup.sh` льёт дамп в `backups/` локально.
Для prod рекомендую дописать заливку на S3-совместимый bucket
(`rclone copy` после `pg_dump`).

## 9. Что мониторить первые сутки

| Сигнал | Где смотреть | Что делать |
|--------|-------------|------------|
| 5xx в `errors.log` | `docker exec lootlink_web tail -f /app/logs/errors.log` | в Sentry должны прийти |
| Failed login spikes | `tail -f /app/logs/security.log` | brute force middleware блокирует |
| postgres connection limit | `docker exec lootlink_db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"` | если > 80 — поднять `DEFAULT_POOL_SIZE` в pgbouncer |
| Celery очередь | `https://lootlink.ru/flower/` | задачи должны успевать |
| Memory | `docker stats` | uvicorn worker > 500MB = leak |

## 10. Rollback (если что-то пошло не так)

```bash
git log --oneline | head -10
git reset --hard <prev-good-sha>
docker compose build
docker compose up -d
```

`migrate` не запустится повторно если миграции уже применены.
Откат миграций — отдельно через `manage.py migrate <app> <prev_migration>`.
