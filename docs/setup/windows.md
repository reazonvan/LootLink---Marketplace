# Установка на Windows

Путь для Windows + VS Code. Если что-то не запускается — см. [проблемы на Windows](../troubleshooting/windows.md) и [проблемы с venv](../troubleshooting/venv.md).

## Требования

- Python 3.13+ — [python.org](https://www.python.org/downloads/), при установке отметить **«Add Python to PATH»**
- Git

## Установка

```powershell
cd D:\LootLink---Marketplace
python -m venv venv
.\venv\Scripts\activate            # в строке появится (venv)
python -m pip install --upgrade pip
pip install -r requirements/development.txt
copy .env.example .env             # отредактировать под себя
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Открыть http://127.0.0.1:8000.

## VS Code

- `Ctrl+Shift+P` → **Python: Select Interpreter** → `.\venv\Scripts\python.exe` (в статус-баре появится `('venv')`).
- Запуск сервера: задача `Ctrl+Shift+B` или терминал с активным venv.
- Отладка: `F5` (Django с debugger), `F9` — breakpoint.

Конфиги в `.vscode/` уже настроены под Windows.

## Полезные команды

PowerShell с активированным venv:

```powershell
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py shell
python manage.py collectstatic --noinput
pytest
```

## Альтернатива — Docker

Если не хочется настраивать Python локально:

```powershell
docker compose up -d
docker compose logs -f web
docker compose exec web python manage.py migrate
docker compose down
```

## Советы

- PowerShell 7 + Windows Terminal удобнее классической консоли.
- Git Bash — если привычнее Unix-команды.
- WSL2 даёт полноценное Linux-окружение с лучшей совместимостью с Django.
