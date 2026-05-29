# Официальный Python 3.13 образ
FROM python:3.13-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Создаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# collectstatic в build-time: с ManifestStaticFilesStorage manifest.json
# должен существовать ДО старта uvicorn, иначе первый запрос упадёт
# с ValueError("Missing staticfiles manifest entry...").
# DJANGO_SETTINGS_MODULE задан выше, SECRET_KEY достаточно фейкового —
# collectstatic не дёргает БД и не валидирует ключ.
RUN SECRET_KEY=build-time-dummy DEBUG=False USE_REDIS=False \
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
