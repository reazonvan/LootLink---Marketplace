# Architecture

**Analysis Date:** 2026-03-18

## Pattern Overview

**Overall:** Multi-layered Django monolith with REST API and real-time WebSocket support

**Key Characteristics:**
- Django 4.2 with Django REST Framework for API endpoints
- Django Channels for WebSocket real-time communication (chat)
- Celery for asynchronous task processing
- PostgreSQL primary database with SQLite fallback
- Redis for caching, session storage, and Channels layer
- Modular app structure with feature-based separation

## Layers

**Presentation Layer:**
- Purpose: HTTP request handling and response rendering
- Location: `templates/`, `static/`
- Contains: HTML templates organized by app, CSS/JS assets
- Depends on: Views, context processors
- Used by: Django template engine, browsers

**View/Controller Layer:**
- Purpose: Handle HTTP requests, orchestrate business logic
- Location: `accounts/views.py`, `listings/views.py`, `transactions/views.py`, `chat/views.py`, `payments/views.py`, `core/views.py`, `api/views.py`
- Contains: Function-based views (FBV) and class-based views (CBV), view logic split by feature (views_*.py)
- Depends on: Models, forms, serializers, utilities
- Used by: URL routing, middleware

**API Layer:**
- Purpose: RESTful API endpoints for client applications
- Location: `api/views.py`, `api/serializers.py`, `api/permissions.py`, `api/throttling.py`
- Contains: DRF ViewSets, custom serializers, permission classes, rate throttling
- Depends on: Models, REST Framework
- Used by: External clients, frontend applications

**Model/Data Layer:**
- Purpose: Data persistence and business logic
- Location: `accounts/models.py`, `listings/models.py`, `transactions/models.py`, `chat/models.py`, `payments/models.py`, `core/models.py`
- Contains: Django ORM models, model methods, signals
- Depends on: Django ORM, validators
- Used by: Views, serializers, managers

**Real-time Layer:**
- Purpose: WebSocket connections for live chat
- Location: `chat/routing.py`, `chat/consumers.py`, `config/asgi.py`
- Contains: Channels consumers, routing configuration
- Depends on: Channels, Redis, authentication
- Used by: Chat views, frontend WebSocket clients

**Async Task Layer:**
- Purpose: Background job processing
- Location: `core/tasks.py`, `payments/tasks.py`, `config/celery.py`
- Contains: Celery tasks, beat schedule configuration
- Depends on: Celery, Redis, models
- Used by: Views, signals, scheduled jobs

**Middleware/Cross-cutting Layer:**
- Purpose: Request/response processing, security, monitoring
- Location: `core/middleware.py`, `core/middleware_audit.py`, `core/middleware_activity.py`, `admin_panel/middleware.py`
- Contains: Rate limiting, security headers, audit logging, activity tracking
- Depends on: Django middleware API, cache, logging
- Used by: Django request/response cycle

**Configuration Layer:**
- Purpose: Application settings and initialization
- Location: `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`
- Contains: Django settings, URL routing, WSGI/ASGI application
- Depends on: Environment variables, installed apps
- Used by: Django runtime

## Data Flow

**Marketplace Listing Flow:**

1. User navigates to listing page → URL routed to `listings/views.py:listing_detail()`
2. View queries `Listing` model with related `Game`, `Category`, `Profile`
3. View renders template with listing data
4. Template displays images from `ListingImage` model
5. User can favorite → AJAX call to `listings/views.py:toggle_favorite()`
6. Favorite state persisted via `Favorite` model

**Purchase/Transaction Flow:**

1. User clicks "Buy" → creates `PurchaseRequest` via `transactions/views.py`
2. Seller receives notification via `core/models.py:Notification`
3. Seller accepts/rejects → updates `PurchaseRequest.status`
4. On completion → creates `Review`, updates seller rating
5. Async task via Celery updates user badges/reputation

**Chat/Real-time Flow:**

1. User opens chat → WebSocket connection via `chat/consumers.py`
2. Message sent → stored in `Message` model, broadcast via Channels
3. Recipient receives real-time update via WebSocket
4. Message history loaded from `Conversation` model

**Payment Flow:**

1. User initiates withdrawal → creates `Withdrawal` request
2. Async task processes payment via external provider
3. On success → updates `Wallet.balance`, creates `Transaction` record
4. Notification sent to user

**State Management:**

- **Session State**: Django sessions via Redis
- **Cache State**: Platform stats, user data cached in Redis (300s TTL)
- **Database State**: All persistent data in PostgreSQL
- **Real-time State**: Active WebSocket connections managed by Channels/Redis

## Key Abstractions

**User Model:**
- Purpose: Central identity and authentication
- Examples: `accounts/models.py:CustomUser`, `accounts/models.py:Profile`
- Pattern: Extends Django's AbstractUser, OneToOne relationship with Profile

**Listing Model:**
- Purpose: Marketplace item representation
- Examples: `listings/models.py:Listing`, `listings/models.py:Game`, `listings/models.py:Category`
- Pattern: Hierarchical (Game → Category → Listing), supports images, favorites, reports

**Transaction Model:**
- Purpose: Purchase and deal tracking
- Examples: `transactions/models.py:PurchaseRequest`, `transactions/models_reviews.py:Review`
- Pattern: State machine (pending → accepted/rejected → completed), linked to buyer/seller

**Conversation Model:**
- Purpose: Real-time messaging between users
- Examples: `chat/models.py:Conversation`, `chat/models.py:Message`
- Pattern: Bidirectional participant relationship, linked to listing context

**Wallet Model:**
- Purpose: User balance and payment management
- Examples: `payments/models.py:Wallet`, `payments/models.py:Transaction`
- Pattern: OneToOne with user, tracks available and frozen balance

## Entry Points

**Web Application:**
- Location: `config/wsgi.py`
- Triggers: HTTP requests from browsers
- Responsibilities: WSGI application initialization, request routing

**Real-time Chat:**
- Location: `config/asgi.py`
- Triggers: WebSocket upgrade requests
- Responsibilities: ASGI application initialization, protocol routing (HTTP/WebSocket)

**Management Commands:**
- Location: `manage.py`
- Triggers: CLI invocation
- Responsibilities: Database migrations, fixture loading, custom commands

**Async Tasks:**
- Location: `config/celery.py`
- Triggers: Scheduled beats or task queue
- Responsibilities: Background job execution, result storage

**Admin Interface:**
- Location: `admin_panel/views.py`
- Triggers: `/custom-admin/` URL access
- Responsibilities: Admin dashboard, moderation, statistics

## Error Handling

**Strategy:** Layered error handling with logging and user feedback

**Patterns:**

- **View Level**: Try-catch with user-friendly messages via Django messages framework
- **Model Level**: Validation errors via Django validators, custom ValidationError
- **API Level**: DRF exception handlers return JSON with status codes
- **Middleware Level**: Security middleware returns 403 on rate limit, audit middleware logs suspicious activity
- **Async Level**: Celery task retry logic with exponential backoff
- **Sentry Integration**: Production error tracking via Sentry (configured in `config/settings.py`)

## Cross-Cutting Concerns

**Logging:**
- Security logger: `django.security` for authentication, rate limiting, audit events
- Application logger: Standard Django logging for business logic
- Location: Configured in `config/settings.py`

**Validation:**
- Model-level: Django validators in field definitions
- Form-level: Custom form validation in `accounts/forms.py`, `listings/forms.py`, etc.
- API-level: DRF serializer validation
- Location: `core/validators.py` for custom validators

**Authentication:**
- Session-based: Django sessions for web views
- Token-based: DRF TokenAuthentication for API
- 2FA: TOTP via `django_otp` in `accounts/views_2fa.py`
- Location: `accounts/backends.py` for custom auth backends

**Authorization:**
- View-level: `@login_required` decorator, custom permission checks
- API-level: DRF permission classes in `api/permissions.py`
- Model-level: Queryset filtering by user ownership
- Location: Distributed across views and API

**Caching:**
- Query caching: `core/utils.py:get_cached_or_set()` for expensive queries
- Page caching: Redis-backed cache for platform stats
- Location: `config/settings.py` CACHES configuration

**Rate Limiting:**
- Middleware-based: `core/middleware.py:SimpleRateLimitMiddleware` for critical endpoints
- API-based: DRF throttling classes in `api/throttling.py`
- Location: Configured in middleware and REST_FRAMEWORK settings

---

*Architecture analysis: 2026-03-18*
