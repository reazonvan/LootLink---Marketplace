# Docker на Windows (Docker Desktop)

## ⚠️ Ошибка `can't open file '/app/manage.py'`

**Причина:** Docker Desktop не имеет доступа к диску, на котором лежит проект (например `F:\`).

**Быстрое решение:** [DOCKER_WINDOWS_FIX.md](./DOCKER_WINDOWS_FIX.md) — пошаговая инструкция.

---

## Настройка bind mount (если File Sharing уже включен)

### Вариант A — скрипт (рекомендуется)

Из корня репозитория в PowerShell:

```powershell
.\scripts\docker-compose-up.ps1 up -d
```

Скрипт выставляет `PROJECT_ROOT` в абсолютный путь с прямыми слешами и вызывает `docker compose`.

### Вариант B — переменная в `.env`

Добавьте в `.env` (подставьте свой путь):

```env
PROJECT_ROOT=F:/LootLink---Marketplace
```

Путь — **прямые слеши**, без кавычек.

### Вариант C — Docker Desktop

**Settings → Resources → File sharing** — включите доступ к диску, на котором лежит проект (например `F:`), перезапустите Docker.

## Обычный запуск после настройки

```powershell
docker compose down
docker compose up -d
```
