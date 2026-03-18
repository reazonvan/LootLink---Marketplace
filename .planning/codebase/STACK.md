# Technology Stack

**Analysis Date:** 2026-03-18

## Languages

**Primary:**
- Python 3.11 - Backend application, Django framework, async tasks with Celery

**Secondary:**
- HTML/CSS/JavaScript - Frontend templates with Bootstrap 5

## Runtime

**Environment:**
- Python 3.11-slim (Docker image)
- ASGI server: Daphne (supports HTTP + WebSocket)
- WSGI fallback: Gunicorn (production)

**Package Manager:**
- pip
- Lockfile: requirements/ directory with base.txt, development.txt, production.txt, telegram.txt, push.txt

## Frameworks

**Core:**
- Django 5.2 - Web framework
- Django REST Framework - API endpoints and serialization
- Django Channels - WebSocket support for real-time chat
- Daphne - ASGI application server

**Forms & UI:**
- django-crispy-forms 2.4 - Form rendering
- crispy-bootstrap5 2024.2 - Bootstrap 5 integration

**Database & ORM:**
- Django ORM (built-in)
- psycopg2-binary 2.9.9 - PostgreSQL adapter

**Testing:**
- pytest 7.4.0 - Test runner
- pytest-django 4.11.0 - Django integration
- pytest-cov 4.1.0 - Coverage reporting
- playwright 1.58.0 - E2E testing

**Build/Dev:**
- black 23.12.0 - Code formatting
- isort 5.13.0 - Import sorting
- flake8 6.1.0 - Linting
- django-debug-toolbar 4.2.0 - Development debugging
- ipython 8.18.0 - Interactive shell
- ipdb 0.13.13 - Debugger

## Key Dependencies

**Critical:**
- Django 5.2 - Core framework
- psycopg2-binary 2.9.9 - PostgreSQL connectivity
- Pillow 11.3.0 - Image processing for listings/avatars
- python-decouple 3.8 - Environment configuration management

**Infrastructure:**
- celery 5.5.0 - Distributed task queue for async operations
- redis 7.0.0 - In-memory data store for caching and Celery broker
- django-redis 6.0.0 - Redis cache backend
- hiredis 3.3.0 - Redis protocol parser (performance)
- channels-redis - Redis backend for WebSocket layer
- django-celery-beat - Periodic task scheduling

**Security & Monitoring:**
- sentry-sdk 2.42.0 - Error tracking and monitoring (production only)
- django-otp 1.x - Two-factor authentication support
- django-otp.plugins.otp_totp - TOTP implementation

**Storage:**
- django-storages 1.14.2 - Abstract storage backends
- boto3 1.40.0 - AWS S3 client (optional)

**Utilities:**
- python-telegram-bot 20.7 - Telegram bot integration
- pywebpush 1.14.0 - Web Push Notifications
- django-environ 0.12.0 - Environment variable management
- django-filter - Query filtering for API

## Configuration

**Environment:**
- Configuration via `.env` file using python-decouple
- Environment-specific requirements: base.txt (all), development.txt, production.txt
- Settings module: `config/settings.py` with conditional logic for DEBUG/production

**Build:**
- Dockerfile: Python 3.11-slim with system dependencies (postgresql-client, libpq-dev, gcc)
- docker-compose.yml: Multi-service orchestration
- .pre-commit-config.yaml: Pre-commit hooks for code quality
- pyproject.toml: Tool configurations (black, isort, pytest, mypy, bandit, pylint)

## Platform Requirements

**Development:**
- Python 3.11+
- PostgreSQL 15 (or SQLite for local dev)
- Redis 7 (optional for local dev, required for production)
- Docker & Docker Compose (for containerized development)

**Production:**
- Docker container deployment
- PostgreSQL 15 database
- Redis 7 for caching and Celery
- Reverse proxy: Caddy or Nginx
- HTTPS/SSL certificates
- Daphne ASGI server on port 8000
- Celery worker and beat scheduler
- Flower monitoring (optional)

---

*Stack analysis: 2026-03-18*
