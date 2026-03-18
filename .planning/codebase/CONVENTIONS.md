# Coding Conventions

**Analysis Date:** 2026-03-18

## Naming Patterns

**Files:**
- snake_case for all Python files: `models.py`, `views.py`, `forms.py`, `test_models.py`
- Modular organization with descriptive names: `models_security.py`, `views_2fa.py`, `tasks_export.py`
- Test files follow pattern: `test_*.py` or `*_test.py`

**Functions:**
- snake_case for all function and method names
- Examples: `clean_username()`, `perform_create()`, `get_platform_stats()`, `send_verification_email()`
- Private methods prefixed with underscore: `_validate_phone()`

**Variables:**
- snake_case for all variable names
- Descriptive names: `verified_user`, `authenticated_client`, `security_logger`
- Constants in UPPERCASE (Django settings convention)

**Types:**
- PascalCase for all class names: `CustomUser`, `Profile`, `CustomUserCreationForm`, `IsOwnerOrReadOnly`
- Model classes: `CustomUser`, `Profile`, `PasswordResetCode`, `DataExportRequest`
- Form classes: `CustomUserCreationForm`, `ProfileUpdateForm`, `PasswordResetRequestForm`
- Permission classes: `IsOwnerOrReadOnly`, `IsReviewerOrReadOnly`, `IsConversationParticipant`
- ViewSet classes: `GameViewSet`, `ListingViewSet`, `CategoryViewSet`

## Code Style

**Formatting:**
- Black formatter with line length of 100 characters
- Configuration: `pyproject.toml` [tool.black]
- Target Python version: 3.11
- Excludes: .git, .venv, migrations, build, dist

**Linting:**
- flake8 with max-line-length=120 (`.flake8`)
- Ignored rules: E203 (whitespace before ':'), E501 (line too long), W503 (line break before binary operator)
- Per-file ignores: F401 in `__init__.py` (unused imports), E501 in `settings.py`
- Max complexity: 10

**Pre-commit Hooks:**
- Black for code formatting
- isort for import sorting
- flake8 for linting
- bandit for security checks
- pydocstyle for docstring validation (Google convention)
- General file checks: trailing whitespace, end-of-file fixer, YAML/JSON validation

**EditorConfig:**
- Python files: 4-space indentation, UTF-8 charset, LF line endings
- HTML/CSS/JS: 2-space indentation
- JSON/YAML: 2-space indentation
- Configured in `.editorconfig`

## Import Organization

**Order:**
1. Future imports (`from __future__ import ...`)
2. Standard library imports (`import os`, `from datetime import ...`)
3. Django imports (`from django.db import models`, `from django.contrib.auth`)
4. Third-party imports (`from rest_framework import ...`, `from django_otp...`)
5. Local/first-party imports (`from accounts.models import ...`, `from .forms import ...`)
6. Relative imports (`.models_export`, `.models_security`)

**Path Aliases:**
- No path aliases configured; uses explicit relative and absolute imports
- Examples from codebase:
  ```python
  from accounts.models import CustomUser, Profile
  from listings.models import Listing, Game
  from .models_export import DataExportRequest
  from .models_security import SecurityAuditLog
  ```

**isort Configuration:**
- Profile: black (compatible with Black formatter)
- Line length: 100
- Known Django: django
- Sections: FUTURE, STDLIB, DJANGO, THIRDPARTY, FIRSTPARTY, LOCALFOLDER

## Error Handling

**Patterns:**
- Form validation: Use `forms.ValidationError()` with descriptive messages
  ```python
  if CustomUser.objects.filter(username__iexact=username).exists():
      raise forms.ValidationError('Пользователь с таким именем уже существует...')
  ```
- Model validation: Use `django.core.exceptions.ValidationError`
- View error handling: try/except with logging
  ```python
  try:
      form = CustomAuthenticationForm(request, data=request.POST)
      if form.is_valid():
          # process
  except Exception as e:
      logger = logging.getLogger(__name__)
      logger.error(f'Ошибка при входе: {e}')
      messages.error(request, 'Произошла ошибка при входе.')
  ```
- API error handling: REST framework exceptions (`PermissionDenied`, `ValidationError`)
- Model deletion prevention: Raise `Exception` with descriptive message
  ```python
  def delete(self, *args, **kwargs):
      raise Exception('Удаление пользователей запрещено! Аккаунты существуют навсегда.')
  ```

## Logging

**Framework:** Python's built-in `logging` module

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Security logger: `security_logger = logging.getLogger('django.security')`
- Log levels used:
  - `logger.info()` - Informational messages (successful operations)
  - `logger.warning()` - Warning messages (suspicious activity)
  - `logger.error()` - Error messages (failures, exceptions)
- Examples from codebase:
  ```python
  logger.info(f'Data export completed for user {user.username}')
  logger.error(f'Data export failed: {str(exc)}')
  security_logger.warning(f'Failed login attempt: username={username} | IP={ip}')
  security_logger.info(f'Successful login: username={user.username} | IP={ip}')
  ```

## Comments

**When to Comment:**
- Complex business logic requiring explanation
- Non-obvious validation rules
- Security-related decisions
- Workarounds or temporary solutions
- Integration points with external services

**JSDoc/TSDoc:**
- Not applicable (Python project)
- Use Google-style docstrings instead

**Docstring Convention:**
- Google-style docstrings enforced by pydocstyle
- Applied to: classes, functions, methods
- Format:
  ```python
  def clean_phone(self):
      """Валидация номера телефона с проверкой формата."""
      # implementation

  class CustomUser(AbstractUser):
      """
      Кастомная модель пользователя.
      Расширяет стандартную модель User Django.
      """
  ```

## Function Design

**Size:**
- Aim for functions under 50 lines
- Complex logic broken into smaller helper functions
- Examples: `clean_*()` methods in forms are typically 10-20 lines

**Parameters:**
- Use keyword arguments for clarity
- Avoid excessive positional arguments
- Example: `Favorite.objects.get_or_create(user=request.user, listing=listing)`

**Return Values:**
- Explicit return statements
- Return None implicitly for void operations
- Return tuples for multiple values: `created, obj = Model.objects.get_or_create(...)`
- Serializers return validated data: `return serializer.data`

## Module Design

**Exports:**
- Explicit imports in consuming modules
- No wildcard imports (`from module import *`)
- Example pattern:
  ```python
  from .models import CustomUser, Profile
  from .forms import CustomUserCreationForm, ProfileUpdateForm
  from .views import register, user_login
  ```

**Barrel Files:**
- Not heavily used in this codebase
- Each module imports what it needs explicitly
- `__init__.py` files typically empty or minimal

**File Organization:**
- Models in `models.py` or split into `models_*.py` for large domains
- Views in `views.py` or split into `views_*.py` (e.g., `views_2fa.py`, `views_security.py`)
- Forms in `forms.py`
- Tests co-located with source: `test_models.py`, `test_views.py`, `test_forms.py`
- Utilities in `utils_*.py` or `tasks_*.py` for async tasks

---

*Convention analysis: 2026-03-18*
