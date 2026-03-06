# 🚨 Критическая проблема: venv не создан

## Проблема

VS Code использует глобальный Python из `uv`:
```
C:\Users\ivanp\AppData\Roaming\uv\python\cpython-3.14.3-windows-x86_64-none\python.exe
```

А должен использовать Python из venv, где установлен Django.

**Вероятная причина:** venv не создан или создан неправильно.

---

## Решение: Создать venv заново

### Шаг 1: Открыть PowerShell в VS Code

1. В VS Code нажми `` Ctrl+` `` (открыть терминал)
2. Или: Terminal → New Terminal

### Шаг 2: Создать venv

```powershell
# Перейти в папку проекта (если не там)
cd D:\LootLink---Marketplace

# Создать venv
python -m venv venv

# Или если python не работает, попробуй:
py -m venv venv
```

### Шаг 3: Активировать venv

```powershell
# Активировать
.\venv\Scripts\activate

# Должно появиться (venv) в начале строки:
# (venv) PS D:\LootLink---Marketplace>
```

**Если ошибка "cannot be loaded":**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
```

### Шаг 4: Установить зависимости

```powershell
# Обновить pip
python -m pip install --upgrade pip

# Установить Django и всё остальное
pip install -r requirements.txt

# Проверить что Django установлен
python -c "import django; print(f'Django {django.VERSION} installed')"
```

### Шаг 5: Выбрать Python в VS Code

1. Нажми `Ctrl+Shift+P`
2. Найди "Python: Select Interpreter"
3. Выбери `.\venv\Scripts\python.exe` (должен появиться после создания venv)
4. Если не видишь - нажми "Enter interpreter path..." и укажи:
   ```
   D:\LootLink---Marketplace\venv\Scripts\python.exe
   ```

### Шаг 6: Перезапустить VS Code

1. Закрыть VS Code полностью
2. Открыть снова:
   ```powershell
   cd D:\LootLink---Marketplace
   code .
   ```

### Шаг 7: Проверить что работает

```powershell
# В терминале VS Code (с активированным venv)
python manage.py check

# Должно вывести:
# System check identified no issues (0 silenced).
```

### Шаг 8: Запустить сервер

```powershell
# Через команду
python manage.py runserver

# Или через задачу VS Code
# Ctrl+Shift+B
```

---

## 🔍 Проверка что venv создан правильно

### Должны существовать файлы:

```
D:\LootLink---Marketplace\
├── venv\
│   ├── Scripts\
│   │   ├── python.exe          ← Должен быть
│   │   ├── pip.exe             ← Должен быть
│   │   ├── activate.bat        ← Должен быть
│   │   └── Activate.ps1        ← Должен быть
│   └── Lib\
│       └── site-packages\
│           └── django\         ← После pip install
```

### Проверить в PowerShell:

```powershell
# Проверить что Python есть
Test-Path venv\Scripts\python.exe

# Проверить что Django установлен
.\venv\Scripts\python.exe -c "import django; print(django.VERSION)"
```

---

## 🐛 Альтернативные решения

### Вариант 1: Использовать uv для создания venv

Если у тебя установлен `uv` (видно из пути к Python):

```powershell
# Создать venv через uv
uv venv

# Активировать
.venv\Scripts\activate

# Установить зависимости
uv pip install -r requirements.txt
```

### Вариант 2: Использовать Docker

Если проблемы с Python на Windows:

```powershell
# Запустить всё в Docker
docker-compose up -d

# Посмотреть логи
docker-compose logs -f web

# Открыть http://localhost:8000
```

### Вариант 3: Использовать WSL2

Если хочешь Linux окружение:

```powershell
# Установить WSL2
wsl --install

# Перезагрузить компьютер

# Открыть Ubuntu
wsl

# В Ubuntu:
cd /mnt/d/LootLink---Marketplace
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

---

## ❓ Почему VS Code использует не тот Python?

### Причина 1: venv не создан
- Решение: создать venv (см. выше)

### Причина 2: VS Code не знает про venv
- Решение: выбрать интерпретатор (`Ctrl+Shift+P` → Python: Select Interpreter)

### Причина 3: uv перехватывает команду python
- Решение: использовать полный путь `.\venv\Scripts\python.exe`

### Причина 4: Неправильный PATH
- Решение: активировать venv перед запуском команд

---

## Чеклист

- [ ] venv создан: `Test-Path venv\Scripts\python.exe` → True
- [ ] venv активирован: в терминале видно `(venv)`
- [ ] Django установлен: `python -c "import django"` → без ошибок
- [ ] Python выбран в VS Code: статус бар показывает `Python 3.x.x ('venv')`
- [ ] `python manage.py check` работает
- [ ] `python manage.py runserver` запускается

---

## 🎯 Быстрое решение (5 минут)

```powershell
# 1. Создать venv
python -m venv venv

# 2. Активировать
.\venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Проверить
python manage.py check

# 5. Запустить
python manage.py runserver
```

Потом в VS Code:
- `Ctrl+Shift+P` → Python: Select Interpreter → `.\venv\Scripts\python.exe`
- Перезапустить VS Code

---

## 📞 Если ничего не помогает

1. **Проверь версию Python:**
   ```powershell
   python --version
   py --version
   ```

2. **Проверь что requirements.txt существует:**
   ```powershell
   Test-Path requirements.txt
   ```

3. **Попробуй создать venv с другим именем:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

4. **Используй Docker** - проще всего для Windows

---

**Следующий шаг:** Создать venv и установить зависимости (команды выше).
