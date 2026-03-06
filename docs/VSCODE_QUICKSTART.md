# LootLink VS Code Quick Start

## Первый запуск

### 1. Установка рекомендованных расширений
При открытии проекта VS Code предложит установить рекомендованные расширения.
Нажмите "Install All" или установите вручную через Extensions (Ctrl+Shift+X).

### 2. Активация виртуального окружения
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

VS Code автоматически определит интерпретатор Python из venv.

---

## Горячие клавиши

### Запуск задач
- `Ctrl+Shift+B` - Запустить Django сервер (задача по умолчанию)
- `Ctrl+Shift+P` → "Tasks: Run Task" - Выбрать любую задачу

### Отладка
- `F5` - Запустить отладку (Django сервер с debugger)
- `F9` - Установить breakpoint
- `F10` - Step over
- `F11` - Step into
- `Shift+F11` - Step out

### Навигация
- `Ctrl+P` - Быстрый поиск файлов
- `Ctrl+Shift+F` - Поиск по всему проекту
- `F12` - Перейти к определению
- `Alt+F12` - Peek определение
- `Shift+F12` - Найти все ссылки

### Редактирование
- `Ctrl+D` - Выделить следующее вхождение
- `Ctrl+Shift+L` - Выделить все вхождения
- `Alt+Click` - Множественные курсоры
- `Ctrl+/` - Закомментировать/раскомментировать
- `Shift+Alt+F` - Форматировать документ

---

## Доступные задачи (Tasks)

### Django команды:
1. **Django: Run Server** - `python manage.py runserver`
2. **Django: Run Tests** - `python manage.py test`
3. **Django: Make Migrations** - `python manage.py makemigrations`
4. **Django: Migrate** - `python manage.py migrate`
5. **Django: Collect Static** - `python manage.py collectstatic --noinput`
6. **Django: Shell** - `python manage.py shell`
7. **Django: Check** - `python manage.py check`

### Celery команды:
8. **Celery: Start Worker** - Запустить Celery worker
9. **Celery: Start Beat** - Запустить Celery beat scheduler

### Docker команды:
10. **Docker: Up** - `docker-compose up -d`
11. **Docker: Down** - `docker-compose down`
12. **Docker: Logs** - `docker-compose logs -f`

### Pytest команды:
13. **Pytest: Run All** - Запустить все тесты
14. **Pytest: Run with Coverage** - Тесты с покрытием кода

---

## Конфигурации отладки (Launch)

### 1. Django: Run Server
Запускает Django сервер с подключенным debugger.
Можно ставить breakpoints в views, models, etc.

### 2. Django: Run Tests
Запускает тесты с debugger.
Можно отлаживать тестовый код.

### 3. Django: Shell
Запускает Django shell с debugger.
Полезно для отладки сложных запросов.

### 4. Python: Current File
Запускает текущий открытый Python файл.

### 5. Pytest: Current File
Запускает тесты из текущего файла.

---

## Типичные сценарии работы

### Создание новой функции

1. **Создать ветку:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Написать код:**
   - VS Code автоматически форматирует при сохранении (Black)
   - Pylint показывает ошибки в реальном времени

3. **Запустить сервер для тестирования:**
   - `Ctrl+Shift+B` → Django: Run Server
   - Или `F5` для запуска с debugger

4. **Написать тесты:**
   - Создать файл `test_*.py`
   - Запустить: Tasks → Django: Run Tests

5. **Проверить покрытие:**
   - Tasks → Pytest: Run with Coverage
   - Открыть `htmlcov/index.html`

6. **Закоммитить:**
   ```bash
   git add .
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

---

### Отладка бага

1. **Найти проблемное место:**
   - `Ctrl+Shift+F` - поиск по проекту
   - GitLens показывает кто и когда менял код

2. **Поставить breakpoint:**
   - `F9` на нужной строке
   - Или кликнуть слева от номера строки

3. **Запустить с debugger:**
   - `F5` → Django: Run Server
   - Воспроизвести баг

4. **Исследовать:**
   - Смотреть значения переменных
   - `F10` - шаг за шагом
   - Debug Console - выполнять код

5. **Исправить и протестировать:**
   - Написать тест, который воспроизводит баг
   - Исправить код
   - Убедиться что тест проходит

---

### Работа с базой данных

1. **Создать миграцию:**
   - Tasks → Django: Make Migrations
   - Проверить созданный файл миграции

2. **Применить миграцию:**
   - Tasks → Django: Migrate

3. **Проверить состояние:**
   - Tasks → Django: Show Migrations

4. **Работа с данными:**
   - Tasks → Django: Shell
   - Или использовать PostgreSQL extension для SQL запросов

---

### Работа с Docker

1. **Запустить контейнеры:**
   - Tasks → Docker: Up

2. **Посмотреть логи:**
   - Tasks → Docker: Logs

3. **Остановить:**
   - Tasks → Docker: Down

---

## Полезные расширения

### Python (Microsoft)
- IntelliSense (автодополнение)
- Linting (проверка кода)
- Debugging (отладка)
- Testing (запуск тестов)

### Django (Baptiste Darthenay)
- Подсветка синтаксиса Django шаблонов
- Автодополнение тегов и фильтров
- Snippets для быстрого написания кода

### GitLens (Eric Amodio)
- Blame annotations (кто менял строку)
- История файла
- Сравнение веток
- Git graph

### Thunder Client (Ranga Vadhineni)
- Тестирование API
- Сохранение запросов
- Переменные окружения
- Альтернатива Postman

### Error Lens (Alexander)
- Показывает ошибки прямо в коде
- Не нужно смотреть в панель Problems
- Цветовая индикация серьезности

### Todo Tree (Gruntfuggly)
- Находит все TODO, FIXME, BUG в проекте
- Древовидная структура
- Быстрая навигация

---

## Настройки форматирования

### Python (Black)
- Длина строки: 100 символов
- Автоформатирование при сохранении
- Автосортировка импортов

### Django Templates
- Tab size: 2 пробела
- Форматирование отключено (чтобы не ломать теги)

### JavaScript (Prettier)
- Автоформатирование при сохранении
- Стандартные настройки Prettier

---

## Troubleshooting

### VS Code не видит Python интерпретатор
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Выбрать `./venv/bin/python`

### Не работает автодополнение Django
1. Убедиться что установлен Django extension
2. Проверить что файлы имеют расширение `.html` (не `.django`)
3. Перезапустить VS Code

### Не работают задачи (Tasks)
1. Убедиться что находитесь в корне проекта
2. Проверить что файл `.vscode/tasks.json` существует
3. Попробовать: `Ctrl+Shift+P` → "Tasks: Run Task"

### Медленно работает IntelliSense
1. Исключить папки из индексации (уже настроено в settings.json)
2. Перезапустить Python Language Server: `Ctrl+Shift+P` → "Python: Restart Language Server"

### Не работает отладка
1. Убедиться что установлен debugpy: `pip install debugpy`
2. Проверить конфигурацию в `.vscode/launch.json`
3. Попробовать запустить без `--noreload`

---

## Советы по производительности

### 1. Исключить ненужные папки
Уже настроено в `settings.json`:
- `__pycache__`
- `node_modules`
- `venv`
- `staticfiles`
- `media`

### 2. Использовать Workspace
Сохранить проект как Workspace:
- File → Save Workspace As...
- Быстрое переключение между проектами

### 3. Использовать Multi-root Workspace
Если работаете с frontend отдельно:
- File → Add Folder to Workspace
- Можно добавить папку с React/Vue приложением

### 4. Настроить Git
Уже настроено:
- Автоматический fetch
- Smart commit
- Без подтверждения sync

---

## Интеграция с Claude (Cline Extension)

### Установка
1. Extensions → Search "Cline"
2. Install
3. Перезапустить VS Code

### Использование
1. Открыть Cline панель (иконка в Activity Bar)
2. Ввести задачу на естественном языке
3. Подтвердить действия

### Примеры задач:
- "Создай тесты для модели Profile"
- "Добавь кеширование в view games_catalog_alphabetical"
- "Найди все TODO в проекте"
- "Оптимизируй запросы в listings/views.py"

---

## Дополнительные ресурсы

- [VS Code Django Tutorial](https://code.visualstudio.com/docs/python/tutorial-django)
- [VS Code Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [Django Documentation](https://docs.djangoproject.com/)
- [Black Formatter](https://black.readthedocs.io/)

---

**Готово к работе!** 🚀
