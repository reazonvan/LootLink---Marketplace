#!/usr/bin/env bash
#
# Deploy P0-P3 security fixes to production.
# Запуск: ssh root@lootlink.ru "bash -s" < scripts/deploy_p0_fixes.sh
# Или:    cd /opt/lootlink && bash scripts/deploy_p0_fixes.sh
#
# Что делает:
# 1. Бэкап БД до миграций (в /root/backups/)
# 2. git pull origin main
# 3. Генерирует недостающие секреты в .env (если ещё нет)
# 4. Пересборка контейнеров (web, celery_worker, celery_beat, flower)
# 5. Применение миграций
# 6. collectstatic
# 7. Healthcheck
#
# Идемпотентно — можно запускать повторно.

set -euo pipefail

PROJECT_DIR="/opt/lootlink"
BACKUP_DIR="/root/backups"
DATE_TAG="$(date +%Y%m%d_%H%M%S)"

log() { echo -e "\n\033[1;34m[$(date +%H:%M:%S)] $*\033[0m"; }
warn() { echo -e "\n\033[1;33m[WARN] $*\033[0m" >&2; }
err() { echo -e "\n\033[1;31m[ERROR] $*\033[0m" >&2; exit 1; }

# ──────────────────────────────────────────────────────────────────────
# 1. Подготовка
# ──────────────────────────────────────────────────────────────────────

[[ -d "$PROJECT_DIR" ]] || err "Проект не найден в $PROJECT_DIR"
cd "$PROJECT_DIR"

command -v docker >/dev/null || err "docker не установлен"
mkdir -p "$BACKUP_DIR"

# ──────────────────────────────────────────────────────────────────────
# 2. Бэкап БД ПЕРЕД миграциями (КРИТИЧНО)
# ──────────────────────────────────────────────────────────────────────

log "Бэкап БД → $BACKUP_DIR/lootlink_pre_p0_$DATE_TAG.sql"
docker compose exec -T db pg_dump -U postgres lootlink_db > "$BACKUP_DIR/lootlink_pre_p0_$DATE_TAG.sql" \
    || err "Бэкап БД не удался — деплой ОТМЕНЁН"

backup_size=$(du -h "$BACKUP_DIR/lootlink_pre_p0_$DATE_TAG.sql" | cut -f1)
log "Бэкап создан: $backup_size"

# ──────────────────────────────────────────────────────────────────────
# 3. Git pull
# ──────────────────────────────────────────────────────────────────────

log "git pull origin main"
git fetch origin main
CURRENT_COMMIT=$(git rev-parse HEAD)
TARGET_COMMIT=$(git rev-parse origin/main)
if [[ "$CURRENT_COMMIT" == "$TARGET_COMMIT" ]]; then
    log "Уже на актуальном коммите $CURRENT_COMMIT — pull не нужен"
else
    log "Пуллим $CURRENT_COMMIT → $TARGET_COMMIT"
    git reset --hard origin/main
fi

# ──────────────────────────────────────────────────────────────────────
# 4. Обновление .env (только новые ключи; существующие НЕ перетираем)
# ──────────────────────────────────────────────────────────────────────

log "Проверка .env"

ensure_env_key() {
    local key="$1"; local value="$2"; local description="$3"
    if grep -qE "^${key}=" .env; then
        log "  .env: $key уже задан — оставляем"
    else
        log "  .env: добавляем $key ($description)"
        echo "" >> .env
        echo "# $description" >> .env
        echo "${key}=${value}" >> .env
    fi
}

# Генерация Fernet ключа для шифрования payment_details
if ! grep -qE "^PAYMENT_DETAILS_KEY=" .env; then
    FERNET_KEY=$(docker compose exec -T web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
        || python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
        || openssl rand -base64 32 | tr '/' '_' | tr '+' '-')
    ensure_env_key "PAYMENT_DETAILS_KEY" "$FERNET_KEY" "P0-4 Fernet шифрование Withdrawal.payment_details"
fi

# HMAC секрет для YooKassa webhook
if ! grep -qE "^YOOKASSA_WEBHOOK_SECRET=" .env; then
    HMAC_SECRET=$(openssl rand -hex 32)
    ensure_env_key "YOOKASSA_WEBHOOK_SECRET" "$HMAC_SECRET" "P0-3 HMAC проверка webhook (ПРОПИСАТЬ в ЛК ЮKassa!)"
    warn "ВАЖНО: задайте этот же секрет в личном кабинете ЮKassa → Webhooks"
fi

# Комиссия платформы (5% по умолчанию, можно сменить)
ensure_env_key "PLATFORM_COMMISSION_PERCENT" "5" "P0-11 Комиссия платформы при release escrow"

# TRUSTED_PROXIES для get_client_ip (защита от XFF-спуфинга)
# Docker network бывает в 172.16.0.0/12, добавим localhost для healthcheck
if ! grep -qE "^TRUSTED_PROXIES=" .env; then
    ensure_env_key "TRUSTED_PROXIES" "127.0.0.1,::1,172.16.0.0/12,10.0.0.0/8" "P0-14 Trusted proxies для get_client_ip"
fi

# ADMIN_URL — если ещё стандартный, поменять на random
if grep -qE "^ADMIN_URL=admin/" .env; then
    RANDOM_PATH=$(openssl rand -hex 8)-mgmt/
    log "  .env: ADMIN_URL=admin/ → $RANDOM_PATH (P2-17 непредсказуемый путь)"
    sed -i "s|^ADMIN_URL=admin/|ADMIN_URL=$RANDOM_PATH|" .env
fi

# DJANGO_SETTINGS_MODULE = production (на всякий случай)
if ! grep -qE "^DJANGO_SETTINGS_MODULE=" .env; then
    ensure_env_key "DJANGO_SETTINGS_MODULE" "config.settings.production" "Production settings"
fi

# USE_REDIS=True если не задано
if ! grep -qE "^USE_REDIS=True" .env; then
    if grep -qE "^USE_REDIS=" .env; then
        sed -i "s|^USE_REDIS=.*|USE_REDIS=True|" .env
    else
        ensure_env_key "USE_REDIS" "True" "Redis обязателен в проде"
    fi
fi

# Security HTTPS флаги
ensure_env_key "SECURE_SSL_REDIRECT" "True" "HTTPS обязателен"
ensure_env_key "SESSION_COOKIE_SECURE" "True" "Secure session cookie"
ensure_env_key "CSRF_COOKIE_SECURE" "True" "Secure CSRF cookie"

# ──────────────────────────────────────────────────────────────────────
# 5. Build образов (web, celery, flower используют один образ)
# ──────────────────────────────────────────────────────────────────────

log "Сборка Docker-образов (~3-5 мин)"
docker compose build web celery_worker celery_beat flower

# ──────────────────────────────────────────────────────────────────────
# 6. Поднимаем стек (без force-recreate всех — только обновлённые)
# ──────────────────────────────────────────────────────────────────────

log "Обновление контейнеров"
docker compose up -d --no-deps --force-recreate web celery_worker celery_beat flower
# Caddy перезагружаем, чтобы подхватить новый Caddyfile
docker compose up -d --force-recreate caddy

# ──────────────────────────────────────────────────────────────────────
# 7. Миграции (выполняются автоматически на старте web, но дублируем
#    явный вызов для логирования и отлова ошибок)
# ──────────────────────────────────────────────────────────────────────

log "Ожидание готовности web (до 60 сек)"
for i in {1..30}; do
    if docker compose exec -T web python manage.py check >/dev/null 2>&1; then
        log "  web готов"
        break
    fi
    sleep 2
    [[ $i -eq 30 ]] && err "web не готов после 60 сек"
done

log "Применение миграций"
docker compose exec -T web python manage.py migrate --noinput

log "collectstatic"
docker compose exec -T web python manage.py collectstatic --noinput --clear

# ──────────────────────────────────────────────────────────────────────
# 8. Healthcheck
# ──────────────────────────────────────────────────────────────────────

log "Healthcheck"
docker compose exec -T web python manage.py check --deploy 2>&1 | tail -20 || warn "deploy check выявил замечания"

docker compose ps

log "HTTP health endpoint"
curl -sI -m 10 -H "X-Forwarded-Proto: https" http://localhost/health/ | head -3 || warn "Health endpoint недоступен"

# ──────────────────────────────────────────────────────────────────────
# 9. Финал
# ──────────────────────────────────────────────────────────────────────

log "=========================================="
log "DEPLOY ЗАВЕРШЁН — версия $(git rev-parse --short HEAD)"
log "Бэкап БД: $BACKUP_DIR/lootlink_pre_p0_$DATE_TAG.sql"
log ""
log "ПОСЛЕ ДЕПЛОЯ — ДЕЙСТВИЯ ВРУЧНУЮ:"
log "  1. Зайти под superuser, включить себе 2FA"
log "     (без 2FA staff не может вызывать критические admin-действия)"
log "  2. Прописать YOOKASSA_WEBHOOK_SECRET в ЛК ЮKassa → Webhooks"
log "  3. Проверить /opt/lootlink/.env — никаких значений не лежит в открытом виде"
log "     (особенно PAYMENT_DETAILS_KEY)"
log "  4. ADMIN_URL: новый путь к Django-админке — см. .env"
log "  5. Тестовая транзакция: создать → accept → confirm received."
log "     Проверить что комиссия 5% удержана с продавца."
log "=========================================="
