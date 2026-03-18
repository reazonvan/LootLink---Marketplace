# External Integrations

**Analysis Date:** 2026-03-18

## APIs & External Services

**Payment Processing:**
- YooKassa (ЮKassa) - Russian payment gateway for accepting payments
  - SDK/Client: yookassa (Python library)
  - Auth: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` (env vars)
  - Webhook: Incoming payment notifications with IP whitelist validation
  - Implementation: `payments/yookassa_integration.py` - YooKassaService class
  - Features: Payment creation, status checking, webhook verification with API validation

**Messaging & Notifications:**
- Telegram Bot - Bot notifications and user communication
  - SDK/Client: python-telegram-bot 20.7
  - Auth: `TELEGRAM_BOT_TOKEN` (env var)
  - Implementation: Telegram bot integration for notifications
  - Requirements: `requirements/telegram.txt`

- SMS.ru - SMS delivery service for Russian market
  - Auth: `SMS_RU_API_KEY` (env var)
  - Enabled via: `SMS_ENABLED` flag
  - Purpose: SMS notifications and verification

- Web Push Notifications - Browser push notifications
  - SDK/Client: pywebpush 1.14.0
  - Auth: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` (env vars)
  - Private key file: `.vapid_private.pem`
  - Requirements: `requirements/push.txt`

**Email:**
- SMTP Email Backend - Configurable email provider
  - Providers: Gmail, Yandex, Mail.ru (configurable)
  - Config: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`/`EMAIL_USE_SSL`
  - Auth: `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (env vars)
  - Default sender: `DEFAULT_FROM_EMAIL`
  - Timeout: 10 seconds
  - Console backend for development

## Data Storage

**Databases:**
- PostgreSQL 15 (primary)
  - Connection: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (env vars)
  - Client: psycopg2-binary
  - ORM: Django ORM
  - Connection pooling: CONN_MAX_AGE=600 (10 minutes)
  - Statement timeout: 30 seconds
  - Fallback: SQLite3 for local development (configurable via `DB_ENGINE`)

**File Storage:**
- AWS S3 (optional, production)
  - Enabled via: `USE_S3` flag
  - Credentials: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (env vars)
  - Bucket: `AWS_STORAGE_BUCKET_NAME`
  - Region: `AWS_S3_REGION_NAME` (default: us-east-1)
  - Client: boto3
  - Backend: django-storages S3Boto3Storage
  - Cache control: max-age=86400 (1 day)
  - ACL: public-read
  - Location prefix: media/

- Local filesystem (development/fallback)
  - Media root: `BASE_DIR / 'media'`
  - Static root: `BASE_DIR / 'staticfiles'`

**Caching:**
- Redis 7 (optional, production)
  - Enabled via: `USE_REDIS` flag
  - Connection: `REDIS_URL` (env var, default: redis://localhost:6379/1)
  - Client: django-redis with DefaultClient
  - Compression: zlib
  - Connection pool: max 50 connections
  - Timeout: 5 seconds per socket
  - Key prefix: lootlink
  - Default TTL: 300 seconds (5 minutes)
  - Fallback: Local memory cache for development

- Redis for Celery (separate instance)
  - Broker: `CELERY_BROKER_URL` (default: redis://localhost:6379/0)
  - Result backend: `CELERY_RESULT_BACKEND` (default: redis://localhost:6379/0)

- Redis for WebSocket layer
  - Channels backend: channels_redis.core.RedisChannelLayer
  - Connection: `REDIS_URL` (default: redis://localhost:6379/2)

## Authentication & Identity

**Auth Provider:**
- Custom Django authentication
  - Implementation: `accounts.backends.CaseInsensitiveModelBackend`
  - Custom user model: `accounts.CustomUser`
  - Case-insensitive username login
  - Token authentication: REST Framework TokenAuthentication
  - Token endpoint: `/api/auth/token/`

**Two-Factor Authentication:**
- TOTP (Time-based One-Time Password)
  - Library: django-otp with otp_totp plugin
  - Purpose: Optional 2FA for user accounts

## Monitoring & Observability

**Error Tracking:**
- Sentry - Error and performance monitoring (production only)
  - SDK: sentry-sdk 2.42.0
  - Auth: `SENTRY_DSN` (env var)
  - Integration: Django integration
  - Trace sampling: 100% (traces_sample_rate=1.0)
  - PII: Enabled (send_default_pii=True)
  - Environment: `ENVIRONMENT` (env var)
  - Release: `RELEASE_VERSION` (env var)

**Logs:**
- File-based logging
  - Main log: `logs/lootlink.log` (5MB rotating, 5 backups)
  - Error log: `logs/errors.log` (5MB rotating, 5 backups)
  - Security log: `logs/security.log` (5MB rotating, 5 backups)
  - Format: Verbose with timestamp, level, module
  - Handlers: Console (INFO), File (WARNING), Error file (ERROR)

## CI/CD & Deployment

**Hosting:**
- Docker containers (production)
- Services: web (Daphne), db (PostgreSQL), redis, celery_worker, celery_beat, flower, nginx/caddy

**CI Pipeline:**
- Pre-commit hooks: `.pre-commit-config.yaml`
- Code quality: flake8, black, isort
- Testing: pytest with coverage
- Not detected: GitHub Actions or external CI service

## Environment Configuration

**Required env vars:**
- `SECRET_KEY` - Django secret key (mandatory, no default)
- `DEBUG` - Debug mode flag
- `ALLOWED_HOSTS` - Comma-separated allowed hosts
- `DB_PASSWORD` - PostgreSQL password (mandatory)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_NAME` - Database connection
- `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` - Payment gateway
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` - Web push keys
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` - Email credentials
- `SENTRY_DSN` - Error tracking (production)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - S3 credentials (if USE_S3=True)
- `REDIS_URL` - Redis connection (if USE_REDIS=True)
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` - Celery configuration

**Secrets location:**
- `.env` file (not committed to git)
- Environment variables in production deployment
- Private key file: `.vapid_private.pem`

## Webhooks & Callbacks

**Incoming:**
- YooKassa payment webhooks
  - Endpoint: Payment webhook handler in `payments/` app
  - Events: payment.succeeded, payment.canceled
  - Verification: IP whitelist + API validation
  - Idempotency: Duplicate webhook handling with status checks
  - Payload validation: Amount, currency, status consistency checks

**Outgoing:**
- Not detected: No outgoing webhooks to external services

---

*Integration audit: 2026-03-18*
