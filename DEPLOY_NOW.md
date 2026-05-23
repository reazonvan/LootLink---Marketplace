# Деплой P0-P3 фиксов — инструкция

## Что в этом коммите

- **Коммит:** `56e8e70` (на main)
- **Изменения:** 88 P0-P3 фиксов безопасности + production-ready Docker
- **Тесты:** 530 passed
- **Миграции:** 9 новых, требуется применить на проде

## Вариант А — автоматический (рекомендуется)

```bash
ssh root@lootlink.ru
cd /opt/lootlink
git fetch origin main && git reset --hard origin/main
bash scripts/deploy_p0_fixes.sh
```

Скрипт сам сделает:
1. Бэкап БД → `/root/backups/lootlink_pre_p0_<timestamp>.sql`
2. Сгенерирует недостающие секреты в `.env` (Fernet, HMAC, ADMIN_URL)
3. Пересоберёт Docker-образы
4. Применит миграции, collectstatic
5. Healthcheck

## Вариант Б — ручной (если хочется контроля)

```bash
# 1. На сервере
ssh root@lootlink.ru
cd /opt/lootlink

# 2. Бэкап БД (КРИТИЧНО, не пропускайте!)
mkdir -p /root/backups
docker compose exec -T db pg_dump -U postgres lootlink_db > \
  /root/backups/lootlink_pre_p0_$(date +%Y%m%d_%H%M).sql

# 3. Pull кода
git fetch origin main
git reset --hard origin/main

# 4. Добавить недостающие секреты в .env
# Сгенерировать значения:
docker compose exec web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → PAYMENT_DETAILS_KEY=...

python3 -c "import secrets; print(secrets.token_hex(32))"
# → YOOKASSA_WEBHOOK_SECRET=...

# Дописать в .env (только новые):
cat >> .env <<EOF

# P0-фиксы (сгенерированы выше)
PAYMENT_DETAILS_KEY=<вставить Fernet ключ>
YOOKASSA_WEBHOOK_SECRET=<вставить HMAC секрет>
PLATFORM_COMMISSION_PERCENT=5
TRUSTED_PROXIES=127.0.0.1,::1,172.16.0.0/12,10.0.0.0/8
EOF

# Поменять ADMIN_URL на непредсказуемый (если ещё admin/)
sed -i 's|^ADMIN_URL=admin/|ADMIN_URL='$(openssl rand -hex 8)'-mgmt/|' .env

# 5. Сборка + перезапуск
docker compose build web celery_worker celery_beat flower
docker compose up -d --force-recreate web celery_worker celery_beat flower caddy

# 6. Миграции (внутри контейнера)
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py collectstatic --noinput --clear

# 7. Проверка
docker compose ps
docker compose exec web python manage.py check --deploy
curl -sI https://lootlink.ru/health/
```

## После деплоя — обязательно

1. **Прописать `YOOKASSA_WEBHOOK_SECRET` в ЛК ЮKassa**
   → Личный кабинет → Настройки → HTTP-уведомления → секрет

2. **Включить 2FA на staff-аккаунтах**
   `https://lootlink.ru/accounts/2fa/setup/`
   Без 2FA staff больше не может вызывать критические admin-действия
   (ban_user, delete_listing, cancel_transaction, resolve_dispute)

3. **Новый ADMIN_URL**
   Старый `https://lootlink.ru/admin/` → больше не работает.
   Новый путь — в `.env` файле на сервере (поле ADMIN_URL).

4. **Тестовая сделка**
   - Создать пробную покупку
   - Принять (accept) — должен создаться funded escrow
   - Подтвердить получение (confirm_received)
   - Проверить что 5% удержано как комиссия платформы

## Откат (если что-то сломалось)

```bash
# Назад к предыдущему коммиту:
ssh root@lootlink.ru
cd /opt/lootlink
git reset --hard f8b22f1  # коммит до P0-фиксов

# Восстановить БД из бэкапа:
docker compose exec -T db psql -U postgres -d lootlink_db < \
  /root/backups/lootlink_pre_p0_<timestamp>.sql

# Пересборка
docker compose build web
docker compose up -d --force-recreate web celery_worker celery_beat flower

# ВАЖНО: после rollback нужно вернуть на место ВСЕ секреты что были
# до изменения, иначе старый код может не понимать новые env-переменные.
```

## Что изменилось важного для пользователей

- **Покупатели:** теперь могут открывать спор только если эскроу funded;
  спор закрывается через 30 дней (auto-release к продавцу если нет спора)
- **Продавцы:** больше не могут самостоятельно "завершить сделку" — только
  покупатель через "подтвердить получение", либо auto-release по deadline
- **Все:** комиссия 5% удерживается с продавца при release
- **Реквизиты выводов** (номера карт) теперь зашифрованы в БД,
  в админке видна только маска `**** **** **** 1234`
- **2FA обязательна для админов** на критических действиях
- **Регистрация:** новый пользователь сначала должен подтвердить телефон

## Риски и мониторинг

| Риск | Что проверять |
|---|---|
| Миграция 0010 долго на большой БД | `docker compose exec web python manage.py migrate --plan` |
| Caddy не получает cert | `docker compose logs caddy 2>&1 \| tail -50` |
| YooKassa webhook 403 | Проверь что secret в .env совпадает с ЛК ЮKassa |
| Старые залогиненные не отвалились | Сессии не инвалидируются — продолжат работать |
| Старые Withdrawal с открытым payment_details | Они продолжат работать (legacy fallback в get_payment_details) |
