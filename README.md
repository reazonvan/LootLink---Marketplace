
<div align="center">

![LootLink](https://capsule-render.vercel.app/api?type=soft&color=gradient&customColorList=10,20,30&height=180&section=header&text=LootLink&fontSize=70&fontColor=fff&animation=fadeIn&fontAlignY=40&desc=🎮%20P2P%20Gaming%20Marketplace&descAlignY=70&descSize=25)

### **Trade. Chat. Game.**

*Прямая торговля игровыми предметами между игроками*

<br>

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-91.218.245.178-9b5de5?style=for-the-badge&logo=world&logoColor=white)](http://91.218.245.178)
[![GitHub Stars](https://img.shields.io/github/stars/reazonvan/LootLink---Marketplace?style=for-the-badge&logo=github&color=f15bb5)](https://github.com/reazonvan/LootLink---Marketplace/stargazers)
[![License](https://img.shields.io/badge/License-MIT-00bbf9?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-ff9e00?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

<br>

**[🚀 Live Demo](http://91.218.245.178)** • 
**[🐛 Report Bug](https://github.com/reazonvan/LootLink---Marketplace/issues)** • 
**[⭐ Star Project](https://github.com/reazonvan/LootLink---Marketplace)**

</div>

## ✨ **Почему выбирают LootLink?**

<div align="center">

| 🎯 **Для игроков** | 🔐 **Безопасность** | ⚡ **Производительность** |
|:-----------------|:-------------------|:------------------------|
| ✓ Без комиссий | ✓ CSRF защита | ✓ Быстрая загрузка |
| ✓ Прямые P2P сделки | ✓ Защита от SQL-инъекций | ✓ Адаптивный дизайн |
| ✓ Чат в реальном времени | ✓ Хеширование паролей | ✓ Оптимизированные запросы |
| ✓ Система рейтингов | ✓ Email верификация | ✓ Кэширование |

</div>

<br>

## 🏆 **Основные возможности**

<div align="center">

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 30px 0;">

<div align="center" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-radius: 15px; border-left: 4px solid #9b5de5;">
<h3>🛒 Умный маркетплейс</h3>
<p>Создание, поиск и фильтрация игровых предметов с изображениями</p>
</div>

<div align="center" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-radius: 15px; border-left: 4px solid #f15bb5;">
<h3>💬 Живой чат</h3>
<p>Прямая переписка между покупателями и продавцами</p>
</div>

<div align="center" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-radius: 15px; border-left: 4px solid #00bbf9;">
<h3>👤 Профили пользователей</h3>
<p>Профили с аватарами, историей сделок и отзывами</p>
</div>

<div align="center" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-radius: 15px; border-left: 4px solid #00f5d4;">
<h3>⭐ Система рейтингов</h3>
<p>Отзывы и репутация для каждого пользователя</p>
</div>

</div>
</div>

## 🚀 **Технологический стек**

<div align="center">

### **Backend**
![Django](https://img.shields.io/badge/Django-4.2-092E20?style=flat-square&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=flat-square&logo=redis&logoColor=white)

### **Frontend**
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.2-7952B3?style=flat-square&logo=bootstrap&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![jQuery](https://img.shields.io/badge/jQuery-3.6-0769AD?style=flat-square&logo=jquery&logoColor=white)

### **Infrastructure**
![Docker](https://img.shields.io/badge/Docker-✅-2496ED?style=flat-square&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-1.24-009639?style=flat-square&logo=nginx&logoColor=white)

</div>

## 📈 **Проектные метрики**

<div align="center">

```python
project_stats = {
    "строк_кода": "5,000+",
    "таблиц_в_БД": "15+",
    "API_эндпоинты": "40+",
    "HTML_шаблоны": "30+",
    "статические_файлы": "50+"
}
```

</div>

## 🎮 **Быстрый старт**

### **Локальная разработка**

```bash
# Клонируйте репозиторий
git clone https://github.com/reazonvan/LootLink---Marketplace.git
cd LootLink---Marketplace

# Создайте виртуальное окружение
python -m venv venv

# Активируйте окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Создайте базу данных
python manage.py migrate

# Создайте суперпользователя
python manage.py createsuperuser

# Запустите сервер
python manage.py runserver
```

### **Docker запуск**

```bash
# Запуск с Docker Compose
docker-compose up -d

# Остановка
docker-compose down
```

## 🏗️ **Архитектура проекта**

```mermaid
graph TB
    subgraph "Клиентский уровень"
        A[🌐 Веб-браузер] --> B[📱 Мобильные устройства]
    end
    
    subgraph "Веб-сервер"
        C[🔄 Nginx] --> D[📦 Статические файлы]
        C --> E[🐍 Gunicorn]
    end
    
    subgraph "Django приложение"
        F[🎯 Django] --> G[👤 Accounts App]
        F --> H[🛒 Listings App]
        F --> I[💬 Messenger App]
        
        G --> J[📄 Templates]
        H --> J
        I --> J
    end
    
    subgraph "Сервисы данных"
        K[(🗄️ PostgreSQL)] --> L[📊 Основные данные]
        M[(⚡ Redis)] --> N[🚀 Кэш]
    end
    
    subgraph "Файловая система"
        O[📁 Media files] --> P[🖼️ Изображения]
        Q[📁 Static files] --> R[🎨 CSS/JS]
    end
    
    A --> C
    E --> F
    F --> K
    F --> M
    F --> O
    F --> Q
    
    style F fill:#1a1a2e,stroke:#9b5de5,stroke-width:3px
    style K fill:#16213e,stroke:#00bbf9,stroke-width:2px
    style M fill:#0f3460,stroke:#f15bb5,stroke-width:2px
```

## 📁 **Структура проекта**

```
LootLink---Marketplace/
├── accounts/                    # Управление пользователями
│   ├── models.py              # CustomUser, Profile
│   ├── views.py               # Регистрация, вход, профиль
│   ├── forms.py               # Формы пользователей
│   └── templates/             # Шаблоны аутентификации
├── listings/                   # Маркетплейс
│   ├── models.py              # Listing, Category, Review
│   ├── views.py               # CRUD для объявлений
│   ├── forms.py               # Формы объявлений
│   └── templates/             # Шаблоны объявлений
├── messenger/                  # Система сообщений
│   ├── models.py              # Conversation, Message
│   ├── views.py               # Просмотр чатов
│   ├── urls.py                # Маршруты чата
│   └── templates/             # Шаблоны сообщений
├── static/                     # Статические файлы
│   ├── css/                   # Стили
│   ├── js/                    # JavaScript
│   └── images/                # Изображения
├── templates/                  # HTML шаблоны
│   ├── base.html             # Базовый шаблон
│   ├── listings/             # Шаблоны объявлений
│   └── accounts/             # Шаблоны аккаунтов
├── marketplace/               # Основное приложение
│   ├── settings.py           # Настройки Django
│   ├── urls.py               # Корневые URL
│   └── wsgi.py               # WSGI конфигурация
├── docker-compose.yml         # Docker Compose
├── Dockerfile                 # Docker конфигурация
├── requirements.txt           # Зависимости Python
└── manage.py                  # Django CLI
```

## 🔒 **Система безопасности**

<div align="center">

| Уровень | Защита | Статус |
|:--------|:-------|:-------|
| **Приложение** | CSRF токены | ✅ Включено |
| **База данных** | Защита от SQL-инъекций | ✅ ORM запросы |
| **Аутентификация** | Хеширование паролей | ✅ PBKDF2 |
| **Сессии** | Безопасные куки | ✅ HttpOnly, Secure |
| **Валидация** | Валидация форм | ✅ Django Forms |
| **Email** | Подтверждение Email | ✅ Обязательно |

</div>

## 🧪 **Тестирование**

```bash
# Запуск всех тестов
python manage.py test

# Запуск тестов конкретного приложения
python manage.py test accounts
python manage.py test listings
python manage.py test messenger
```

## 📊 **Оптимизация**

- **База данных**: Использование `select_related` и `prefetch_related`
- **Статические файлы**: Минификация CSS/JS в production
- **Изображения**: Оптимизация и сжатие
- **Шаблоны**: Кэширование шаблонов
- **Запросы**: Оптимизация запросов к базе данных

## 🌍 **Деплой**

### **Production настройки**

1. **Настройка окружения**
```bash
# Создайте .env файл
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,localhost
DATABASE_URL=postgresql://user:password@localhost:5432/lootlink
```

2. **Сборка статических файлов**
```bash
python manage.py collectstatic --noinput
```

3. **Запуск с Gunicorn**
```bash
gunicorn marketplace.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## 🤝 **Как внести вклад**

1. **Сделайте форк репозитория**
2. **Создайте ветку** (`git checkout -b feature/AmazingFeature`)
3. **Сделайте коммит** (`git commit -m 'Add AmazingFeature'`)
4. **Запушьте в ветку** (`git push origin feature/AmazingFeature`)
5. **Откройте Pull Request**

## 📞 **Контакты**

**Email:** ivanpetrov20066.ip@gmail.com  
**Демо:** [http://91.218.245.178](http://91.218.245.178)  
**GitHub Issues:** [Отчет об ошибках](https://github.com/reazonvan/LootLink---Marketplace/issues)

## 📄 **Лицензия**

Этот проект лицензирован под MIT License - смотрите файл [LICENSE](LICENSE) для деталей.

---

<div align="center">

### **История звёзд**

[![Star History Chart](https://api.star-history.com/svg?repos=reazonvan/LootLink---Marketplace&type=Date&theme=dark)](https://star-history.com/#reazonvan/LootLink---Marketplace&Date)

<br>

**Создано с ❤️ для игрового сообщества**

![Footer](https://capsule-render.vercel.app/api?type=soft&color=gradient&customColorList=10,20,30&height=80&section=footer&reversal=true&animation=fadeIn)

[⬆ Наверх](#)

</div>
```

