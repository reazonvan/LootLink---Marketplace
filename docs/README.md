# Документация LootLink

## Быстрый старт

- **[Быстрый старт](setup/quickstart.md)** — поднять локально за несколько минут (SQLite)
- **[Полная установка](setup.md)** — установка для разработки с PostgreSQL, Redis, Celery
- **[Установка на Windows](setup/windows.md)** — гайд под Windows + VS Code

## Настройка компонентов

- **[Celery](setup/celery.md)** — асинхронные задачи
- **[Redis](setup/redis.md)** — кэш, сессии, брокер
- **[Email и SMS](setup/email.md)** — отправка писем и кодов
- **[Telegram-бот](setup/telegram-bot.md)** — уведомления в Telegram
- **[Web Push](setup/web-push.md)** — браузерные push-уведомления
- **[Админ-панель](setup/admin-panel.md)** — кастомная админка
- **[Docker на Windows](setup/docker-windows.md)** — bind mount и File Sharing

## Архитектура и API

- **[Архитектура](architecture.md)** — стек, слои, связи между app
- **[API](api.md)** — REST endpoints

## Тестирование

- **[Тестирование](testing.md)** — как писать и запускать тесты

## Развёртывание

- **[Deployment Guide](deployment.md)** — архитектура прод-стека (Docker + Caddy), эксплуатация, обновление, откат
- **[Pre-deploy checklist](deployment/pre-deploy-checklist.md)** — первый запуск на боевом сервере (DNS, `.env`, секреты)
- **[Чеклист после деплоя](deployment/post-deploy-checklist.md)** — что проверить после каждого выката
- **[Бэкапы](deployment/backup.md)** — резервное копирование БД

## Решение проблем

- **[Проблемы с venv](troubleshooting/venv.md)** — виртуальное окружение
- **[Проблемы на Windows](troubleshooting/windows.md)** — Python, PowerShell, VS Code

## Вклад в проект

См. [CONTRIBUTING.md](../CONTRIBUTING.md) в корне проекта.

## Структура

```
docs/
├── architecture.md  api.md  testing.md
├── setup.md            # обзор установки
├── deployment.md       # обзор деплоя
├── setup/              # настройка компонентов
├── deployment/         # чеклисты и бэкапы
└── troubleshooting/    # решение проблем
```
