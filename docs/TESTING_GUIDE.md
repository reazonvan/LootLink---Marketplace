# 🧪 Гайд по тестированию LootLink

## Оглавление

1. [Запуск тестов](#запуск-тестов)
2. [Smoke проверки production](#smoke-проверки-production)
3. [Типы тестов](#типы-тестов)
4. [Написание тестов](#написание-тестов)
5. [Coverage](#coverage)
6. [CI/CD](#cicd)

---

## Запуск тестов

### Все тесты

```bash
# С Django test runner
python manage.py test

# С pytest (рекомендуется)
pytest

# С выводом
pytest -v

# С coverage
pytest --cov=. --cov-report=html
```

### Конкретное приложение

```bash
# Только accounts
pytest accounts/

# Только chat
pytest chat/tests.py

# Только models
pytest accounts/tests.py::AccountsModelsTest
```

### Один тест

```bash
pytest accounts/tests.py::AccountsModelsTest::test_user_creation
```

---

## Smoke проверки production

Эти проверки нужны для быстрого регресса после деплоя: редиректы, SEO-теги, авторизация, базовая валидация форм и целостность ключевых счетчиков.

### Подготовка QA данных (один раз на среду)

Создайте/обновите тестовых пользователей и базовые данные для e2e-потоков:

```bash
python manage.py setup_smoke_data \
  --seller-username "<seller_username>" \
  --seller-email "<seller_email>" \
  --seller-password "<seller_password>" \
  --buyer-username "<buyer_username>" \
  --buyer-email "<buyer_email>" \
  --buyer-password "<buyer_password>"
```

Команда идемпотентная: повторный запуск не создает дубликаты и поддерживает baseline-данные в актуальном состоянии.

### PowerShell smoke

```powershell
.\scripts\smoke_prod.ps1 -Domain lootlink.ru -WwwDomain www.lootlink.ru
```

Что проверяется:
- доступность ключевых страниц и файлов (`/`, `/catalog/`, `/robots.txt`, `/sitemap.xml`, `/manifest.json`);
- канонические редиректы (`www -> apex` с кодом `308`, `http -> https` с кодом `308`);
- наличие SEO-разметки (`canonical`, `manifest`, `SearchAction`);
- консистентность счетчика активных пользователей (главная vs логин);
- негативные auth-сценарии (невалидный логин и регистрация с несовпадающими паролями должны возвращать ошибки на форме).

### Browser smoke (Playwright)

Установка зависимостей (один раз):

```bash
pip install -r requirements/development.txt
python -m playwright install chromium
```

Запуск:

```bash
python scripts/playwright_smoke.py --base-url https://lootlink.ru
```

Опциональная проверка входа реальным пользователем:

```bash
python scripts/playwright_smoke.py \
  --base-url https://lootlink.ru \
  --login-username "<username_or_email>" \
  --login-password "<password>"
```

Проверки Playwright включают:
- отсутствие JS-ошибок и same-origin request failures;
- layout-check страницы входа на desktop и mobile (без горизонтального “растягивания”);
- видимость сообщения об ошибке при невалидном логине;
- консистентность счетчика активных пользователей (главная vs логин);
- редирект `www -> apex` со статусом `308`.

### Browser user journeys (Playwright)

Отдельный скрипт для бизнес-потоков авторизованных пользователей:

```bash
python scripts/playwright_user_journey.py \
  --base-url https://lootlink.ru \
  --seller-username "<seller_username>" \
  --seller-password "<seller_password>" \
  --buyer-username "<buyer_username>" \
  --buyer-password "<buyer_password>"
```

Сценарии:
- продавец логинится и создает новое объявление;
- покупатель открывает объявление, стартует чат и отправляет сообщение;
- покупатель отправляет запрос на покупку.

Можно также передать креды через переменные окружения:
- `SMOKE_SELLER_USERNAME`
- `SMOKE_SELLER_PASSWORD`
- `SMOKE_BUYER_USERNAME`
- `SMOKE_BUYER_PASSWORD`

### Post-deploy запуск через GitHub Actions

В репозитории добавлен workflow: `.github/workflows/post-deploy-smoke.yml`.

Он умеет:
- запускаться вручную (`workflow_dispatch`);
- запускаться через `repository_dispatch` с событием `post_deploy_smoke`.

Минимальные secrets для полного набора проверок:
- `SMOKE_SELLER_USERNAME`
- `SMOKE_SELLER_PASSWORD`
- `SMOKE_BUYER_USERNAME`
- `SMOKE_BUYER_PASSWORD`

Дополнительно для проверки логина в `playwright_smoke.py`:
- `SMOKE_LOGIN_USERNAME`
- `SMOKE_LOGIN_PASSWORD`

---

## Типы тестов

### Unit Tests

Тестируют отдельные компоненты (модели, формы, функции).

**Примеры:**
- `accounts/tests.py` - тесты пользователей и профилей
- `listings/tests.py` - тесты объявлений и игр
- `transactions/tests.py` - тесты сделок и отзывов
- `chat/tests.py` - тесты чата
- `core/tests.py` - тесты уведомлений

### Integration Tests

Тестируют взаимодействие между компонентами.

**Пример:**
```python
def test_complete_purchase_flow(self):
    # 1. Покупатель находит товар
    # 2. Отправляет запрос
    # 3. Продавец принимает
    # 4. Завершает сделку
    # 5. Покупатель оставляет отзыв
    # 6. Рейтинг обновляется
```

### View Tests

Тестируют HTTP запросы и ответы.

```python
def test_listing_create_view(self):
    self.client.login(username='testuser', password='testpass123')
    response = self.client.post(reverse('listings:listing_create'), {
        'title': 'Test Item',
        'description': 'Test description',
        'game': self.game.id,
        'price': 100
    })
    
    self.assertEqual(response.status_code, 302)
    self.assertTrue(Listing.objects.filter(title='Test Item').exists())
```

---

## Написание тестов

### Структура теста

```python
from django.test import TestCase

class MyFeatureTest(TestCase):
    """Описание набора тестов."""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом."""
        # Создание пользователей, объектов и т.д.
        pass
    
    def tearDown(self):
        """Очистка после теста (опционально)."""
        pass
    
    def test_something(self):
        """Описание конкретного теста."""
        # Arrange - подготовка данных
        user = CustomUser.objects.create_user(...)
        
        # Act - выполнение действия
        result = some_function(user)
        
        # Assert - проверка результата
        self.assertEqual(result, expected_value)
```

### Best Practices

1. **Один тест = одна проверка**
   ```python
   # Плохо
   def test_user(self):
       self.assertEqual(user.username, 'test')
       self.assertTrue(user.is_active)
       self.assertIsNotNone(user.profile)
   
   # Хорошо
   def test_user_creation(self):
       self.assertEqual(user.username, 'test')
   
   def test_user_is_active_by_default(self):
       self.assertTrue(user.is_active)
   
   def test_profile_auto_created(self):
       self.assertIsNotNone(user.profile)
   ```

2. **Используйте фикстуры**
   ```python
   def setUp(self):
       self.user = self.create_user()
       self.game = self.create_game()
   
   def create_user(self, username='testuser'):
       return CustomUser.objects.create_user(...)
   ```

3. **Тестируйте граничные случаи**
   ```python
   def test_empty_description(self):
       # Что если описание пустое?
   
   def test_negative_price(self):
       # Что если цена отрицательная?
   
   def test_duplicate_listing(self):
       # Что если создать дубликат?
   ```

---

## Coverage

### Генерация отчета

```bash
# HTML отчет
pytest --cov=. --cov-report=html

# Открыть в браузере
# Windows:
start htmlcov/index.html
# Linux:
xdg-open htmlcov/index.html
```

### Целевой coverage

- **Минимум:** 70%
- **Цель:** 80%
- **Идеал:** 90%+

### Что не считается

```python
# pytest.ini
omit = 
    */migrations/*
    */tests/*
    manage.py
```

---

## CI/CD

### GitHub Actions

При каждом push/PR автоматически запускаются:

1. **Lint** - проверка стиля кода
2. **Security** - сканирование уязвимостей
3. **Tests** - unit тесты
4. **Coverage** - отчет о покрытии
5. **Build** - сборка Docker образа

### Локальная проверка перед push

```bash
# Форматирование
black .
isort .

# Линтеры
flake8 .

# Тесты
pytest

# Django checks
python manage.py check --deploy
```

---

## Примеры тестов

### Model Test

```python
def test_listing_creation(self):
    listing = Listing.objects.create(
        seller=self.user,
        game=self.game,
        title='Test Item',
        description='Test description',
        price=100
    )
    
    self.assertEqual(listing.status, 'active')
    self.assertTrue(listing.is_available())
```

### View Test

```python
def test_listing_create_requires_login(self):
    response = self.client.get(reverse('listings:listing_create'))
    self.assertEqual(response.status_code, 302)
    self.assertRedirects(response, '/accounts/login/?next=/listing/create/')
```

### Form Test

```python
def test_listing_form_valid(self):
    form = ListingCreateForm(data={
        'game': self.game.id,
        'title': 'Test',
        'description': 'Test description',
        'price': 100
    })
    self.assertTrue(form.is_valid())
```

### API Test

```python
def test_get_new_messages_api(self):
    response = self.client.get(
        f'/chat/api/messages/{conversation.id}/',
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertIn('messages', data)
```

---

## Troubleshooting

### Тесты не находятся

```bash
# Проверьте pytest.ini
[pytest]
python_files = tests.py test_*.py
testpaths = accounts chat core listings transactions
```

### База данных не очищается

```bash
# Используйте --reuse-db для скорости
pytest --reuse-db

# Или пересоздайте БД
pytest --create-db
```

### Coverage неточный

```bash
# Убедитесь что файлы не в omit списке
# pytest.ini
omit = 
    */migrations/*
    */tests/*
```

---

## Полезные команды

```bash
# Запустить только failed тесты
pytest --lf

# Остановиться на первой ошибке
pytest -x

# Показать 10 самых медленных тестов
pytest --durations=10

# Параллельное выполнение (требует pytest-xdist)
pytest -n auto

# Только тесты с определенной меткой
pytest -m "slow"
```

---

**Удачи с тестированием! 🧪**

