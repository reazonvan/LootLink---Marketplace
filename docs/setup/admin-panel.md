# Кастомная админ-панель

Админ-панель LootLink для управления маркетплейсом: модерация, пользователи, сделки, споры, жалобы и логи безопасности. Отдельный интерфейс поверх Django-механизмов, с AJAX-операциями и графиками. Стандартный Django Admin остаётся доступен для сложных операций.

## Быстрый старт

```bash
python manage.py migrate
python manage.py runserver
```

Открыть `http://127.0.0.1:8000/custom-admin/` и войти под staff-аккаунтом.

После первого запуска стоит проверить:

- [ ] панель открывается (`/custom-admin/`), dashboard показывает статистику
- [ ] графики и счётчики в sidebar работают
- [ ] AJAX-действия (верификация, модерация) проходят без перезагрузки
- [ ] мобильная версия корректна

## Доступ и права

URL: `/custom-admin/`

- **Владелец** (`is_superuser`) — полный доступ.
- **Администратор** (`is_staff`) — полный доступ к управлению.
- **Модератор** (`profile.is_moderator`) — доступ к модерации.

## Разделы

### Dashboard — `/custom-admin/`

Общая статистика (пользователи, объявления, сделки), графики регистраций и объявлений (Chart.js), алерты по спорам/жалобам/безопасности, топ игр, последние пользователи и объявления, финансовая сводка. Быстрые переходы к модерации, спорам и проверке безопасности.

### Пользователи — `/custom-admin/users/`

Таблица с поиском по имени и email, фильтрами по роли и верификации. Быстрые действия: верификация, назначение модератором, блокировка/разблокировка. Детальная страница — профиль, рейтинг, последние объявления и покупки, логи безопасности.

### Модерация объявлений — `/custom-admin/listings/`

Карточки с превью изображений, поиск и фильтры по статусу и игре. По умолчанию показываются объявления на модерации (`status='pending'`). Действия: одобрить, отклонить с указанием причины, удалить. Детальная страница — полное изображение и описание, информация о продавце, жалобы (если есть).

### Сделки — `/custom-admin/transactions/`

Список транзакций с поиском по покупателю, продавцу и товару, фильтром по статусу. Действие — отмена активной сделки. Отображает ID, стороны, товар и сумму, статус, дату.

### Споры — `/custom-admin/disputes/`

Список споров с фильтром по статусу. Разрешение: выбор победителя (покупатель/продавец), текст решения, автоматическое логирование. Детальная страница — участники, доказательства, история.

### Жалобы — `/custom-admin/reports/`

Список жалоб с превью объявления и причиной. Действия: заблокировать объявление, отметить жалобу необоснованной, открыть объявление на сайте.

### Логи безопасности — `/custom-admin/security/`

Последние 100 записей с фильтрами по уровню риска, типу действия и периоду, цветовой индикацией риска и ссылками на пользователей. События: неудачные входы, блокировки, подозрительная активность, действия админов, изменение ролей.

### Настройки — `/custom-admin/settings/`

Режим отладки, состояние БД и Redis, быстрые ссылки на Django Admin и сайт.

## API

POST-эндпоинты доступны только авторизованным админам/модераторам:

```
POST /custom-admin/api/users/<id>/verify/        — верифицировать
POST /custom-admin/api/users/<id>/ban/           — заблокировать
POST /custom-admin/api/users/<id>/unban/         — разблокировать
POST /custom-admin/api/users/<id>/moderator/     — назначить модератором
POST /custom-admin/api/listings/<id>/approve/    — одобрить
POST /custom-admin/api/listings/<id>/reject/     — отклонить
POST /custom-admin/api/listings/<id>/delete/     — удалить
POST /custom-admin/api/transactions/<id>/cancel/ — отменить сделку
POST /custom-admin/api/disputes/<id>/resolve/    — разрешить спор
POST /custom-admin/api/reports/<id>/process/     — обработать жалобу
GET  /custom-admin/api/stats/?period=7           — статистика за период
```

Пример AJAX-вызова через глобальные хелперы:

```javascript
async function verifyUser(userId) {
    const result = await adminAjax(`/custom-admin/api/users/${userId}/verify/`);
    if (result.success) {
        showToast(result.message, 'success');
        location.reload();
    } else {
        showToast(result.message, 'danger');
    }
}
```

`window.adminAjax(url, data)` — запрос с CSRF-токеном, `window.showToast(message, type)` — уведомление.

## Дизайн

Тёмный sidebar, светлый контент, карточки с тенями, бейджи статусов, toast-уведомления, графики Chart.js. Цветовая схема (CSS-переменные в `admin_panel/templates/admin_panel/base.html`, блок `:root`):

```css
:root {
    --admin-primary: #6366F1;   /* индиго, основной */
    --sidebar-bg:    #1F2937;   /* тёмно-серый sidebar */
    /* success #10B981, danger #EF4444, warning #F59E0B */
}
```

Адаптивность: на десктопе (>768px) sidebar развёрнут, на мобильных (<768px) скрыт и открывается кнопкой.

## Техническая структура

```
admin_panel/
├── urls.py
├── views.py            # основные views
├── api_views.py        # AJAX-эндпоинты
├── middleware.py       # счётчики для sidebar (AdminPanelContextMiddleware)
└── templates/admin_panel/
    ├── base.html       # layout + стили
    ├── dashboard.html
    ├── users_list.html / user_detail.html
    ├── listings_moderation.html / listing_detail.html
    ├── transactions_list.html / transaction_detail.html
    ├── disputes_list.html / dispute_detail.html
    ├── reports_list.html
    ├── security_logs.html
    └── settings.html
```

Зависимости: Django 5.2, Chart.js (графики), кастомный CSS (без Bootstrap).

## Безопасность

CSRF-токены на всех POST, проверка прав в каждом view, rate limiting через middleware. Все действия админов пишутся в `SecurityAuditLog` (верификации, блокировки, модерация, разрешение споров, изменение ролей).

## Кастомизация

**Цвета** — переменные в блоке `:root` в `base.html`.

**Новый раздел** — view в `views.py`, route в `urls.py`, template, ссылка в sidebar (`base.html`).

**Новый API-эндпоинт** — функция в `api_views.py`, route в `urls.py` (раздел API), JS-функция в template.

## Решение проблем

**Счётчики в sidebar показывают нули** — добавьте middleware в `MIDDLEWARE`:

```python
MIDDLEWARE = [
    # ...
    'admin_panel.middleware.AdminPanelContextMiddleware',
]
```

**404 при открытии панели** — проверьте подключение в `config/urls.py`:

```python
path('custom-admin/', include('admin_panel.urls')),
```

**AJAX даёт 403 CSRF** — убедитесь, что запрос идёт через `adminAjax()` (она передаёт токен).

## FAQ

**Как дать доступ к панели?** Через Django Admin (`/admin/`): Accounts → Profiles → отметить «Is moderator», либо Custom users → «Staff status».

**Чем отличается от Django Admin?** Визуальная модерация с превью, графики, AJAX без перезагрузки, мобильная версия. Django Admin остаётся для сложных операций и настроек.

**Можно ли работать с телефона?** Да, панель адаптивна.
