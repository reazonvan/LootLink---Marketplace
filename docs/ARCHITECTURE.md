# Архитектура LootLink

Полное описание архитектуры проекта LootLink.

---

## Общая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  HTML Templates + Bootstrap 5 + Vanilla JavaScript           │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/HTTPS
┌────────────────────▼────────────────────────────────────────┐
│                         Nginx                                │
│  - SSL Termination                                           │
│  - Static/Media serving                                      │
│  - Reverse Proxy                                             │
│  - Gzip Compression                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                      Gunicorn                                │
│  - WSGI Server                                               │
│  - Process Management                                        │
│  - Load Balancing (workers)                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Django 4.2                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Applications:                                        │  │
│  │  - accounts   (Пользователи, профили)              │  │
│  │  - listings   (Объявления, игры)                   │  │
│  │  - transactions (Покупки, отзывы)                  │  │
│  │  - chat       (Сообщения, беседы)                  │  │
│  │  - core       (Уведомления, утилиты)               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Middleware:                                          │  │
│  │  - SecurityHeadersMiddleware (CSP, HSTS)            │  │
│  │  - SimpleRateLimitMiddleware (DDoS защита)          │  │
│  │  - CSRF Protection                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────┬────────────┬────────────────────────────────┘
               │            │
        ┌──────▼──────┐  ┌─▼────────┐
        │ PostgreSQL  │  │  Redis   │
        │    15+      │  │   7      │
        │             │  │          │
        │ - Full-Text │  │ - Cache  │
        │ - Indexes   │  │ - Sessions│
        │ - Relations │  │ - Rate   │
        └─────────────┘  │   Limit  │
                         └──────────┘
```

---

## 📦 Структура приложений Django

### 1. **accounts** - Управление пользователями

**Модели:**
- `CustomUser` - Кастомная модель пользователя
  - `username` (unique)
  - `email` (unique)
  - Переопределен delete() - удаление запрещено

- `Profile` - Профиль пользователя
  - `avatar` - Аватар (с валидацией)
  - `bio`, `phone` - Контактная информация
  - `rating` (0-5) - Рейтинг продавца
  - `total_sales`, `total_purchases` - Статистика
  - `is_verified` - Верификация
  - Автоматический расчет рейтинга из отзывов
  - **Общение только через встроенный чат** (соцсети удалены)

- `PasswordResetCode` - Коды для сброса пароля
  - 6-значный код
  - TTL 15 минут
  - Одноразовый

**Views:**
- `register()` - Регистрация
- `user_login()` - Вход
- `profile()` - Просмотр профиля
- `profile_edit()` - Редактирование
- `my_listings()`, `my_purchases()`, `my_sales()` - Личные разделы
- `password_reset_request()` - Сброс пароля

**Безопасность:**
- CSRF защита
- Rate limiting (5 попыток входа за 5 минут)
- Валидация email
- Хеширование паролей (PBKDF2)

---

### 2. **listings** - Объявления и игры

**Модели:**
- `Game` - Игра
  - `name`, `slug`, `description`
  - `icon` - Иконка игры
  - `is_active` - Активность

- `Listing` - Объявление
  - `title`, `description`, `price`
  - `image` - Фото (валидация 5MB, JPEG/PNG/GIF/WebP)
  - `status` - active/reserved/sold/cancelled
  - `search_vector` - PostgreSQL Full-Text Search
  - GIN индекс для быстрого поиска

- `Favorite` - Избранное
  - unique_together для user + listing

- `Report` - Жалобы
  - На объявления или пользователей
  - Статусы: pending/reviewed/resolved/rejected

**Views:**
- `catalog()` - Каталог с фильтрами и поиском
- `listing_detail()` - Детали объявления
- `listing_create()`, `listing_edit()`, `listing_delete()` - CRUD
- `toggle_favorite()` - AJAX добавление в избранное
- `report_listing()`, `report_user()` - Жалобы

**Производительность:**
- `select_related()` для ForeignKey
- `prefetch_related()` для ManyToMany
- PostgreSQL Full-Text Search с русской морфологией
- Кеширование статистики (5 минут)
- Пагинация (12 объявлений на страницу)

---

### 3. **transactions** - Сделки и отзывы

**Модели:**
- `PurchaseRequest` - Запрос на покупку
  - Статусы: pending → accepted → completed
  - `unique_together` для buyer + listing (один запрос от покупателя)
  - Атомарное обновление статистики через F()

- `Review` - Отзыв
  - Рейтинг 1-5 звезд
  - `unique_together` для purchase_request + reviewer
  - Автообновление рейтинга пользователя

**Business Logic:**

```
1. Покупатель создает PurchaseRequest (status=pending)
2. Продавец принимает → status=accepted, listing.status=reserved
3. Продавец завершает → status=completed, listing.status=sold
4. Обновляется статистика: total_sales++, total_purchases++
5. Покупатель и продавец могут оставить Review
6. Рейтинг пересчитывается автоматически
```

**Views:**
- `purchase_request_create()` - Создание запроса
- `purchase_request_accept()` - Принятие (только продавец)
- `purchase_request_reject()` - Отклонение (только продавец)
- `purchase_request_complete()` - Завершение (только продавец)
- `review_create()` - Создание отзыва

---

### 4. **chat** - Система сообщений

**Модели:**
- `Conversation` - Беседа
  - `participant1`, `participant2` - Участники
  - `listing` - Связанное объявление (optional)
  - `unique_together` для предотвращения дубликатов
  - Автообновление `updated_at` при новом сообщении

- `Message` - Сообщение
  - `content` (max 5000 символов)
  - `is_read` - Статус прочтения
  - Ordering по `created_at` (старые первыми)

**Real-time Updates:**
```javascript
// JavaScript polling каждые 3 секунды
setInterval(() => {
    fetch(`/chat/api/messages/${conversationId}/?after=${lastMessageId}`)
        .then(response => response.json())
        .then(data => {
            // Добавить новые сообщения с escapeHtml()
        });
}, 3000);
```

**Уведомления:**
- Email при новом сообщении (только получателю!)
- Создание Notification в БД
- Auto-mark as read при открытии беседы

---

### 5. **core** - Ядро системы

**Модели:**
- `Notification` - Уведомления
  - Типы: new_message, purchase_request, request_accepted, etc.
  - `is_read`, `read_at` - Статус
  - Индексы для быстрого подсчета непрочитанных

**Utilities:**
- `email_utils.py` - Отправка email уведомлений
- `context_processors.py` - Глобальные данные (количество уведомлений)
- `middleware.py`:
  - `SimpleRateLimitMiddleware` - Защита от брутфорса
  - `SecurityHeadersMiddleware` - CSP, HSTS, XSS защита

---

## Безопасность

### 1. CSRF Protection
```python
# Все POST формы защищены
{% csrf_token %}

# AJAX запросы включают CSRF токен
headers: {'X-CSRFToken': getCookie('csrftoken')}
```

### 2. XSS Protection
```javascript
// Все пользовательские данные экранируются
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

### 3. SQL Injection Protection
```python
# Django ORM автоматически параметризует запросы
Listing.objects.filter(title__icontains=search)  # Safe
```

### 4. Rate Limiting
```python
RATE_LIMITS = {
    '/accounts/login/': (5, 300),        # 5 попыток за 5 минут
    '/accounts/register/': (3, 600),      # 3 попытки за 10 минут
    '/listing/create/': (10, 3600),       # 10 объявлений в час
}
```

### 5. Content Security Policy
```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://cdn.jsdelivr.net;
  style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline';
  img-src 'self' data: https:;
```

### 6. File Upload Validation
```python
# Валидация на сервере
- Размер: max 5MB
- Тип: JPEG, PNG, GIF, WebP
- imghdr проверка (не только content-type)
```

---

## База данных

### Schema Diagram

```
CustomUser ──1:1─→ Profile
    │                 │
    │                 └─→ Reviews received
    │
    ├──1:N─→ Listings ──1:N─→ PurchaseRequests ──1:N─→ Reviews
    │           │                   │
    │           └──1:N─→ Favorites  │
    │                               │
    ├──1:N─→ Conversations ──1:N─→ Messages
    │
    └──1:N─→ Notifications
```

### Индексы (24+)

**accounts:**
- `user` (ForeignKey, auto)
- `rating` (для сортировки)
- `is_verified, rating` (композитный)

**listings:**
- `game, status` (каталог по игре)
- `seller, status` (мои объявления)
- `created_at, status` (сортировка по дате)
- `search_vector` (GIN для full-text)
- `status, price` (сортировка по цене)

**transactions:**
- `buyer, status, created_at` (мои покупки)
- `seller, status, created_at` (мои продажи)
- `listing, status` (запросы по объявлению)

**chat:**
- `participant1, updated_at` (беседы пользователя)
- `conversation, is_read` (непрочитанные)

**core:**
- `user, is_read` (непрочитанные уведомления)
- `created_at` (сортировка)

### Constraints

```python
# Unique Together
- Profile: не нужен (OneToOne с User)
- Conversation: [participant1, participant2, listing]
- PurchaseRequest: [listing, buyer]
- Review: [purchase_request, reviewer]
- Favorite: [user, listing]

# Check Constraints (можно добавить)
- price >= 0
- rating between 0 and 5
- description length >= 10
```

---

## 🔄 Data Flow

### Пример: Создание запроса на покупку

```
1. User нажимает "Купить" на странице объявления
   ↓
2. listings/listing_detail.html
   ↓
3. POST /transactions/purchase-request/<listing_id>/create/
   ↓
4. transactions/views.py::purchase_request_create()
   ├─ Валидация (не свое объявление, доступно)
   ├─ Проверка существующего запроса
   └─ Создание PurchaseRequest
       ├─ status = 'pending'
       ├─ buyer = request.user
       └─ seller = listing.seller
   ↓
5. Signal / Email
   ├─ create_notification(seller, ...)
   └─ send_mail(seller.email, ...)
   ↓
6. Redirect → /transactions/purchase-request/<id>/
```

---

## Frontend Architecture

### Templates Hierarchy

```
base.html (Layout)
  ├─ listings/
  │   ├─ landing_page.html (Главная)
  │   ├─ catalog.html (Каталог)
  │   ├─ listing_detail.html
  │   └─ listing_create.html
  │
  ├─ accounts/
  │   ├─ register.html
  │   ├─ login.html
  │   ├─ profile.html
  │   └─ profile_edit.html
  │
  ├─ chat/
  │   ├─ conversations_list.html
  │   └─ conversation_detail.html
  │
  ├─ transactions/
  │   ├─ purchase_request_detail.html
  │   └─ review_create.html
  │
  └─ core/
      └─ notifications_list.html
```

### JavaScript Modules

```
static/js/
  ├─ toast-notifications.js   (Toast уведомления)
  ├─ chat-improvements.js     (Real-time чат)
  ├─ phone-formatter.js       (Форматирование телефона)
  └─ file-upload-fix.js       (Превью загрузки файлов)
```

### CSS Architecture

```css
:root {
    /* CSS Variables */
    --primary: #2563eb;
    --success: #059669;
    --danger: #dc2626;
}

/* Components */
- Buttons (.btn-primary, .btn-success)
- Cards (.card, .listing-item)
- Forms (.form-control, .form-select)
- Badges (.status-active, .status-sold)
- Chat (.message-bubble, .chat-container)
```

---

## 🔌 API Endpoints

### Chat API

```
GET  /chat/api/messages/<conversation_id>/?after=<last_id>
  → Получить новые сообщения
  Response: {
      "messages": [
          {"id": 123, "content": "...", "sender": "...", "created_at": "..."}
      ],
      "count": 1
  }
```

### Notifications API

```
GET  /notifications/unread-count/
  → Количество непрочитанных
  Response: {"count": 5}

POST /notifications/<id>/read/
  → Отметить как прочитанное
  Response: {"success": true}

POST /notifications/mark-all-read/
  → Отметить все как прочитанные
  Response: {"success": true}
```

### Favorites API

```
POST /listing/<id>/favorite/
  → Добавить/убрать из избранного (toggle)
  Response: {
      "success": true,
      "is_favorited": true,
      "message": "Добавлено в избранное"
  }
```

---

## Performance Optimizations

### 1. Database Queries

**N+1 Problem Solution:**
```python
# BAD
listings = Listing.objects.all()
for listing in listings:
    print(listing.seller.username)  # N+1 запросов!

# GOOD
listings = Listing.objects.select_related('seller').all()
for listing in listings:
    print(listing.seller.username)  # 1 запрос
```

**Prefetch Related:**
```python
# Для ManyToMany и обратных ForeignKey
conversations = Conversation.objects.prefetch_related(
    'messages',
    'messages__sender'
)
```

### 2. Caching Strategy

```python
# Homepage stats - 5 минут
cache.set('homepage_stats', stats, 300)

# Список игр - 1 час
cache.set('active_games', games, 3600)

# Количество уведомлений - 1 минута
cache.set(f'unread_notif_{user.id}', count, 60)
```

### 3. Pagination

```python
# Всегда используем пагинацию для больших списков
paginator = Paginator(queryset, 12)
page_obj = paginator.get_page(page_number)
```

### 4. Full-Text Search

```python
# PostgreSQL с русской морфологией
from django.contrib.postgres.search import SearchQuery, SearchRank

search_query = SearchQuery(search_term, config='russian')
listings = Listing.objects.annotate(
    rank=SearchRank('search_vector', search_query)
).filter(
    search_vector=search_query
).order_by('-rank')
```

---

## 🔧 Configuration Files

### settings.py

**Development:**
```python
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
CACHES = {'default': {'BACKEND': 'locmem.LocMemCache'}}
EMAIL_BACKEND = 'console.EmailBackend'
```

**Production:**
```python
DEBUG = False
ALLOWED_HOSTS = ['lootlink.ru']
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache'}}
EMAIL_BACKEND = 'smtp.EmailBackend'
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
```

---

## 🧪 Testing Strategy

### Test Coverage

```
accounts/tests.py       - 9 тестов (модели, views, forms)
listings/tests.py       - 8 тестов (модели, views)
transactions/tests.py   - 7 тестов (бизнес-логика)
chat/tests.py          - 15 тестов (сообщения, беседы)
core/tests.py          - 13 тестов (уведомления)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ВСЕГО                  - 52+ теста (coverage 65%+)
```

### Types of Tests

1. **Model Tests** - Проверка бизнес-логики моделей
2. **View Tests** - HTTP запросы и ответы
3. **Form Tests** - Валидация форм
4. **Integration Tests** - Полный user flow
5. **Security Tests** - CSRF, XSS, permissions

---

## 📦 Deployment

### Docker Containers

```yaml
services:
  db:         # PostgreSQL 15
  web:        # Django + Gunicorn
  redis:      # Redis 7 (cache)
  nginx:      # Nginx (reverse proxy)
```

### Scaling Strategy

**Horizontal Scaling:**
```yaml
# docker-compose.yml
web:
  deploy:
    replicas: 4  # 4 инстанса Django
    
  # Nginx автоматически балансирует
```

**Database:**
```
PostgreSQL Master-Slave Replication
  Master (write) → Slave (read)
```

**Cache:**
```
Redis Cluster или Redis Sentinel
для high availability
```

---

## 📈 Monitoring

### Sentry Integration

```python
# settings.py
sentry_sdk.init(
    dsn="https://...",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
)
```

### Logging

```
logs/
  ├─ lootlink.log    (INFO+)
  ├─ errors.log      (ERROR+)
  └─ security.log    (WARNING+ для django.security)
```

### Metrics to Monitor

- **Response time** (p50, p95, p99)
- **Error rate** (4xx, 5xx)
- **Database connections** (active, idle)
- **Cache hit rate** (Redis)
- **Queue length** (если используется Celery)

---

## 🔮 Future Improvements

### Phase 1: Payments
- Интеграция ЮKassa/Stripe
- Escrow система
- Wallet для пользователей

### Phase 2: Real-time
- WebSockets (Django Channels)
- Online статус пользователей
- Typing indicators в чате

### Phase 3: Advanced Features
- Machine Learning для рекомендаций
- Fraud detection
- Price prediction
- Automatic moderation

### Phase 4: Mobile
- REST API
- React Native app
- Push notifications

---

## 📞 Architecture Decisions

Все важные архитектурные решения документированы в `docs/architecture/ADR/`

Пример ADR (Architecture Decision Record):
- ADR-001: Почему PostgreSQL, а не MongoDB
- ADR-002: Почему не использу использованы Django Channels
- ADR-003: Polling vs WebSockets для чата

---

**Версия документа:** 1.0  
**Последнее обновление:** 27 октября 2025
