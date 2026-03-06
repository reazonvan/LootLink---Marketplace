# Задачи редизайна LootLink в Pencil

## Дата: 2026-03-06

---

## 🎯 Цель
Создать новый уникальный дизайн для LootLink в Pencil перед реализацией в коде.

---

## 📋 Приоритетные страницы для редизайна

### 1. Главная страница (Homepage)
**Текущие проблемы:**
- Стандартный Bootstrap дизайн
- Недостаточно уникальности
- Hero section можно улучшить

**Что нужно в Pencil:**
- [ ] Wireframe главной страницы
- [ ] Mockup Desktop (1920x1080)
- [ ] Mockup Mobile (375x667)

**Элементы:**
- Hero Section (заголовок, 2 CTA кнопки, 3 статистики)
- How It Works (4 шага с иконками)
- Latest Listings (сетка 4x2)
- Security Guarantees (3 карточки)
- Footer

---

### 2. Каталог игр (Games Catalog)
**Текущие проблемы:**
- Карточки игр однообразные
- Можно добавить больше информации

**Что нужно в Pencil:**
- [ ] Wireframe каталога
- [ ] Mockup Desktop
- [ ] Mockup Mobile

**Элементы:**
- Сетка карточек игр
- Поиск и фильтры
- Категории

---

### 3. Карточка товара (Listing Detail)
**Текущие проблемы:**
- Галерея изображений базовая
- Блок продавца можно выделить лучше

**Что нужно в Pencil:**
- [ ] Wireframe карточки товара
- [ ] Mockup Desktop
- [ ] Mockup Mobile

**Элементы:**
- Галерея изображений (большая + превью)
- Информация о товаре
- Блок продавца (с бейджами)
- CTA кнопки
- Похожие товары

---

### 4. Профиль пользователя (Profile)
**Текущие проблемы:**
- Бейджи можно показать лучше
- Статистика не очень заметна

**Что нужно в Pencil:**
- [ ] Wireframe профиля
- [ ] Mockup Desktop
- [ ] Mockup Mobile

**Элементы:**
- Header профиля (аватар, бейджи, статистика)
- Табы (Объявления, Отзывы, О себе)
- Сетка объявлений
- Рейтинг и отзывы

---

### 5. Чат (Chat)
**Текущие проблемы:**
- Можно сделать более современным
- Мобильная версия требует улучшений

**Что нужно в Pencil:**
- [ ] Wireframe чата
- [ ] Mockup Desktop
- [ ] Mockup Mobile

**Элементы:**
- Список диалогов
- Окно чата
- Поле ввода
- Индикатор печати

---

## 🎨 Дизайн-система (использовать в Pencil)

### Цвета:
- Primary: `#2563eb` (синий)
- Success: `#10b981` (зеленый)
- Warning: `#f59e0b` (оранжевый)
- Danger: `#ef4444` (красный)
- Text: `#1e293b` (темно-серый)
- Background: `#f8fafc` (светло-серый)
- White: `#ffffff`

### Иконки:
- Только Bootstrap Icons
- Размеры: 16px, 20px, 24px, 32px

### Типографика:
- Заголовки: 24-32px, weight 600-700
- Текст: 14-16px, weight 400-500
- Мелкий текст: 12px

---

## 📝 Процесс работы

### Шаг 1: Wireframes (каркасы)
1. Открой Pencil
2. Создай новый проект: "LootLink Redesign"
3. Создай страницы для каждой секции
4. Используй простые прямоугольники и текст
5. Определи структуру и расположение элементов

### Шаг 2: Mockups (макеты)
1. Дублируй wireframes
2. Примени цвета из дизайн-системы
3. Добавь реальный текст
4. Вставь иконки Bootstrap Icons
5. Настрой типографику

### Шаг 3: Экспорт
1. Экспортируй все страницы в PNG
2. Сохрани в папку `D:\LootLink---Marketplace\design-exports\`
3. Создай PDF презентацию

### Шаг 4: Реализация
1. Покажи экспорты для обсуждения
2. После утверждения - верстка в HTML/CSS
3. Интеграция с Django

---

## ✅ Чеклист

### Перед началом:
- [ ] Запустил Pencil
- [ ] Создал проект "LootLink Redesign"
- [ ] Изучил PENCIL_DESIGN_GUIDE.md
- [ ] Изучил PROJECT_RULES.md (без смайликов!)

### Wireframes:
- [ ] Homepage
- [ ] Games Catalog
- [ ] Listing Detail
- [ ] Profile
- [ ] Chat

### Mockups Desktop:
- [ ] Homepage
- [ ] Games Catalog
- [ ] Listing Detail
- [ ] Profile
- [ ] Chat

### Mockups Mobile:
- [ ] Homepage
- [ ] Games Catalog
- [ ] Listing Detail
- [ ] Profile
- [ ] Chat

### Экспорт:
- [ ] Все wireframes в PNG
- [ ] Все mockups в PNG
- [ ] PDF презентация

---

## 🚀 Начни с этого:

1. **Запусти Pencil** (найди в меню Пуск)
2. **Создай новый документ:** File → New
3. **Выбери шаблон:** Web Page
4. **Создай первую страницу:** "Homepage - Wireframe"
5. **Начни с Hero Section:**
   - Добавь Rectangle для фона
   - Добавь Text для заголовка
   - Добавь 2 Button для CTA
   - Добавь 3 блока для статистики

---

## 📁 Структура файлов

Сохраняй файлы так:
```
D:\LootLink---Marketplace\
├── design-pencil/
│   ├── LootLink-Wireframes.epgz
│   ├── LootLink-Mockups.epgz
│   └── LootLink-Components.epgz
└── design-exports/
    ├── wireframes/
    │   ├── homepage.png
    │   ├── catalog.png
    │   └── ...
    └── mockups/
        ├── homepage-desktop.png
        ├── homepage-mobile.png
        └── ...
```

---

**После создания дизайнов в Pencil - покажи экспорты для обсуждения и реализации.**
