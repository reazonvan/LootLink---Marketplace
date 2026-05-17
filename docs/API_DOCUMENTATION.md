# API Документация LootLink

## Обзор

LootLink - это web-приложение на Django с традиционным server-side рендерингом. Ниже описаны основные эндпоинты и их использование.

## Аутентификация

### Регистрация
**URL:** `/accounts/register/`  
**Метод:** `GET`, `POST`  
**Доступ:** Публичный

**POST параметры:**
- `username` - Имя пользователя (обязательно, уникальное)
- `email` - Email (обязательно, уникальный)
- `password1` - Пароль (обязательно)
- `password2` - Подтверждение пароля (обязательно)

### Вход
**URL:** `/accounts/login/`  
**Метод:** `GET`, `POST`  
**Доступ:** Публичный

**POST параметры:**
- `username` - Имя пользователя
- `password` - Пароль

### Выход
**URL:** `/accounts/logout/`  
**Метод:** `GET`  
**Доступ:** Только авторизованные пользователи

## Профиль пользователя

### Просмотр профиля
**URL:** `/accounts/profile/<username>/`  
**Метод:** `GET`  
**Доступ:** Публичный

**Возвращает:**
- Информация о пользователе
- Рейтинг и статистика
- Отзывы о пользователе

### Редактирование профиля
**URL:** `/accounts/profile-edit/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только авторизованные (свой профиль)

**POST параметры:**
- `avatar` - Аватар (файл изображения)
- `bio` - О себе (текст)
- `phone` - Телефон
- `telegram` - Telegram username
- `discord` - Discord username
- `first_name` - Имя
- `last_name` - Фамилия

## Объявления

### Список объявлений (Главная)
**URL:** `/`  
**Метод:** `GET`  
**Доступ:** Публичный

**GET параметры (фильтры):**
- `game` - ID игры
- `min_price` - Минимальная цена
- `max_price` - Максимальная цена
- `search` - Поиск по названию/описанию
- `sort` - Сортировка (`-created_at`, `created_at`, `price`, `-price`)
- `page` - Номер страницы (пагинация)

### Детали объявления
**URL:** `/listing/<id>/`  
**Метод:** `GET`  
**Доступ:** Публичный

**Возвращает:**
- Полная информация об объявлении
- Информация о продавце
- Доступность для покупки

### Создание объявления
**URL:** `/listing/create/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только авторизованные пользователи

**POST параметры:**
- `game` - ID игры (обязательно)
- `title` - Название (обязательно)
- `description` - Описание (обязательно)
- `price` - Цена (обязательно, decimal)
- `image` - Изображение (обязательно, файл)

### Редактирование объявления
**URL:** `/listing/<id>/edit/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только создатель объявления

**POST параметры:**
- `title` - Название
- `description` - Описание
- `price` - Цена
- `image` - Изображение (необязательно)
- `status` - Статус (`active`, `reserved`, `sold`, `cancelled`)

### Удаление объявления
**URL:** `/listing/<id>/delete/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только создатель объявления

### Объявления по игре
**URL:** `/game/<slug>/`  
**Метод:** `GET`  
**Доступ:** Публичный

**GET параметры:**
- `page` - Номер страницы

## Транзакции

### Создание запроса на покупку
**URL:** `/transactions/purchase-request/<listing_id>/create/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только авторизованные (не владелец объявления)

**POST параметры:**
- `message` - Сообщение продавцу (необязательно)

### Детали запроса на покупку
**URL:** `/transactions/purchase-request/<id>/`  
**Метод:** `GET`  
**Доступ:** Только участники сделки (покупатель/продавец)

**Возвращает:**
- Информация о сделке
- Статус сделки
- Доступные действия

### Принять запрос (продавец)
**URL:** `/transactions/purchase-request/<id>/accept/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только продавец

**Результат:**
- Статус меняется на `accepted`
- Объявление резервируется

### Отклонить запрос (продавец)
**URL:** `/transactions/purchase-request/<id>/reject/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только продавец

**Результат:**
- Статус меняется на `rejected`

### Завершить сделку (продавец)
**URL:** `/transactions/purchase-request/<id>/complete/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только продавец

**Результат:**
- Статус меняется на `completed`
- Объявление помечается как проданное
- Обновляется статистика пользователей

### Отменить запрос (покупатель)
**URL:** `/transactions/purchase-request/<id>/cancel/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только покупатель

**Результат:**
- Статус меняется на `cancelled`
- Если объявление было зарезервировано, возвращается в активные

### Создание отзыва
**URL:** `/transactions/review/<purchase_request_id>/create/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только участники завершенной сделки

**POST параметры:**
- `rating` - Оценка (1-5, обязательно)
- `comment` - Комментарий (необязательно)

**Результат:**
- Отзыв создается
- Обновляется рейтинг получателя отзыва

## Чат

### Список бесед
**URL:** `/chat/`  
**Метод:** `GET`  
**Доступ:** Только авторизованные пользователи

**Возвращает:**
- Список всех бесед пользователя
- Последнее сообщение в каждой беседе
- Количество непрочитанных сообщений

### Детали беседы
**URL:** `/chat/conversation/<id>/`  
**Метод:** `GET`, `POST`  
**Доступ:** Только участники беседы

**GET:** Показывает историю сообщений и форму отправки

**POST параметры:**
- `content` - Текст сообщения (обязательно)

**Результат POST:**
- Сообщение отправляется
- Все непрочитанные сообщения помечаются как прочитанные

### Начать беседу
**URL:** `/chat/start/<listing_id>/`  
**Метод:** `GET`  
**Доступ:** Только авторизованные (не владелец объявления)

**Результат:**
- Если беседа существует - перенаправление на неё
- Если нет - создается новая беседа и открывается

## Личный кабинет

### Мои объявления
**URL:** `/accounts/my-listings/`  
**Метод:** `GET`  
**Доступ:** Только авторизованные

### Мои покупки
**URL:** `/accounts/my-purchases/`  
**Метод:** `GET`  
**Доступ:** Только авторизованные

### Мои продажи
**URL:** `/accounts/my-sales/`  
**Метод:** `GET`  
**Доступ:** Только авторизованные

## Модели данных

### CustomUser
```python
{
    "id": int,
    "username": str,
    "email": str,
    "first_name": str,
    "last_name": str,
    "date_joined": datetime,
    "is_active": bool
}
```

### Profile
```python
{
    "id": int,
    "user": int (User ID),
    "avatar": str (URL),
    "bio": str,
    "phone": str,
    "telegram": str,
    "discord": str,
    "rating": decimal,
    "total_sales": int,
    "total_purchases": int
}
```

### Listing
```python
{
    "id": int,
    "seller": int (User ID),
    "game": int (Game ID),
    "title": str,
    "description": str,
    "price": decimal,
    "image": str (URL),
    "status": str, # active, reserved, sold, cancelled
    "created_at": datetime,
    "updated_at": datetime
}
```

### PurchaseRequest
```python
{
    "id": int,
    "listing": int (Listing ID),
    "buyer": int (User ID),
    "seller": int (User ID),
    "status": str, # pending, accepted, rejected, completed, cancelled
    "message": str,
    "created_at": datetime,
    "updated_at": datetime,
    "completed_at": datetime (nullable)
}
```

### Review
```python
{
    "id": int,
    "purchase_request": int,
    "reviewer": int (User ID),
    "reviewed_user": int (User ID),
    "rating": int, # 1-5
    "comment": str,
    "created_at": datetime
}
```

### Conversation
```python
{
    "id": int,
    "participant1": int (User ID),
    "participant2": int (User ID),
    "listing": int (Listing ID, nullable),
    "created_at": datetime,
    "updated_at": datetime
}
```

### Message
```python
{
    "id": int,
    "conversation": int (Conversation ID),
    "sender": int (User ID),
    "content": str,
    "is_read": bool,
    "created_at": datetime
}
```

## Коды ответов

- `200 OK` - Успешный запрос
- `302 Found` - Редирект
- `400 Bad Request` - Ошибка валидации данных
- `403 Forbidden` - Нет доступа
- `404 Not Found` - Ресурс не найден
- `500 Internal Server Error` - Ошибка сервера

## Примечания

- Все даты в формате ISO 8601 (UTC)
- Цены в рублях с точностью до 2 знаков после запятой
- Изображения загружаются в S3 или локально (в зависимости от USE_S3)
- Для авторизации используется Django Session Authentication
- CSRF защита включена для всех POST запросов

---

**Версия API:** 1.0  
**Последнее обновление:** 2025

