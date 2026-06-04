# ---------- Stage 1: builder ----------
# Собираем wheels со всеми C-зависимостями (psycopg2, hiredis, cryptography,
# argon2-cffi, Pillow). gcc/libpq-dev ставятся ТОЛЬКО здесь и в финальный
# образ не попадают — меньше вес и attack surface в проде.
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements/ requirements/
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# Только runtime-зависимости: libmagic1 (python-magic), postgresql-client
# (pg_isready/psql в healthcheck и init-скриптах). gcc/libpq-dev НЕ ставим —
# psycopg2-binary везёт собственный libpq внутри wheel.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Ставим пакеты из заранее собранных wheels — без сети и без компиляторов.
COPY --from=builder /wheels /wheels
COPY requirements.txt .
COPY requirements/ requirements/
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Копируем проект
COPY . .

# collectstatic в build-time: с ManifestStaticFilesStorage manifest.json
# должен существовать ДО старта uvicorn, иначе первый запрос упадёт
# с ValueError("Missing staticfiles manifest entry...").
# DJANGO_SETTINGS_MODULE задан выше, SECRET_KEY достаточно фейкового —
# collectstatic не дёргает БД и не валидирует ключ.
# logs/ исключён через .dockerignore, а RotatingFileHandler в base.py
# открывает BASE_DIR/logs/*.log при любой management-команде (включая
# collectstatic). Поэтому каталог нужно создать ДО collectstatic, иначе
# configure_logging падает с FileNotFoundError на errors.log.
RUN mkdir -p /app/logs && \
    SECRET_KEY=build-time-dummy DEBUG=False USE_REDIS=False \
    DB_ENGINE=sqlite SQLITE_PATH=/tmp/build.sqlite3 \
    ADMIN_URL=build-only/ TRUSTED_PROXIES=127.0.0.1 \
    python manage.py collectstatic --noinput --clear

# Создаем пользователя для запуска приложения (безопасность)
RUN useradd -m -u 1000 lootlink && \
    mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R lootlink:lootlink /app

USER lootlink

# Открываем порт
EXPOSE 8000

# Production-сервер: gunicorn master + uvicorn ASGI workers.
# WEB_CONCURRENCY = 2*CPU + 1 (Heroku rule of thumb), переопределяется env-var.
# --worker-tmp-dir=/dev/shm избегает диск-I/O на heartbeat-файле в k8s.
# --timeout=60 длиннее дефолтных 30s — WebSocket handshake + handover не должен резать соединение.
CMD ["sh", "-c", "gunicorn config.asgi:application \
    --bind 0.0.0.0:8000 \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WEB_CONCURRENCY:-4} \
    --timeout 60 \
    --keep-alive 5 \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile -"]
