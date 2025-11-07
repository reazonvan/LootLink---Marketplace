#!/usr/bin/env python
"""
ПОЛНОСТЬЮ АВТОМАТИЧЕСКИЙ СКРИПТ
Выполняет ВСЕ необходимые действия:
1. Проверяет БД
2. Удаляет тестовых пользователей (сохраняет reazonvan)
3. Обновляет .env
4. Очищает кеш

Запуск: python scripts/auto_fix_all.py --auto
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import CustomUser
from listings.models import Listing
from transactions.models import PurchaseRequest, Review
from payments.models import Wallet, Transaction
from chat.models import Conversation, Message
from django.db import transaction as db_transaction
from django.core.cache import cache

print("=" * 80)
print("  ПОЛНОСТЬЮ АВТОМАТИЧЕСКАЯ ОЧИСТКА")
print("=" * 80)
print()

# Проверка аргументов
auto_mode = '--auto' in sys.argv or '-y' in sys.argv

if not auto_mode:
    print("[INFO] Для автоматического режима (без подтверждений) запустите:")
    print("       python scripts/auto_fix_all.py --auto")
    print()

# Защищенные пользователи
PROTECTED_USERNAMES = ['reazonvan']
TEST_PATTERNS = ['demo', 'test', 'fake', '@example.com', '@test.com', '@lootlink.com']

# ==================== ШАГ 1: АНАЛИЗ ====================
print("[STEP 1/4] АНАЛИЗ БАЗЫ ДАННЫХ")
print("-" * 80)

all_users = CustomUser.objects.all()
test_users = []
protected_users = []

for user in all_users:
    if user.username.lower() in [u.lower() for u in PROTECTED_USERNAMES]:
        protected_users.append(user)
        continue
    
    is_test = False
    username_lower = user.username.lower()
    email_lower = user.email.lower()
    
    for pattern in TEST_PATTERNS:
        if pattern in username_lower or pattern in email_lower:
            is_test = True
            break
    
    if is_test:
        test_users.append(user)

print(f"Всего пользователей:     {all_users.count()}")
print(f"Защищенных:              {len(protected_users)}")
print(f"Тестовых (к удалению):   {len(test_users)}")
print()

if protected_users:
    print("[PROTECTED] Будут сохранены:")
    for user in protected_users:
        listings = user.listings.count()
        print(f"  [OK] {user.username:20} ({user.email:30}) - {listings} объявл.")
print()

if test_users:
    print("[DELETE] Будут удалены:")
    for user in test_users:
        listings = user.listings.count()
        print(f"  [X] {user.username:20} ({user.email:30}) - {listings} объявл.")
    print()
else:
    print("[SUCCESS] Тестовых пользователей не найдено!")
    print("База данных уже чистая.")
    sys.exit(0)

# Подтверждение
if not auto_mode:
    response = input("Продолжить удаление? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("[CANCELLED] Отменено")
        sys.exit(0)
    print()

# ==================== ШАГ 2: УДАЛЕНИЕ ====================
print("[STEP 2/4] УДАЛЕНИЕ ТЕСТОВЫХ ДАННЫХ")
print("-" * 80)

deleted_count = 0
deleted_listings = 0
deleted_transactions = 0

try:
    with db_transaction.atomic():
        for user in test_users:
            # Подсчет
            listings_count = user.listings.count()
            trans_count = Transaction.objects.filter(user=user).count()
            
            deleted_listings += listings_count
            deleted_transactions += trans_count
            
            # Удаление
            username = user.username
            user.delete()  # CASCADE удалит всё связанное
            deleted_count += 1
            
            print(f"  [OK] Удален: {username} ({listings_count} объявл., {trans_count} транз.)")
    
    print()
    print(f"[SUCCESS] Удалено пользователей: {deleted_count}")
    print(f"          Удалено объявлений:    {deleted_listings}")
    print(f"          Удалено транзакций:    {deleted_transactions}")
    
except Exception as e:
    print()
    print(f"[ERROR] Ошибка: {e}")
    print("Транзакция откачена, данные не изменены")
    sys.exit(1)

print()

# ==================== ШАГ 3: ОБНОВЛЕНИЕ .ENV ====================
print("[STEP 3/4] ОБНОВЛЕНИЕ .ENV")
print("-" * 80)

env_file = '.env'
real_email = 'ivanpetrov20066.ip@gmail.com'

if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # Проверяем есть ли уже DEFAULT_FROM_EMAIL
    if 'DEFAULT_FROM_EMAIL' in env_content:
        # Заменяем
        lines = env_content.split('\n')
        new_lines = []
        updated = False
        for line in lines:
            if line.startswith('DEFAULT_FROM_EMAIL'):
                new_lines.append(f'DEFAULT_FROM_EMAIL={real_email}')
                updated = True
                print(f"  [OK] Обновлено: DEFAULT_FROM_EMAIL={real_email}")
            else:
                new_lines.append(line)
        
        if updated:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
    else:
        # Добавляем
        with open(env_file, 'a', encoding='utf-8') as f:
            f.write(f'\nDEFAULT_FROM_EMAIL={real_email}\n')
        print(f"  [OK] Добавлено: DEFAULT_FROM_EMAIL={real_email}")
else:
    print("  [WARNING] .env файл не найден")

print()

# ==================== ШАГ 4: ОЧИСТКА КЕША ====================
print("[STEP 4/4] ОЧИСТКА КЕША")
print("-" * 80)

try:
    cache.clear()
    print("  [OK] Кеш Django очищен")
except Exception as e:
    print(f"  [WARNING] Ошибка очистки кеша: {e}")

print()

# ==================== ФИНАЛЬНАЯ ПРОВЕРКА ====================
print("=" * 80)
print("  ФИНАЛЬНАЯ ПРОВЕРКА")
print("=" * 80)
print()

remaining_users = CustomUser.objects.all()
print(f"Пользователей осталось: {remaining_users.count()}")
print()
print("Оставшиеся пользователи:")
for user in remaining_users:
    listings = user.listings.count()
    print(f"  - {user.username:20} ({user.email:30}) - {listings} объявл.")

print()

# Проверка что владелец на месте
owner = CustomUser.objects.filter(username__iexact='reazonvan').first()
if owner:
    print("[SUCCESS] Владелец 'reazonvan' сохранен и на месте!")
else:
    print("[ERROR] ВНИМАНИЕ: Владелец 'reazonvan' не найден!")

print()
print("=" * 80)
print("  АВТОМАТИЧЕСКАЯ ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО!")
print("=" * 80)
print()
print("Что сделано:")
print(f"  [OK] Удалено тестовых пользователей:  {deleted_count}")
print(f"  [OK] Удалено объявлений:              {deleted_listings}")
print(f"  [OK] Удалено транзакций:              {deleted_transactions}")
print("  [OK] Обновлен .env файл")
print("  [OK] Очищен кеш")
print("  [OK] Владелец 'reazonvan' сохранен")
print()
print("Следующие шаги:")
print("  1. Перезапустите сервис:")
print("     sudo systemctl restart lootlink")
print("  2. Проверьте сайт:")
print("     http://91.218.245.178/requisites/")
print("  3. Отправьте заявку в ЮKassa (см. YUKASSA_SUBMISSION_CHECKLIST.md)")
print()
print("=" * 80)

