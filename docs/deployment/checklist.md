# Чеклист после деплоя

Прогоняется после каждого выката на production. Первый запуск на чистом
сервере — по [PRE_DEPLOY_CHECKLIST.md](../../PRE_DEPLOY_CHECKLIST.md);
процедура самого выката и откат — в [DEPLOY_NOW.md](../../DEPLOY_NOW.md).

## 1. Контейнеры подняты

```bash
docker compose ps
```

- [ ] `web` — `healthy`
- [ ] `db`, `pgbouncer`, `redis` — `healthy`
- [ ] `migrator` — `Exited (0)` (отработал миграции и вышел)
- [ ] `caddy`, `celery_worker`, `celery_beat`, `flower` — `running`

## 2. Миграции применены

```bash
docker compose exec web python manage.py showmigrations | grep -c "\[ \]"
# Должно быть 0 неприменённых
docker compose exec web python manage.py check --deploy
```

## 3. Сайт отвечает

```bash
# Изнутри сети
docker exec lootlink_web curl -s http://localhost:8000/health/ready/
# {"status": "ok", ... "database": "ok", "cache": "ok"}

# Снаружи (после выдачи сертификата Let's Encrypt — может занять 1–3 мин)
curl -I https://lootlink.ru/health/live/      # HTTP/2 200 + HSTS
curl -I https://www.lootlink.ru               # 308 → https://lootlink.ru
```

- [ ] `/health/ready/` отдаёт `database: ok`, `cache: ok`
- [ ] `https://lootlink.ru/` открывается, есть заголовок `Strict-Transport-Security`
- [ ] `www` редиректится на apex кодом 308
- [ ] `/sitemap.xml`, `/robots.txt`, `/manifest.json` отдаются

## 4. Логи чистые

```bash
docker compose logs web --tail=80
docker exec lootlink_web tail -20 /app/logs/errors.log
docker compose logs caddy --tail=20          # сертификат получен, без ACME-ошибок
```

- [ ] Нет повторяющихся 5xx и трейсбеков
- [ ] В Sentry не сыплются новые ошибки выката

## 5. Фоновые задачи и метрики

- [ ] Flower доступен: `https://lootlink.ru/flower/`, воркеры online
- [ ] Celery beat запланировал задачи (auto-release эскроу, прогрев кэша)
- [ ] Метрики (из сети): `curl -H "Authorization: Bearer $METRICS_TOKEN" http://localhost:8000/metrics/`

## 6. Бизнес-сценарии (smoke)

Автоматически — через post-deploy smoke (Playwright), см.
[TESTING_GUIDE.md](../TESTING_GUIDE.md):

```bash
export GITHUB_DISPATCH_TOKEN="<github_token>"
bash scripts/trigger_post_deploy_smoke.sh
```

Либо вручную проверить:

- [ ] Регистрация/вход работают, ошибки формы показываются
- [ ] Создание объявления (продавец)
- [ ] Старт чата и отправка сообщения (WebSocket)
- [ ] Запрос на покупку → эскроу funded

## 7. Если что-то сломалось

Откат — по [DEPLOY_NOW.md](../../DEPLOY_NOW.md) (раздел «Откат»): `git reset`
на предыдущий SHA, пересборка, при необходимости — восстановление БД из дампа
в `backups/`.
