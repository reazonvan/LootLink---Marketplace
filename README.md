# LootLink Marketplace

> P2P gaming marketplace for trading in-game items between players

[![Live Demo](https://img.shields.io/badge/demo-lootlink.ru-blue)](https://lootlink.ru)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

LootLink is a full-stack web application that enables direct peer-to-peer trading of gaming items. Built with Django and PostgreSQL, it provides a secure platform for gamers to buy, sell, and trade virtual items without intermediaries.

**Live Demo:** [lootlink.ru](https://lootlink.ru)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Performance](#performance)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Features

### Core Functionality
- **Marketplace**: Create, browse, and search listings with advanced filtering
- **Real-time Chat**: Direct messaging between buyers and sellers
- **Transaction System**: Formalized purchase requests with status tracking
- **User Profiles**: Reputation system based on completed transactions
- **Review System**: Ratings and feedback for users
- **Email Verification**: Account verification via email
- **Admin Panel**: Custom admin interface for moderation

### Technical Features
- RESTful API with Django REST Framework
- Real-time notifications
- Image upload and optimization
- Full-text search with PostgreSQL
- Redis caching for performance
- Responsive design with Bootstrap 5
- CSRF protection and security headers
- Rate limiting and brute-force protection
- Comprehensive test coverage

---

## Tech Stack

**Backend:**
- Python 3.10+
- Django 4.2
- Django REST Framework 3.16
- PostgreSQL 15
- Redis 7.0
- Celery 5.5 (async tasks)
- Django Channels 4.0 (WebSockets)

**Frontend:**
- Bootstrap 5.2
- JavaScript ES6+
- jQuery 3.6
- HTML5/CSS3

**Infrastructure:**
- Docker & Docker Compose
- Nginx 1.24
- Gunicorn
- Systemd (production)

**Development:**
- Git
- pytest
- flake8, black, isort
- pre-commit hooks

---

## Prerequisites

Before installation, ensure you have:

- Python 3.10 or higher
- PostgreSQL 15+
- Redis 7.0+ (optional, for caching)
- Git
- Virtual environment tool (venv or virtualenv)

For Docker deployment:
- Docker 20.10+
- Docker Compose 2.0+

---

## Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace
```

2. **Create and activate virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements/development.txt
```

4. **Set up environment variables**
```bash
cp env.example.txt .env
# Edit .env with your configuration
```

5. **Create database**
```bash
# PostgreSQL
createdb lootlink_db
```

6. **Run migrations**
```bash
python manage.py migrate
```

7. **Create superuser**
```bash
python manage.py createsuperuser
```

8. **Run development server**
```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

### Docker Deployment

```bash
# Build and start containers
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=lootlink_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis (optional)
USE_REDIS=True
REDIS_URL=redis://localhost:6379/1

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AWS S3 (optional)
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=

# Security (production only)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

See `env.example.txt` for complete configuration options.

---

## Usage

### Admin Panel
Access the Django admin at `http://localhost:8000/admin/` with your superuser credentials.

### Creating Listings
1. Register an account or log in
2. Navigate to "Create Listing"
3. Fill in item details and upload an image
4. Submit for publication

### Making Purchases
1. Browse listings or use search/filters
2. Click on an item to view details
3. Send a purchase request to the seller
4. Communicate via built-in chat
5. Complete the transaction

### API Access
API endpoints are available at `/api/`. See [API Documentation](#api-documentation) for details.

---

## Project Structure

```
LootLink---Marketplace/
├── accounts/           # User authentication and profiles
├── listings/           # Marketplace listings and categories
├── chat/              # Real-time messaging system
├── transactions/      # Purchase requests and reviews
├── payments/          # Payment processing (future)
├── api/               # REST API endpoints
├── admin_panel/       # Custom admin interface
├── core/              # Shared utilities and middleware
├── config/            # Django settings and configuration
├── static/            # Static files (CSS, JS, images)
├── templates/         # HTML templates
├── nginx/             # Nginx configuration files
├── scripts/           # Deployment and utility scripts
├── tests/             # Test suite
├── docs/              # Documentation
├── requirements/      # Python dependencies
│   ├── base.txt       # Core dependencies
│   ├── development.txt # Development tools
│   └── production.txt  # Production requirements
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── README.md
```

### Django Apps

- **accounts**: User registration, authentication, profiles, verification
- **listings**: Item listings, categories, games, favorites
- **chat**: Conversations and messages between users
- **transactions**: Purchase requests, transaction history, reviews
- **payments**: Payment integration (planned)
- **api**: RESTful API with DRF
- **admin_panel**: Enhanced admin interface
- **core**: Middleware, utilities, notifications

---

## API Documentation

The REST API provides programmatic access to marketplace functionality.

**Base URL:** `https://lootlink.ru/api/`

### Authentication
API uses session-based authentication. Include CSRF token in POST requests.

### Endpoints

```
GET    /api/listings/              # List all listings
GET    /api/listings/{id}/         # Get listing details
POST   /api/listings/              # Create listing (auth required)
PUT    /api/listings/{id}/         # Update listing (owner only)
DELETE /api/listings/{id}/         # Delete listing (owner only)

GET    /api/games/                 # List games
GET    /api/categories/            # List categories

GET    /api/conversations/         # List user conversations
POST   /api/conversations/         # Create conversation
GET    /api/messages/              # List messages

GET    /api/transactions/          # List user transactions
POST   /api/transactions/          # Create purchase request
```

For complete API documentation, see `docs/API_DOCUMENTATION.md`.

---

## Testing

### Run Tests

```bash
# All tests
python manage.py test

# Specific app
python manage.py test accounts

# With coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Test Structure

```
tests/
├── test_models.py
├── test_views.py
├── test_api.py
├── test_security.py
└── test_integration.py
```

### Linting

```bash
# Flake8
flake8 . --exclude=migrations,venv

# Black formatting
black . --exclude="migrations|venv"

# Import sorting
isort . --skip migrations --skip venv
```

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up SSL/TLS certificates
- [ ] Configure production database
- [ ] Set up Redis for caching
- [ ] Configure email backend
- [ ] Set up static file serving
- [ ] Configure Nginx/Apache
- [ ] Set up monitoring (Sentry)
- [ ] Configure automated backups
- [ ] Set up firewall rules

### Deployment Guide

See `docs/DEPLOYMENT.md` for detailed production deployment instructions including:
- Server setup
- Nginx configuration
- SSL with Let's Encrypt
- Systemd service configuration
- Database optimization
- Security hardening

### Quick Deploy

```bash
# Using provided script
bash scripts/deploy_with_smoke.sh
```

---

## Performance

### Optimization Techniques

- **Database**: Query optimization with `select_related` and `prefetch_related`
- **Caching**: Redis caching for frequently accessed data
- **Static Files**: CDN delivery and minification
- **Images**: Automatic compression and optimization
- **Indexes**: Database indexes on frequently queried fields
- **Connection Pooling**: Persistent database connections

### Benchmarks

- Average page load: < 200ms
- API response time: < 100ms
- Concurrent users: 1000+
- Database queries per page: < 10

---

## Security

### Implemented Security Measures

- **CSRF Protection**: Django CSRF tokens on all forms
- **SQL Injection**: ORM-based queries prevent SQL injection
- **XSS Protection**: Template auto-escaping and CSP headers
- **Password Security**: PBKDF2 hashing with salt
- **Session Security**: Secure, HttpOnly cookies
- **Rate Limiting**: Brute-force protection on login/registration
- **Email Verification**: Required for account activation
- **HTTPS**: SSL/TLS encryption in production
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, etc.

### Security Audit

Run security checks:
```bash
python manage.py check --deploy
bandit -r . -x ./venv
safety check
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation as needed
- Run linters before committing
- Keep commits atomic and well-described

See `CONTRIBUTING.md` for detailed guidelines.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

**Developer:** Ivan Petrov
**Email:** ivanpetrov20066.ip@gmail.com
**Demo:** [lootlink.ru](https://lootlink.ru)
**Issues:** [GitHub Issues](https://github.com/reazonvan/LootLink---Marketplace/issues)

---

## Acknowledgments

- Django community for excellent documentation
- Bootstrap team for the UI framework
- All contributors and testers

---

**[⬆ Back to Top](#lootlink-marketplace)**
