# Windows Setup Guide - LootLink

## Исправлено: Python не найден

Обновлены конфигурационные файлы для Windows:
- `.vscode/tasks.json` - использует Python из VS Code
- `.vscode/settings.json` - Windows пути

---

## Следующие шаги (5 минут)

### Шаг 1: Выбрать Python интерпретатор

1. **Открой Command Palette:**
   - Нажми `Ctrl+Shift+P`

2. **Найди "Python: Select Interpreter":**
   - Начни печатать "Python: Select"
   - Выбери "Python: Select Interpreter"

3. **Выбери Python из venv:**
   - Должен быть вариант: `.\venv\Scripts\python.exe`
   - Если нет, нажми "Enter interpreter path..." и укажи:
     ```
     D:\LootLink---Marketplace\venv\Scripts\python.exe
     ```

4. **Проверь статус бар:**
   - Внизу справа должно появиться: `Python 3.x.x ('venv')`

---

### Шаг 2: Перезапустить VS Code

1. Закрой VS Code полностью
2. Открой снова:
   ```powershell
   cd D:\LootLink---Marketplace
   code .
   ```

---

### Шаг 3: Запустить сервер

1. **Через задачу:**
   - Нажми `Ctrl+Shift+B`
   - Или `Ctrl+Shift+P` → "Tasks: Run Task" → "Django: Run Server"

2. **Через терминал (если задача не работает):**
   ```powershell
   # Активировать venv
   .\venv\Scripts\activate

   # Запустить сервер
   python manage.py runserver
   ```

---

## 🐛 Если всё ещё не работает

### Проблема: "Python was not found"

**Решение 1: Проверить venv**
```powershell
# Проверить существует ли venv
dir venv\Scripts\python.exe

# Если нет, создать заново
python -m venv venv
```

**Решение 2: Использовать полный путь**
```powershell
# В терминале VS Code
D:\LootLink---Marketplace\venv\Scripts\python.exe manage.py runserver
```

**Решение 3: Установить Python из python.org**
- Скачать: https://www.python.org/downloads/
- Установить с галочкой "Add Python to PATH"
- Создать venv заново

---

### Проблема: "Activate.ps1 cannot be loaded"

**Решение:**
```powershell
# Разрешить выполнение скриптов (один раз)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Потом активировать venv
.\venv\Scripts\activate
```

---

### Проблема: Задачи не работают

**Решение: Использовать терминал напрямую**
```powershell
# Активировать venv
.\venv\Scripts\activate

# Команды Django
python manage.py runserver
python manage.py migrate
python manage.py shell
python manage.py test
```

---

## Проверка что всё работает

### 1. Python интерпретатор выбран
```
Статус бар (внизу справа): Python 3.x.x ('venv')
```

### 2. Venv активирован
```powershell
# В терминале должно быть:
(venv) PS D:\LootLink---Marketplace>
```

### 3. Django работает
```powershell
python manage.py check
# Должно вывести: System check identified no issues (0 silenced).
```

### 4. Сервер запускается
```powershell
python manage.py runserver
# Открыть: http://127.0.0.1:8000
```

---

## 🎯 Быстрые команды для Windows

### Активация venv
```powershell
.\venv\Scripts\activate
```

### Деактивация venv
```powershell
deactivate
```

### Запуск сервера
```powershell
python manage.py runserver
```

### Миграции
```powershell
python manage.py makemigrations
python manage.py migrate
```

### Тесты
```powershell
python manage.py test
```

### Shell
```powershell
python manage.py shell
```

### Собрать статику
```powershell
python manage.py collectstatic --noinput
```

---

## 🔍 Отладка в VS Code (Windows)

### 1. Поставить breakpoint
- Открой файл (например, `listings/views.py`)
- Кликни слева от номера строки (красная точка)
- Или нажми `F9`

### 2. Запустить с debugger
- Нажми `F5`
- Выбери "Django: Run Server"
- Сервер запустится с подключенным debugger

### 3. Использовать debugger
- `F10` - Step Over (следующая строка)
- `F11` - Step Into (войти в функцию)
- `F5` - Continue (продолжить)
- Смотри значения переменных в панели слева

---

## 📦 Установка зависимостей (Windows)

### Если нужно переустановить всё:

```powershell
# 1. Удалить старый venv
Remove-Item -Recurse -Force venv

# 2. Создать новый venv
python -m venv venv

# 3. Активировать
.\venv\Scripts\activate

# 4. Обновить pip
python -m pip install --upgrade pip

# 5. Установить зависимости
pip install -r requirements.txt

# 6. Установить dev зависимости (опционально)
pip install -r requirements-dev.txt

# 7. Миграции
python manage.py migrate

# 8. Запустить сервер
python manage.py runserver
```

---

## 🚀 Альтернатива: Использовать Docker

Если проблемы с Python на Windows, можно использовать Docker:

```powershell
# Запустить всё в Docker
docker-compose up -d

# Посмотреть логи
docker-compose logs -f web

# Выполнить команду в контейнере
docker-compose exec web python manage.py migrate

# Остановить
docker-compose down
```

---

## 💡 Советы для Windows

### 1. Используй PowerShell 7
- Лучше чем старый PowerShell
- Уже установлен (видно в ошибке)

### 2. Используй Windows Terminal
- Современный терминал от Microsoft
- Поддержка вкладок
- Скачать: Microsoft Store → "Windows Terminal"

### 3. Git Bash как альтернатива
- Если привык к Linux командам
- Устанавливается с Git for Windows

### 4. WSL2 для Linux окружения
- Windows Subsystem for Linux
- Полноценный Linux внутри Windows
- Лучшая совместимость с Django

---

## 📞 Что делать если ничего не помогло

1. **Проверь версию Python:**
   ```powershell
   python --version
   # Должно быть 3.11+
   ```

2. **Проверь PATH:**
   ```powershell
   $env:PATH -split ';' | Select-String python
   ```

3. **Переустанови Python:**
   - Удали через "Add or Remove Programs"
   - Скачай с python.org
   - Установи с галочкой "Add Python to PATH"

4. **Используй Docker:**
   - Проще чем настраивать Python на Windows
   - Всё уже настроено в docker-compose.yml

---

## Чеклист готовности

- [ ] Python 3.11+ установлен
- [ ] venv создан и активирован
- [ ] Зависимости установлены
- [ ] Python интерпретатор выбран в VS Code
- [ ] `python manage.py check` работает
- [ ] `python manage.py runserver` запускается
- [ ] http://127.0.0.1:8000 открывается
- [ ] Задачи VS Code работают (`Ctrl+Shift+B`)
- [ ] Отладка работает (`F5`)

---

**Если всё работает - готово! Можно разрабатывать.**

**Если нет - напиши какая именно ошибка, помогу разобраться.**
