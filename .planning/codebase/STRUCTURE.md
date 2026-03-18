# Codebase Structure

**Analysis Date:** 2026-03-18

## Directory Layout

```
LootLink---Marketplace/
├── config/                 # Django project configuration
├── accounts/               # User authentication, profiles, verification
├── listings/               # Marketplace listings, games, categories
├── transactions/           # Purchase requests, reviews, disputes
├── chat/                   # Real-time messaging via WebSocket
├── payments/               # Wallet, transactions, payment processing
├── core/                   # Shared utilities, notifications, audit
├── api/                    # REST API endpoints
├── admin_panel/            # Custom admin dashboard
├── templates/              # HTML templates
├── static/                 # CSS, JavaScript, images
├── staticfiles/            # Collected static files (generated)
├── media/                  # User-uploaded files
├── logs/                   # Application logs
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── tests/                  # Integration tests
├── requirements/           # Python dependencies
├── deployment/             # Deployment configuration
├── nginx/                  # Nginx configuration
├── manage.py               # Django management script
└── .planning/              # GSD planning documents
```

## Directory Purposes

**config/**
- Purpose: Django project settings and initialization
- Contains: Settings, URL routing, WSGI/ASGI, Celery configuration
- Key files: `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `celery.py`

**accounts/**
- Purpose: User authentication, profiles, security, verification
- Contains: User models, authentication views, 2FA, email verification, export functionality
- Key files: `models.py`, `views.py`, `forms.py`, `backends.py`, `models_security.py`

**listings/**
- Purpose: Marketplace listings, games, categories, search
- Contains: Listing models, game/category management, search views, trading (offers/reservations)
- Key files: `models.py`, `views.py`, `forms.py`, `search_views.py`, `views_trading.py`

**transactions/**
- Purpose: Purchase requests, reviews, disputes
- Contains: Transaction models, purchase workflow, review system, dispute resolution
- Key files: `models.py`, `views.py`, `models_reviews.py`, `models_disputes.py`

**chat/**
- Purpose: Real-time messaging between users
- Contains: Conversation models, WebSocket consumers, message routing
- Key files: `models.py`, `consumers.py`, `routing.py`, `views.py`

**payments/**
- Purpose: Wallet management, payment processing, transactions
- Contains: Wallet models, payment views, transaction history, dispute handling
- Key files: `models.py`, `views.py`, `tasks.py`, `models_disputes.py`

**core/**
- Purpose: Shared utilities, notifications, audit logging, middleware
- Contains: Notification models, audit logs, security middleware, utility functions
- Key files: `models.py`, `utils.py`, `middleware.py`, `tasks.py`, `models_audit.py`

**api/**
- Purpose: REST API endpoints for external clients
- Contains: DRF viewsets, serializers, permissions, throttling
- Key files: `views.py`, `serializers.py`, `permissions.py`, `throttling.py`

**admin_panel/**
- Purpose: Custom admin dashboard for moderation and statistics
- Contains: Admin views, templates, middleware for context
- Key files: `views.py`, `urls.py`, `middleware.py`

**templates/**
- Purpose: HTML templates for rendering views
- Contains: Base templates, app-specific templates, email templates
- Structure: `templates/{app_name}/` for app-specific, `templates/components/` for reusable

**static/**
- Purpose: Static assets (CSS, JavaScript, images)
- Contains: Bootstrap CSS, custom styles, JavaScript utilities
- Structure: `static/css/`, `static/js/`, `static/images/`

**media/**
- Purpose: User-uploaded files (avatars, listing images, verification documents)
- Contains: Organized by upload type
- Structure: `media/avatars/`, `media/covers/`, `media/verification_documents/`

**tests/**
- Purpose: Integration and unit tests
- Contains: Test files for models, views, API endpoints
- Key files: `test_*.py` files throughout apps

**docs/**
- Purpose: Project documentation
- Contains: Setup guides, deployment docs, design decisions
- Structure: `docs/setup/`, `docs/deployment/`, `docs/design/`

## Key File Locations

**Entry Points:**
- `manage.py`: Django CLI entry point
- `config/wsgi.py`: WSGI application for production servers
- `config/asgi.py`: ASGI application for WebSocket support

**Configuration:**
- `config/settings.py`: All Django settings (database, apps, middleware, caching)
- `config/urls.py`: Root URL routing to app-specific URLs
- `config/celery.py`: Celery configuration and task discovery
- `.env`: Environment variables (not committed, contains secrets)

**Core Logic:**
- `accounts/models.py`: User and profile models
- `listings/models.py`: Listing, game, category models
- `transactions/models.py`: Purchase request and transaction models
- `chat/models.py`: Conversation and message models
- `payments/models.py`: Wallet and payment models

**Views:**
- `listings/views.py`: Listing display, creation, editing
- `accounts/views.py`: User registration, login, profile management
- `transactions/views.py`: Purchase request handling
- `chat/views.py`: Chat interface
- `payments/views.py`: Wallet and payment views

**API:**
- `api/views.py`: REST API viewsets
- `api/serializers.py`: DRF serializers for API responses
- `api/permissions.py`: Custom permission classes

**Utilities:**
- `core/utils.py`: Pagination, caching, platform statistics
- `core/middleware.py`: Rate limiting, security headers
- `core/tasks.py`: Celery async tasks

**Testing:**
- `accounts/test_*.py`: User model and view tests
- `listings/test_*.py`: Listing model and view tests
- `api/tests_*.py`: API endpoint tests

## Naming Conventions

**Files:**
- `models.py`: Primary model definitions
- `models_{feature}.py`: Feature-specific models (e.g., `models_security.py`, `models_audit.py`)
- `views.py`: Primary view definitions
- `views_{feature}.py`: Feature-specific views (e.g., `views_2fa.py`, `views_trading.py`)
- `forms.py`: Django form classes
- `urls.py`: URL routing for app
- `tasks.py`: Celery async tasks
- `test_*.py` or `tests.py`: Test files
- `serializers.py`: DRF serializers
- `permissions.py`: Custom permission classes
- `middleware.py`: Custom middleware

**Directories:**
- `migrations/`: Django database migrations (auto-generated)
- `templates/{app_name}/`: App-specific templates
- `management/commands/`: Custom Django management commands
- `static/`: Static assets

**Models:**
- PascalCase class names: `CustomUser`, `Listing`, `PurchaseRequest`
- Descriptive names reflecting domain: `Conversation`, `Wallet`, `Review`

**Functions/Methods:**
- snake_case: `get_available_balance()`, `toggle_favorite()`, `mark_as_read()`
- Verb-first for actions: `create_`, `update_`, `delete_`, `send_`

**Variables:**
- snake_case: `user_profile`, `listing_count`, `is_verified`
- Descriptive names: `purchase_request`, `frozen_balance`

## Where to Add New Code

**New Feature (e.g., Ratings System):**
- Primary code: Create `listings/models_ratings.py` for models, `listings/views_ratings.py` for views
- Forms: Add to `listings/forms.py` or create `listings/forms_ratings.py`
- Tests: Create `listings/test_ratings.py`
- Templates: Add to `templates/listings/ratings/`
- API: Add serializers to `api/serializers.py`, viewsets to `api/views.py`

**New Component/Module:**
- Implementation: Create new app via `python manage.py startapp {app_name}`
- Models: `{app_name}/models.py` (split into `models_*.py` if complex)
- Views: `{app_name}/views.py` (split into `views_*.py` by feature)
- URLs: `{app_name}/urls.py`, register in `config/urls.py`
- Templates: `templates/{app_name}/`
- Tests: `{app_name}/test_*.py`

**Utilities/Helpers:**
- Shared helpers: `core/utils.py` for general utilities
- App-specific helpers: `{app_name}/utils.py` if needed
- Validators: `core/validators.py` for custom field validators
- Middleware: `core/middleware.py` or `core/middleware_{feature}.py`

**Async Tasks:**
- App-specific tasks: `{app_name}/tasks.py`
- Shared tasks: `core/tasks.py`
- Register in `config/celery.py` for discovery

**API Endpoints:**
- Serializers: Add to `api/serializers.py`
- ViewSets: Add to `api/views.py`
- Permissions: Add to `api/permissions.py` if custom
- Register in `api/urls.py`

## Special Directories

**migrations/**
- Purpose: Database schema version control
- Generated: Yes (via `python manage.py makemigrations`)
- Committed: Yes (must be committed to git)
- Note: Never edit manually; create new migrations for schema changes

**staticfiles/**
- Purpose: Collected static files for production
- Generated: Yes (via `python manage.py collectstatic`)
- Committed: No (generated during deployment)
- Note: Recreated on each deployment

**media/**
- Purpose: User-uploaded files
- Generated: Yes (via user uploads)
- Committed: No (stored in S3 or local filesystem)
- Note: In production, stored in S3 via `storages` package

**logs/**
- Purpose: Application runtime logs
- Generated: Yes (during execution)
- Committed: No (ignored in .gitignore)
- Note: Rotated daily, archived for debugging

**.planning/**
- Purpose: GSD project planning and codebase analysis
- Generated: Yes (via GSD commands)
- Committed: Yes (part of project context)
- Note: Contains STATE.md, ROADMAP.md, and codebase analysis docs

**requirements/**
- Purpose: Python dependency specifications
- Generated: No (manually maintained)
- Committed: Yes
- Note: Split by environment (base.txt, dev.txt, prod.txt)

---

*Structure analysis: 2026-03-18*
