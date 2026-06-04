# Проблемы на Windows

Частые проблемы запуска на Windows. Проблемы именно с venv (не создаётся, выбран не тот интерпретатор) — в [venv.md](venv.md).

## «Python was not found»

PATH не видит Python, либо перехватывает заглушка из Microsoft Store.

```powershell
dir venv\Scripts\python.exe                       # есть ли venv
python -m venv venv                               # создать, если нет
.\venv\Scripts\python.exe manage.py runserver     # запуск полным путём
```

Если Python не установлен — поставить с [python.org](https://www.python.org/downloads/) с галочкой «Add Python to PATH».

## «Activate.ps1 cannot be loaded ... running scripts is disabled»

PowerShell запрещает выполнение скриптов. Разрешить один раз для пользователя:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
```

## VS Code берёт не тот Python

Например, глобальный uv-Python вместо venv (в котором установлен Django):

- `Ctrl+Shift+P` → **Python: Select Interpreter** → `.\venv\Scripts\python.exe`.
- Если в списке нет — «Enter interpreter path…» и указать `D:\LootLink---Marketplace\venv\Scripts\python.exe`.
- Перезапустить VS Code.

Конфиги `.vscode/` (`tasks.json`, `launch.json`, `settings.json`) уже используют выбранный в VS Code интерпретатор и Windows-пути.

## Задачи VS Code не запускаются

Запускать напрямую в терминале с активным venv:

```powershell
.\venv\Scripts\activate
python manage.py runserver
```

## Ничего не помогает

- Версия: `python --version` (нужен 3.13+).
- PATH: `$env:PATH -split ';' | Select-String python`.
- Переустановить Python с python.org («Add Python to PATH»).
- Запустить через Docker — см. [установку на Windows](../setup/windows.md).
