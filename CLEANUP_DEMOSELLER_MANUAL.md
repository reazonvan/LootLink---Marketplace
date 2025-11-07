# 🗑️ УДАЛЕНИЕ ТЕСТОВОГО ПОЛЬЗОВАТЕЛЯ DemoSeller

## Вариант 1: Через Django Shell (рекомендуется)

```bash
# На локальной машине с активированным venv:
python manage.py shell

# В shell выполните:
from accounts.models import CustomUser
from listings.models import Listing

# Найти пользователя
try:
    demo = CustomUser.objects.get(username='DemoSeller')
    print(f"Найден: {demo.username} ({demo.email})")
    
    # Посмотреть сколько у него объявлений
    count = demo.listings.count()
    print(f"Объявлений: {count}")
    
    # Удалить все объявления
    if count > 0:
        demo.listings.all().delete()
        print(f"✓ Удалено {count} объявлений")
    
    # Удалить пользователя
    demo.delete()
    print("✓ Пользователь DemoSeller удален")
    
except CustomUser.DoesNotExist:
    print("DemoSeller не найден в базе")

exit()
```

---

## Вариант 2: Через SQL (если есть доступ к PostgreSQL)

```sql
-- Подключиться к базе
psql -U postgres -d lootlink_db

-- Проверить существует ли DemoSeller
SELECT id, username, email FROM accounts_customuser WHERE username = 'DemoSeller';

-- Удалить объявления DemoSeller (если есть)
DELETE FROM listings_listing WHERE seller_id IN (
    SELECT id FROM accounts_customuser WHERE username = 'DemoSeller'
);

-- Удалить пользователя
DELETE FROM accounts_customuser WHERE username = 'DemoSeller';

-- Проверить результат
SELECT username FROM accounts_customuser WHERE username = 'DemoSeller';
-- Должно вернуть 0 строк
```

---

## Вариант 3: На production сервере

```bash
# SSH на сервер
ssh root@91.218.245.178

# Перейти в директорию проекта
cd /var/www/lootlink

# Активировать виртуальное окружение (если есть)
source venv/bin/activate

# ИЛИ если используется системный Python:
# (без активации venv)

# Запустить скрипт
python scripts/cleanup_production.py

# ИЛИ через Django shell (как в Варианте 1)
python manage.py shell
```

---

## Проверка что DemoSeller удален

После выполнения проверьте:

```bash
python manage.py shell

# В shell:
from accounts.models import CustomUser
CustomUser.objects.filter(username='DemoSeller').exists()
# Должно вернуть: False

exit()
```

---

## ⚠️ ВАЖНО

Если DemoSeller не существует в базе - ничего страшного, значит он уже был удален или никогда не создавался на production.

Команда `create_demo_listings` создает DemoSeller только при запуске, и если вы ее не запускали на production - пользователя там нет.

---

## ✅ Что уже сделано

**Пункт 1 - ВЫПОЛНЕН ✅**
- Заменены все фейковые email (10 замен в 6 файлах)
- support@lootlink.com → ivanpetrov20066.ip@gmail.com
- tech@lootlink.com → ivanpetrov20066.ip@gmail.com

**Пункт 2 - ТРЕБУЕТ ВЫПОЛНЕНИЯ**
- Нужно удалить DemoSeller через Django shell
- Можно сделать на сервере или локально с активированным venv

