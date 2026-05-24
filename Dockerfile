# Официальный Python 3.13 образ
FROM python:3.14-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Создаем пользователя для запуска приложения (безопасность)
RUN useradd -m -u 1000 lootlink && \
    mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R lootlink:lootlink /app

USER lootlink

# Открываем порт
EXPOSE 8000

# Запуск через ASGI сервер (поддержка HTTP + WebSocket)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

