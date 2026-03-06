# 🔧 Исправлено: Конфигурация для Windows

## Дата: 2026-03-06

---

## ❌ Проблема

При попытке запустить задачу Django в VS Code (`Ctrl+Shift+B`) появлялась ошибка:
```
Python was not found; run without arguments to install from the Microsoft Store
```

**Причина:** Конфигурационные файлы были настроены для Linux/Mac, использовали неправильные пути для Windows.

---

## ✅ Что исправлено

### 1. `.vscode/tasks.json`
**Было:**
```json
"command": "python"
```

**Стало:**
```json
"command": "${command:python.interpreterPath}"
```

**Результат:** Теперь использует Python интерпретатор, выбранный в VS Code (из venv).

---

### 2. `.vscode/settings.json`
**Было:**
```json
"python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python"
```

**Стало:**
```json
"python.defaultInterpreterPath": "${workspaceFolder}\\venv\\Scripts\\python.exe"
```

**Результат:** Правильный путь для Windows.

---

### 3. `.vscode/launch.json`
**Добавлено:**
```json
"python": "${command:python.interpreterPath}",
"env": {
  "PYTHONPATH": "${workspaceFolder}"
}
```

**Результат:** Отладка теперь использует правильный Python и PYTHONPATH.

---

### 4. Создан `WINDOWS_SETUP.md`
Подробное руководство по настройке и troubleshooting для Windows.

---

## 🎯 Что делать сейчас (2 минуты)

### Шаг 1: Выбрать Python интерпретатор
1. Нажми `Ctrl+Shift+P`
2. Найди "Python: Select Interpreter"
3. Выбери `.\venv\Scripts\python.exe`
4. Проверь статус бар внизу: должно быть `Python 3.x.x ('venv')`

### Шаг 2: Перезапустить VS Code
1. Закрой VS Code
2. Открой снова: `code .`

### Шаг 3: Попробовать запустить
1. Нажми `Ctrl+Shift+B`
2. Должен запуститься Django сервер
3. Открой http://127.0.0.1:8000

---

## 🐛 Если всё ещё не работает

### Вариант 1: Через терминал
```powershell
# Активировать venv
.\venv\Scripts\activate

# Запустить сервер
python manage.py runserver
```

### Вариант 2: Проверить venv
```powershell
# Проверить существует ли Python в venv
dir venv\Scripts\python.exe

# Если нет - создать заново
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Вариант 3: Разрешить выполнение скриптов
```powershell
# Если ошибка "cannot be loaded because running scripts is disabled"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## ✅ Проверка что всё работает

### 1. Python интерпретатор выбран
- Статус бар (внизу справа): `Python 3.x.x ('venv')`

### 2. Задачи работают
- `Ctrl+Shift+B` → запускается сервер
- `Ctrl+Shift+P` → Tasks: Run Task → видны все задачи

### 3. Отладка работает
- `F5` → запускается Django с debugger
- Breakpoints останавливают выполнение

### 4. Django работает
```powershell
python manage.py check
# System check identified no issues (0 silenced).
```

---

## 📋 Все исправленные файлы

1. ✅ `.vscode/tasks.json` - использует Python из VS Code
2. ✅ `.vscode/settings.json` - Windows пути
3. ✅ `.vscode/launch.json` - явный Python интерпретатор
4. ✅ `WINDOWS_SETUP.md` - руководство для Windows

---

## 🚀 Следующие шаги

После того как всё заработает:

1. **Прочитать документацию:**
   - `docs/CLAUDE_OPTIMIZATION_GUIDE.md` - как работать с Claude
   - `docs/VSCODE_QUICKSTART.md` - как использовать VS Code
   - `QUICK_REFERENCE.md` - шпаргалка команд

2. **Попробовать функции:**
   - `Ctrl+Shift+B` - запустить сервер
   - `F5` - запустить с debugger
   - `F9` - поставить breakpoint
   - `Ctrl+Shift+P` → Tasks - все доступные задачи

3. **Установить Cline Extension:**
   - Extensions → Search "Cline"
   - Install
   - Попробовать: "Найди все TODO в проекте"

---

## 💡 Полезные команды для Windows

```powershell
# Активация venv
.\venv\Scripts\activate

# Запуск сервера
python manage.py runserver

# Миграции
python manage.py makemigrations
python manage.py migrate

# Тесты
python manage.py test

# Shell
python manage.py shell

# Проверка
python manage.py check
```

---

## 📞 Если нужна помощь

1. Проверь `WINDOWS_SETUP.md` - там подробный troubleshooting
2. Проверь что Python 3.11+ установлен: `python --version`
3. Проверь что venv создан: `dir venv\Scripts\python.exe`
4. Попробуй запустить через терминал напрямую

---

**Статус:** ✅ Исправлено и готово к использованию

**Следующий шаг:** Выбрать Python интерпретатор в VS Code и перезапустить.
