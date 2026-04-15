# LootLink Development Quick Reference

## Quick Start

```bash
# Setup (first time)
./setup.sh          # Linux/Mac
setup.bat           # Windows

# Or manually:
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## VS Code Shortcuts

| Action | Shortcut |
|--------|----------|
| Run Django Server | `Ctrl+Shift+B` |
| Run Task | `Ctrl+Shift+P` → Tasks: Run Task |
| Start Debugging | `F5` |
| Toggle Breakpoint | `F9` |
| Quick File Search | `Ctrl+P` |
| Search in Project | `Ctrl+Shift+F` |
| Go to Definition | `F12` |
| Format Document | `Shift+Alt+F` |
| Comment/Uncomment | `Ctrl+/` |

## Common Tasks

### Django Commands
```bash
# Development
python manage.py runserver
python manage.py shell
python manage.py check

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Static files
python manage.py collectstatic --noinput

# Testing
python manage.py test
pytest -v
pytest --cov=. --cov-report=html
```

### Celery Commands
```bash
# Worker
celery -A lootlink worker -l info

# Beat scheduler
celery -A lootlink beat -l info

# Both (development only)
celery -A lootlink worker -B -l info
```

### Docker Commands
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Rebuild
docker-compose up -d --build
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Commit
git add .
git commit -m "Add new feature"

# Push
git push origin feature/new-feature

# Update from main
git checkout main
git pull
git checkout feature/new-feature
git rebase main
```

## 🧪 Testing

```bash
# All tests
pytest -v

# Specific test
pytest path/to/test_file.py::TestClass::test_method

# With coverage
pytest --cov=. --cov-report=html

# Fast (no coverage)
pytest -v --no-cov

# Parallel
pytest -n auto
```

## Code Quality

```bash
# Format code
black .
isort .

# Lint
flake8 .
pylint **/*.py

# Security
bandit -r . -c pyproject.toml

# All checks
make lint
```

## Debugging

### In VS Code:
1. Set breakpoint: `F9`
2. Start debug: `F5`
3. Step over: `F10`
4. Step into: `F11`
5. Continue: `F5`

### In code:
```python
# Add breakpoint
import ipdb; ipdb.set_trace()

# Or
breakpoint()
```

### Django Debug Toolbar:
```python
# In settings.py (already configured)
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

## 📦 Dependencies

```bash
# Install
pip install package-name

# Add to requirements
pip freeze > requirements.txt

# Update all
pip install --upgrade -r requirements.txt
```

## Database

```bash
# PostgreSQL shell
psql -U postgres -d lootlink

# Django shell
python manage.py shell

# Create backup
pg_dump lootlink > backup.sql

# Restore backup
psql lootlink < backup.sql
```

## Useful Django Shell Commands

```python
# Import models
from accounts.models import User, Profile
from listings.models import Game, Listing

# Query examples
User.objects.all()
User.objects.filter(is_active=True)
User.objects.get(username='admin')

# Create object
user = User.objects.create_user('username', 'email@example.com', 'password')

# Update
user.email = 'newemail@example.com'
user.save()

# Delete
user.delete()

# Raw SQL
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM accounts_user LIMIT 10")
rows = cursor.fetchall()
```

## 🎨 Frontend

```bash
# Watch CSS (if using preprocessor)
npm run watch

# Build for production
npm run build

# Lint JavaScript
npm run lint
```

## Performance

```bash
# Profile view
python manage.py runprofileserver

# Check queries
python manage.py debugsqlshell

# Cache stats
python manage.py shell
>>> from django.core.cache import cache
>>> cache.get_stats()
```

## Security

```bash
# Check for vulnerabilities
safety check

# Update dependencies
pip install --upgrade -r requirements.txt

# Security audit
bandit -r .
```

## Documentation

```bash
# Generate API docs
python manage.py spectacular --file schema.yml

# Build Sphinx docs
cd docs
make html
```

## Troubleshooting

### Port already in use:
```bash
# Find process
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

### Database locked:
```bash
# Reset database
python manage.py flush
python manage.py migrate
```

### Static files not loading:
```bash
python manage.py collectstatic --clear --noinput
```

### Cache issues:
```python
from django.core.cache import cache
cache.clear()
```

## 📚 Resources

- [Django Docs](https://docs.djangoproject.com/)
- [DRF Docs](https://www.django-rest-framework.org/)
- [Celery Docs](https://docs.celeryproject.org/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [VS Code Guide](docs/VSCODE_QUICKSTART.md)

## 🆘 Getting Help

1. Check logs: `tail -f logs/lootlink.log`
2. Check Django Debug Toolbar
3. Check browser console (F12)
4. Search in documentation
5. Search StackOverflow

---

**Keep this file open in a separate tab for quick reference!**
