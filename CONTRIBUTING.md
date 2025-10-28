# Contributing to LootLink

Спасибо за интерес к улучшению LootLink! Этот документ содержит рекомендации для разработчиков.

## 📋 Содержание

1. [Начало работы](#начало-работы)
2. [Стандарты кода](#стандарты-кода)
3. [Процесс разработки](#процесс-разработки)
4. [Тестирование](#тестирование)
5. [Pull Requests](#pull-requests)

---

## 🚀 Начало работы

### 1. Fork и клонирование репозитория

```bash
# Fork репозитория на GitHub
# Затем клонируйте ваш fork
git clone https://github.com/YOUR_USERNAME/LootLink.git
cd LootLink

# Добавьте upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/LootLink.git
```

### 2. Настройка окружения

```bash
# Создайте виртуальное окружение
python -m venv venv

# Активируйте (Windows)
venv\Scripts\activate

# Активируйте (Linux/Mac)
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Установите pre-commit hooks
pip install pre-commit
pre-commit install
```

### 3. Настройка базы данных

```bash
# Создайте PostgreSQL базу
createdb lootlink_db

# Примените миграции
python manage.py migrate

# Создайте суперпользователя
python manage.py createsuperuser

# Загрузите тестовые данные
python scripts/create_test_data.py
```

---

## 📝 Стандарты кода

### Python Style Guide

Мы следуем **PEP 8** с некоторыми модификациями:

- **Максимальная длина строки**: 120 символов
- **Форматтер**: Black
- **Сортировка импортов**: isort
- **Линтер**: Flake8

### Автоматическое форматирование

```bash
# Форматирование кода
black . --exclude="migrations|venv|env"

# Сортировка импортов
isort . --skip migrations --skip venv

# Проверка линтером
flake8 .
```

### Структура импортов

```python
# Стандартная библиотека
import os
import sys
from datetime import datetime

# Django
from django.db import models
from django.contrib.auth import get_user_model

# Сторонние библиотеки
from crispy_forms.helper import FormHelper
import boto3

# Локальные импорты
from accounts.models import CustomUser
from .models import Listing
```

### Naming Conventions

```python
# Classes - PascalCase
class UserProfile(models.Model):
    pass

# Functions/methods - snake_case
def get_user_profile(user_id):
    pass

# Constants - UPPER_CASE
MAX_FILE_SIZE = 5 * 1024 * 1024

# Private methods/attributes - _leading_underscore
def _internal_method(self):
    pass
```

---

## 🔄 Процесс разработки

### 1. Создание новой ветки

```bash
# Обновите main ветку
git checkout main
git pull upstream main

# Создайте feature ветку
git checkout -b feature/your-feature-name

# или для bugfix
git checkout -b bugfix/issue-123
```

### 2. Commit Guidelines

Используйте **Conventional Commits**:

```bash
# Format
<type>(<scope>): <description>

# Examples
feat(listings): add full-text search
fix(chat): resolve XSS vulnerability
docs(readme): update installation guide
test(accounts): add profile tests
refactor(views): optimize database queries
style(css): improve responsive design
chore(deps): update Django to 4.2.7
```

**Types:**
- `feat`: Новая функция
- `fix`: Исправление бага
- `docs`: Документация
- `style`: Форматирование кода
- `refactor`: Рефакторинг
- `test`: Тесты
- `chore`: Рутинные задачи

### 3. Перед коммитом

```bash
# Запустите тесты
python manage.py test

# Проверьте линтеры
flake8 .
black --check .
isort --check .

# Проверьте миграции
python manage.py makemigrations --check --dry-run
```

---

## 🧪 Тестирование

### Написание тестов

Каждая новая функция должна иметь тесты:

```python
# tests.py
from django.test import TestCase

class YourFeatureTest(TestCase):
    """Описание тестируемой функции."""
    
    def setUp(self):
        """Подготовка данных для тестов."""
        self.user = User.objects.create_user(...)
    
    def test_feature_works(self):
        """Тест что функция работает."""
        # Arrange
        expected = 'result'
        
        # Act
        actual = your_function()
        
        # Assert
        self.assertEqual(actual, expected)
```

### Запуск тестов

```bash
# Все тесты
python manage.py test

# Конкретное приложение
python manage.py test accounts

# Конкретный тест
python manage.py test accounts.tests.UserModelTest

# С coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Откроется htmlcov/index.html
```

### Минимальное покрытие

- **Unit tests**: 80%+
- **Integration tests**: основные user flows
- **Все новые features**: 100% покрытие

---

## 📬 Pull Requests

### Checklist перед созданием PR

- [ ] Код отформатирован (black, isort)
- [ ] Все тесты проходят
- [ ] Добавлены тесты для новой функциональности
- [ ] Документация обновлена (если нужно)
- [ ] Нет конфликтов с main веткой
- [ ] Commit messages следуют Conventional Commits
- [ ] Линтеры не выдают ошибок

### Создание Pull Request

1. **Push вашей ветки:**
```bash
git push origin feature/your-feature-name
```

2. **Создайте PR на GitHub** со следующей информацией:

```markdown
## Описание
Краткое описание изменений

## Тип изменения
- [ ] Bug fix (исправление бага)
- [ ] New feature (новая функция)
- [ ] Breaking change (изменения ломающие обратную совместимость)
- [ ] Documentation update (обновление документации)

## Как протестировано?
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist
- [ ] Код следует style guide проекта
- [ ] Self-review кода выполнен
- [ ] Комментарии добавлены где нужно
- [ ] Документация обновлена
- [ ] Нет новых warnings
- [ ] Все тесты проходят
- [ ] Coverage не понизился
```

### Code Review

Ваш PR будет проверен на:
- Качество кода
- Соответствие стандартам
- Тесты
- Документацию
- Безопасность
- Производительность

---

## 🛡️ Security

### Reporting Vulnerabilities

**НЕ создавайте public issue для уязвимостей!**

Отправьте email на: security@lootlink.com

Укажите:
- Описание уязвимости
- Шаги для воспроизведения
- Потенциальное влияние
- Предлагаемое исправление (если есть)

### Security Best Practices

1. **Никогда не коммитьте:**
   - Пароли, API ключи, секретные токены
   - `.env` файлы
   - Credentials любого вида

2. **Всегда валидируйте:**
   - Пользовательский ввод
   - Файлы (размер, тип)
   - Права доступа

3. **Используйте:**
   - Django ORM (предотвращает SQL injection)
   - Django Forms (CSRF защита)
   - Template auto-escaping (XSS защита)

---

## 📚 Полезные ресурсы

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [PostgreSQL Performance](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

## 🤝 Community

- Будьте вежливы и уважительны
- Задавайте вопросы в Discussions
- Помогайте новичкам
- Делитесь знаниями

---

## 📄 License

См. файл [LICENSE](LICENSE) для деталей.

---

**Спасибо за ваш вклад в LootLink! 🎉**
