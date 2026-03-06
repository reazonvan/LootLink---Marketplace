# 📖 Пошаговое руководство по запуску LootLink

Это подробное руководство поможет вам запустить проект LootLink на вашем компьютере.

## Шаг 1: Установка Python

### Windows:
1. Скачайте Python с [python.org](https://www.python.org/downloads/)
2. Установите, **обязательно отметив галочку "Add Python to PATH"**
3. Проверьте установку:
```bash
python --version
```

### Linux/Mac:
Python обычно уже установлен. Проверьте:
```bash
python3 --version
```

## Шаг 2: Установка PostgreSQL

### Windows:
1. Скачайте PostgreSQL с [postgresql.org](https://www.postgresql.org/download/windows/)
2. Установите с настройками по умолчанию
3. Запомните пароль суперпользователя!

### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Mac:
```bash
brew install postgresql
brew services start postgresql
```

## Шаг 3: Создание базы данных

Откройте pgAdmin или командную строку PostgreSQL:

```bash
# Windows: откройте SQL Shell (psql)
# Linux/Mac: выполните в терминале
sudo -u postgres psql

# В консоли PostgreSQL:
CREATE DATABASE lootlink_db;
CREATE USER lootlink_user WITH PASSWORD 'mypassword123';
GRANT ALL PRIVILEGES ON DATABASE lootlink_db TO lootlink_user;
\q
```

## Шаг 4: Настройка проекта

### 1. Откройте командную строку/терминал в папке проекта:
```bash
cd C:\Users\ivanp\Desktop\LootLink
```

### 2. Создайте виртуальное окружение:
```bash
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux/Mac:
python3 -m venv venv
source venv/bin/activate
```

Вы должны увидеть `(venv)` в начале строки.

### 3. Установите зависимости:
```bash
pip install -r requirements/development.txt
```

Подождите, пока все библиотеки установятся.

## Шаг 5: Настройка переменных окружения

Создайте файл `.env` в корне проекта (рядом с `manage.py`):

```env
# Django settings
SECRET_KEY=django-insecure-your-secret-key-here-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database settings
DB_NAME=lootlink_db
DB_USER=lootlink_user
DB_PASSWORD=mypassword123
DB_HOST=localhost
DB_PORT=5432

# Media storage (локально)
USE_S3=False
```

**Важно:** Замените `mypassword123` на ваш реальный пароль от PostgreSQL!

## Шаг 6: Создание структуры базы данных

Выполните команды по очереди:

```bash
# 1. Создайте миграции
python manage.py makemigrations

# 2. Примените миграции
python manage.py migrate

# 3. Создайте суперпользователя
python manage.py createsuperuser
```

При создании суперпользователя введите:
- Имя пользователя (например: admin)
- Email (можно оставить пустым)
- Пароль (введите дважды, символы не отображаются!)

## Шаг 7: Создание папок для медиа

```bash
# Windows:
mkdir media
mkdir media\avatars
mkdir media\listings
mkdir media\games
mkdir static

# Linux/Mac:
mkdir -p media/{avatars,listings,games}
mkdir static
```

## Шаг 8: Запуск сервера

```bash
python manage.py runserver
```

Вы должны увидеть:
```
Starting development server at http://127.0.0.1:8000/
```

## Шаг 9: Первоначальная настройка

### 1. Откройте админ-панель:
Перейдите в браузере: http://127.0.0.1:8000/admin

Войдите с данными суперпользователя.

### 2. Добавьте игры:
В админке перейдите в раздел "Игры" → "Добавить игру"

Создайте несколько игр, например:
- **Название**: Dota 2, **Slug**: dota-2
- **Название**: CS:GO, **Slug**: csgo
- **Название**: World of Warcraft, **Slug**: world-of-warcraft

### 3. Создайте тестовое объявление:
- Перейдите на главную: http://127.0.0.1:8000
- Нажмите "Создать объявление"
- Заполните форму и загрузите изображение

## 🎉 Готово!

Теперь вы можете:
- Просматривать каталог объявлений
- Создавать новые объявления
- Отправлять запросы на покупку
- Общаться в чате
- Оставлять отзывы

## 🐛 Возможные проблемы

### Ошибка подключения к базе данных:
- Проверьте, что PostgreSQL запущен
- Проверьте пароль в `.env`
- Убедитесь, что база данных создана

### Ошибка импорта модулей:
```bash
pip install -r requirements/development.txt --upgrade
```

### Ошибка прав доступа к папке media:
```bash
# Windows: откройте папку свойства → Безопасность → дайте полные права
# Linux:
chmod -R 755 media/
```

### Не отображаются изображения:
Убедитесь, что `DEBUG=True` в `.env`

## 📱 Тестирование функционала

1. **Регистрация**: http://127.0.0.1:8000/accounts/register/
2. **Создание объявления**: http://127.0.0.1:8000/listing/create/
3. **Просмотр профиля**: http://127.0.0.1:8000/accounts/profile/admin/
4. **Просмотр объявлений**: http://127.0.0.1:8000/

## 🔄 Остановка и перезапуск

### Остановка сервера:
Нажмите `Ctrl+C` в терминале

### Перезапуск:
```bash
# Активируйте виртуальное окружение (если не активировано)
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Запустите сервер
python manage.py runserver
```

## 📝 Полезные команды

```bash
# Создать нового пользователя (админ)
python manage.py createsuperuser

# Очистить базу данных
python manage.py flush

# Посмотреть список всех URL
python manage.py show_urls

# Запустить в другом порту
python manage.py runserver 8080
```

---

**Если что-то не работает, проверьте:**
1. ✅ PostgreSQL запущен?
2. ✅ Виртуальное окружение активировано?
3. ✅ Все зависимости установлены?
4. ✅ Файл `.env` создан правильно?
5. ✅ Миграции применены?

**Успешного запуска! 🚀**

