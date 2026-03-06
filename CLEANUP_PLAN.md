# 🧹 План очистки и реорганизации проекта LootLink

**Дата:** 2026-03-06
**Статус:** В процессе
**Цель:** Удалить дубликаты, мусор, реорганизовать структуру по best practices

---

## 📊 Текущее состояние

### Проблемы:
- ✗ 22 markdown файла в корне (норма: 3-5)
- ✗ Дубликаты документации (SETUP, START, READY)
- ✗ Архив lootlink_deploy.tar.gz (374KB) в git
- ✗ db.sqlite3 в корне (1MB) - не должен быть в git
- ✗ IDE-специфичные папки (.cursor, .vscode)
- ✗ design-exports/, design-pencil/ - не нужны в production
- ✗ Множество setup скриптов с дублированием

---

## 🎯 Фаза 1: Удаление дубликатов документации (КРИТИЧНО)

### Корневые MD файлы для УДАЛЕНИЯ (15 файлов):

#### Группа "Setup/Start" - оставить только README.md
```bash
# УДАЛИТЬ:
- ADMIN_PANEL_QUICKSTART.md      → переместить в docs/
- DEPLOYMENT_CHECKLIST.md        → переместить в docs/
- EMOJI_CLEANUP_COMPLETE.md      → удалить (временный файл)
- IMPLEMENTATION_SUMMARY.md      → удалить (устарело)
- MCP_STATUS.md                  → удалить (временный статус)
- QUICK_REFERENCE.md             → переместить в docs/
- QUICK_START_GUIDE.md           → объединить с README.md
- README_SETUP.md                → объединить с README.md
- READY_TO_GO.md                 → удалить (дубликат)
- REDESIGN_STATUS.md             → удалить (временный)
- SETUP_COMPLETE.md              → удалить (временный)
- START_DESIGN.md                → удалить (временный)
- START_HERE.md                  → удалить (дубликат README)
- VENV_FIX.md                    → переместить в docs/troubleshooting/
- WINDOWS_FIX.md                 → переместить в docs/troubleshooting/
- WINDOWS_SETUP.md               → переместить в docs/
- WORK_COMPLETED.md              → удалить (временный)
```

#### Группа "Design" - переместить в docs/design/
```bash
- DESIGN_WORKFLOW.md             → docs/design/
```

### Оставить в корне (5 файлов):
```
✓ README.md                      - главная документация
✓ CHANGELOG.md                   - история изменений
✓ CONTRIBUTING.md                - гайд для контрибьюторов
✓ PROJECT_RULES.md               - правила проекта
✓ LICENSE (если есть)            - лицензия
```

---

## 🎯 Фаза 2: Очистка временных и служебных файлов

### Удалить из git:
```bash
# Архивы
rm lootlink_deploy.tar.gz        # 374KB - не должен быть в git

# База данных разработки
rm db.sqlite3                    # 1MB - только для локальной разработки

# Временные файлы
rm CHANGES_SUMMARY.txt
rm FINAL_SUMMARY.txt
rm env.example.txt               # дубликат .env.example
```

### Обновить .gitignore:
```gitignore
# Добавить:
*.tar.gz
*.zip
db.sqlite3
*.sqlite3
.cursor/
.vscode/
design-exports/
design-pencil/
```

---

## 🎯 Фаза 3: Реорганизация директорий

### 3.1 Создать структуру docs/
```
docs/
├── setup/
│   ├── quickstart.md           ← QUICK_START_GUIDE.md
│   ├── windows.md              ← WINDOWS_SETUP.md
│   └── admin-panel.md          ← ADMIN_PANEL_QUICKSTART.md
├── deployment/
│   ├── checklist.md            ← DEPLOYMENT_CHECKLIST.md
│   └── production.md           ← docs/DEPLOYMENT.md
├── troubleshooting/
│   ├── venv.md                 ← VENV_FIX.md
│   └── windows.md              ← WINDOWS_FIX.md
├── design/
│   └── workflow.md             ← DESIGN_WORKFLOW.md
└── reference/
    └── quick-reference.md      ← QUICK_REFERENCE.md
```

### 3.2 Удалить ненужные директории
```bash
# Design файлы (если не используются активно)
rm -rf design-exports/          # экспорты дизайна
rm -rf design-pencil/           # исходники дизайна

# IDE конфиги (добавить в .gitignore)
# .cursor/ - оставить в .gitignore
# .vscode/ - оставить только settings.json и launch.json
```

### 3.3 Очистка scripts/
```bash
# Проверить дубликаты:
scripts/
├── setup_production.sh         # основной
├── deploy_with_smoke.sh        # CI/CD
├── backup_db.sh                # бэкапы
├── restore_db.sh
└── docker-entrypoint.sh        # Docker

# Удалить если дублируются:
- setup.sh (в корне)            # если дублирует scripts/setup_production.sh
- setup.bat (в корне)           # если дублирует
```

---

## 🎯 Фаза 4: Консолидация setup скриптов

### Текущие setup файлы:
```
./setup.bat
./setup.sh
./setup_venv.bat
./setup_venv.ps1
scripts/setup_production.sh
```

### Решение:
```bash
# Оставить:
scripts/setup_dev.sh            # для разработки
scripts/setup_production.sh     # для production

# Удалить из корня:
rm setup.bat
rm setup.sh
rm setup_venv.bat
rm setup_venv.ps1
```

### Создать единый Makefile:
```makefile
# Makefile уже есть - проверить и дополнить
make setup-dev          # локальная разработка
make setup-prod         # production
make test               # тесты
make lint               # линтеры
```

---

## 🎯 Фаза 5: Очистка requirements

### Текущая структура:
```
requirements.txt
requirements-dev.txt
requirements/
├── base.txt
├── development.txt
└── production.txt
```

### Проблема: Дублирование

### Решение:
```bash
# Вариант 1: Использовать только requirements/
rm requirements.txt
rm requirements-dev.txt

# Вариант 2: Использовать только корневые файлы
rm -rf requirements/

# Рекомендация: Вариант 1 (requirements/ директория)
```

---

## 🎯 Фаза 6: Очистка тестов

### Проверить дубликаты:
```bash
# 509 тестовых файлов - проверить:
find . -name "*test*.py" -type f | grep -v ".venv"

# Удалить:
- Пустые test файлы
- Дубликаты тестов
- Закомментированные тесты
```

---

## 🎯 Фаза 7: Финальная структура корня

### Идеальная структура:
```
LootLink---Marketplace/
├── .github/              # CI/CD workflows
├── accounts/             # Django app
├── admin_panel/          # Django app
├── api/                  # Django app
├── chat/                 # Django app
├── config/               # Django settings
├── core/                 # Django app
├── docs/                 # 📚 ВСЯ документация
├── listings/             # Django app
├── logs/                 # Логи (в .gitignore)
├── media/                # User uploads (в .gitignore)
├── nginx/                # Nginx конфиги
├── payments/             # Django app
├── scripts/              # Утилиты и скрипты
├── static/               # Статика
├── staticfiles/          # Собранная статика (в .gitignore)
├── templates/            # Django templates
├── tests/                # Интеграционные тесты
├── transactions/         # Django app
├── .dockerignore
├── .editorconfig
├── .env.example          # Пример конфига
├── .flake8
├── .gitignore
├── .pre-commit-config.yaml
├── Caddyfile
├── CHANGELOG.md          # 📝 История изменений
├── CONTRIBUTING.md       # 🤝 Гайд для контрибьюторов
├── docker-compose.yml
├── Dockerfile
├── LICENSE               # Лицензия
├── Makefile              # Команды для разработки
├── manage.py
├── manifest.json
├── PROJECT_RULES.md      # 📋 Правила проекта
├── pyproject.toml
├── README.md             # 📖 Главная документация
├── requirements.txt      # или requirements/
└── robots.txt
```

---

## 📋 Чеклист выполнения

### Фаза 1: Документация
- [ ] Создать docs/setup/, docs/deployment/, docs/troubleshooting/
- [ ] Переместить 15 MD файлов из корня в docs/
- [ ] Объединить дубликаты в README.md
- [ ] Удалить временные MD файлы

### Фаза 2: Временные файлы
- [ ] Удалить lootlink_deploy.tar.gz
- [ ] Удалить db.sqlite3
- [ ] Удалить *.txt файлы (кроме robots.txt)
- [ ] Обновить .gitignore

### Фаза 3: Директории
- [ ] Удалить/переместить design-exports/
- [ ] Удалить/переместить design-pencil/
- [ ] Очистить .cursor/ (добавить в .gitignore)
- [ ] Очистить .vscode/ (оставить только нужное)

### Фаза 4: Setup скрипты
- [ ] Удалить дубликаты setup из корня
- [ ] Консолидировать в scripts/
- [ ] Обновить Makefile

### Фаза 5: Requirements
- [ ] Выбрать стратегию (корень или requirements/)
- [ ] Удалить дубликаты
- [ ] Обновить документацию

### Фаза 6: Тесты
- [ ] Найти и удалить пустые тесты
- [ ] Удалить дубликаты
- [ ] Проверить покрытие

### Фаза 7: Финальная проверка
- [ ] Запустить тесты
- [ ] Проверить Docker build
- [ ] Обновить README.md
- [ ] Создать git commit

---

## ⚠️ Важные предупреждения

1. **Перед удалением:**
   - Создать backup: `git branch backup-before-cleanup`
   - Проверить что файлы не используются в коде

2. **Не удалять:**
   - Файлы из .github/workflows/ (CI/CD)
   - Конфиги (.flake8, .editorconfig, etc.)
   - requirements файлы до выбора стратегии

3. **После очистки:**
   - Запустить полный тест suite
   - Проверить Docker build
   - Обновить документацию

---

## 📈 Ожидаемый результат

### До:
- 22 MD файла в корне
- 374KB архив в git
- 1MB db.sqlite3 в git
- Дубликаты документации
- Неорганизованные скрипты

### После:
- 5 MD файлов в корне
- Чистый git (без бинарников)
- Организованная docs/ структура
- Консолидированные скрипты
- Понятная структура проекта

### Выгода:
- ✅ Легче ориентироваться новым разработчикам
- ✅ Меньше размер репозитория
- ✅ Проще поддержка документации
- ✅ Соответствие Django best practices
- ✅ Профессиональный вид проекта
