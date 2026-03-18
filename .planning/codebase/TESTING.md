# Testing Patterns

**Analysis Date:** 2026-03-18

## Test Framework

**Runner:**
- pytest 7.x with Django plugin (`pytest-django`)
- Configuration: `pyproject.toml` [tool.pytest.ini_options]
- Django settings module: `lootlink.settings`

**Assertion Library:**
- pytest built-in assertions
- pytest.raises() for exception testing

**Run Commands:**
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest -m "not slow"            # Skip slow tests
pytest --cov=.                  # Run with coverage
pytest --cov-report=html        # Generate HTML coverage report
pytest tests/                   # Run specific directory
pytest accounts/test_models.py  # Run specific file
```

## Test File Organization

**Location:**
- Co-located with source code: `accounts/test_models.py`, `accounts/test_views.py`, `accounts/test_forms.py`
- Separate integration tests directory: `tests/test_security_comprehensive.py`
- Pattern: Tests live in same app directory as code being tested

**Naming:**
- Test files: `test_*.py` or `*_test.py`
- Test classes: `Test*` (e.g., `TestCustomUserModel`, `TestRegistrationView`)
- Test functions: `test_*` (e.g., `test_create_user`, `test_user_email_unique`)

**Structure:**
```
accounts/
├── models.py
├── views.py
├── forms.py
├── test_models.py          # Unit tests for models
├── test_views.py           # Unit tests for views
├── test_forms.py           # Unit tests for forms
├── test_verification.py    # Feature-specific tests
└── tests_push.py           # Feature-specific tests

tests/
└── test_security_comprehensive.py  # Integration/security tests
```

## Test Structure

**Suite Organization:**
```python
@pytest.mark.django_db
class TestCustomUserModel:
    """Тесты модели CustomUser."""

    def test_create_user(self):
        """Создание пользователя."""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
```

**Patterns:**
- Setup: Use pytest fixtures (see Fixtures section)
- Teardown: Automatic via pytest-django with @pytest.mark.django_db
- Assertion: Direct pytest assertions (`assert condition`)
- Database: @pytest.mark.django_db decorator for database access

**Markers:**
```python
@pytest.mark.django_db        # Requires database access
@pytest.mark.slow             # Marks as slow test
@pytest.mark.integration      # Integration test
@pytest.mark.unit             # Unit test
```

## Mocking

**Framework:** pytest fixtures for test data and setup

**Patterns:**
```python
@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )

@pytest.fixture
def verified_user(db):
    user = User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )
    # Additional setup for verified user
    return user

@pytest.fixture
def authenticated_client(client, verified_user):
    client.force_login(verified_user)
    return client
```

**What to Mock:**
- External API calls (email, SMS, payment services)
- File uploads (use temporary files)
- Time-dependent operations (use freezegun or mock.patch)
- Database queries that are expensive

**What NOT to Mock:**
- Django ORM operations (use test database)
- Authentication/authorization (use fixtures)
- Form validation (test actual validation logic)
- Model methods (test actual implementation)

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def client():
    return Client()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123'
    )

@pytest.fixture
def moderator(db):
    user = User.objects.create_user(
        username='moderator',
        email='mod@test.com',
        password='modpass123',
        is_staff=True
    )
    user.profile.is_moderator = True
    user.profile.save()
    return user
```

**Location:**
- Fixtures defined in test files or in `conftest.py` (if shared across multiple test files)
- No factory_boy or factory pattern currently used
- Direct model creation with `.create_user()` or `.objects.create()`

## Coverage

**Requirements:**
- Target coverage not explicitly enforced
- Coverage reports generated in HTML and term-missing format

**View Coverage:**
```bash
pytest --cov=. --cov-report=html
# Opens htmlcov/index.html in browser
```

**Coverage Configuration:**
- Source: all files (`.`)
- Omit: migrations, tests, venv, manage.py, wsgi.py, asgi.py
- Exclude lines: pragma: no cover, __repr__, raise AssertionError, raise NotImplementedError, if __name__ == '__main__', if TYPE_CHECKING, abstract methods

## Test Types

**Unit Tests:**
- Scope: Individual models, forms, utilities
- Location: `accounts/test_models.py`, `accounts/test_forms.py`
- Approach: Test single function/method in isolation
- Example: `test_create_user()`, `test_user_email_unique()`, `test_valid_form()`

**Integration Tests:**
- Scope: Views, API endpoints, multiple components
- Location: `accounts/test_views.py`, `api/tests_idor.py`
- Approach: Test full request/response cycle
- Example: `test_registration_page_get()`, `test_successful_registration()`

**Security Tests:**
- Scope: Authentication, authorization, IDOR prevention
- Location: `tests/test_security_comprehensive.py`, `api/tests_idor.py`
- Approach: Test security constraints and edge cases
- Example: `test_secret_key_is_secure()`, `test_api_has_throttling()`

**E2E Tests:**
- Framework: Not currently used
- Could be added with Selenium or Playwright for browser automation

## Common Patterns

**Async Testing:**
```python
# Not heavily used yet
# When needed, use pytest-asyncio or pytest-django async support
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == expected
```

**Error Testing:**
```python
def test_user_email_unique(self):
    """Email должен быть уникальным."""
    CustomUser.objects.create_user(
        username='user1',
        email='test@example.com',
        password='pass123'
    )

    with pytest.raises(Exception):
        CustomUser.objects.create_user(
            username='user2',
            email='test@example.com',
            password='pass123'
        )

def test_user_cannot_be_deleted(self):
    """Пользователя нельзя удалить."""
    user = CustomUser.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

    with pytest.raises(Exception) as exc_info:
        user.delete()
    assert 'Удаление пользователей запрещено' in str(exc_info.value)
```

**Form Validation Testing:**
```python
def test_duplicate_email(self, verified_user):
    """Дубликат email."""
    data = {
        'username': 'anotheruser',
        'email': verified_user.email,
        'phone': '+7 (999) 123-45-68',
        'password1': 'complexP@ss123',
        'password2': 'complexP@ss123',
    }
    form = CustomUserCreationForm(data=data)
    assert not form.is_valid()
    assert 'email' in form.errors
```

**View Testing:**
```python
def test_registration_page_get(self, client):
    """GET запрос на страницу регистрации."""
    response = client.get(reverse('accounts:register'))
    assert response.status_code == 200
    assert 'Регистрация' in response.content.decode()

def test_successful_registration(self, client):
    """Успешная регистрация."""
    data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'phone': '+7 (999) 123-45-67',
        'password1': 'complexP@ss123',
        'password2': 'complexP@ss123',
    }
    response = client.post(reverse('accounts:register'), data)

    assert response.status_code == 302
    assert CustomUser.objects.filter(username='newuser').exists()
    assert '_auth_user_id' in client.session
```

**API Testing:**
```python
def test_api_has_throttling(self):
    """API должен иметь throttling классы."""
    from django.conf import settings
    throttle_classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
    assert len(throttle_classes) > 0
```

---

*Testing analysis: 2026-03-18*
