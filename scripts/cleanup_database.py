#!/usr/bin/env python
"""
Скрипт для безопасной очистки базы данных от тестовых пользователей и данных.
СОХРАНЯЕТ владельца и реальных пользователей.

Запуск: python scripts/cleanup_database.py
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
from payments.models import Wallet, Transaction, Escrow
from chat.models import Conversation, Message
from django.db import transaction as db_transaction

print("=" * 80)
print("  ОЧИСТКА БАЗЫ ДАННЫХ ОТ ТЕСТОВЫХ ДАННЫХ")
print("=" * 80)
print()

# Паттерны для определения тестовых данных
TEST_PATTERNS = [
    'demo', 'test', 'fake', 'admin@example', 'test@test',
    'user@example', '@example.com', '@test.com', '@lootlink.com'
]

# ВАЖНО: Защищенные пользователи (НЕ УДАЛЯТЬ)
PROTECTED_USERNAMES = ['reazonvan']  # Добавьте других реальных пользователей если нужно

print("[SAFETY] Защищенные пользователи (НЕ будут удалены):")
for username in PROTECTED_USERNAMES:
    user = CustomUser.objects.filter(username__iexact=username).first()
    if user:
        print(f"  [PROTECTED] {user.username} ({user.email})")
    else:
        print(f"  [!] ВНИМАНИЕ: {username} не найден в БД!")
print()

# Поиск тестовых пользователей
all_users = CustomUser.objects.all()
test_users = []
protected_users = []

for user in all_users:
    # Проверка на защищенного пользователя
    if user.username.lower() in [u.lower() for u in PROTECTED_USERNAMES]:
        protected_users.append(user)
        continue
    
    # Проверка на тестовые паттерны
    is_test = False
    username_lower = user.username.lower()
    email_lower = user.email.lower()
    
    for pattern in TEST_PATTERNS:
        if pattern in username_lower or pattern in email_lower:
            is_test = True
            break
    
    if is_test:
        test_users.append(user)

print("[ANALYSIS] Результаты анализа:")
print(f"  Всего пользователей в БД:    {all_users.count()}")
print(f"  Защищенных пользователей:    {len(protected_users)}")
print(f"  Тестовых пользователей:      {len(test_users)}")
print()

if not test_users:
    print("[SUCCESS] Тестовых пользователей не найдено!")
    print("База данных уже чистая.")
    sys.exit(0)

# Показываем что будет удалено
print("[DELETE LIST] Следующие пользователи будут УДАЛЕНЫ:")
print()
total_listings = 0
total_transactions = 0
total_messages = 0

for user in test_users:
    listings_count = user.listings.count()
    transactions_count = Transaction.objects.filter(user=user).count()
    messages_sent = Message.objects.filter(sender=user).count()
    
    total_listings += listings_count
    total_transactions += transactions_count
    total_messages += messages_sent
    
    print(f"  [X] {user.username:20} ({user.email:35})")
    print(f"      - Объявлений: {listings_count}")
    print(f"      - Транзакций: {transactions_count}")
    print(f"      - Сообщений:  {messages_sent}")
    print()

print("[TOTAL IMPACT] Что будет удалено:")
print(f"  Пользователей:  {len(test_users)}")
print(f"  Объявлений:     {total_listings}")
print(f"  Транзакций:     {total_transactions}")
print(f"  Сообщений:      {total_messages}")
print()

# Подтверждение
print("=" * 80)
print("[WARNING] ВНИМАНИЕ!")
print("Это действие НЕОБРАТИМО!")
print("Все данные тестовых пользователей будут УДАЛЕНЫ из базы данных.")
print("Защищенные пользователи и их данные СОХРАНЯТСЯ.")
print("=" * 80)
print()

response = input("Вы уверены что хотите продолжить? Введите 'DELETE' для подтверждения: ")

if response != 'DELETE':
    print()
    print("[CANCELLED] Отменено пользователем. Данные не изменены.")
    sys.exit(0)

print()
print("[PROCESSING] Начинаю очистку...")
print()

# Выполняем очистку в транзакции
deleted_stats = {
    'users': 0,
    'listings': 0,
    'transactions': 0,
    'reviews': 0,
    'wallets': 0,
    'conversations': 0,
    'messages': 0,
}

try:
    with db_transaction.atomic():
        for user in test_users:
            print(f"[DELETE] Удаляю: {user.username}")
            
            # Удаляем связанные объекты (Django сделает это автоматически с CASCADE)
            # Но подсчитаем для статистики
            
            # Объявления
            listings_count = user.listings.count()
            deleted_stats['listings'] += listings_count
            
            # Транзакции
            transactions_count = Transaction.objects.filter(user=user).count()
            deleted_stats['transactions'] += transactions_count
            
            # Отзывы (как автор)
            reviews_count = Review.objects.filter(reviewer=user).count()
            deleted_stats['reviews'] += reviews_count
            
            # Кошелек
            if hasattr(user, 'wallet'):
                deleted_stats['wallets'] += 1
            
            # Сообщения
            messages_count = Message.objects.filter(sender=user).count()
            deleted_stats['messages'] += messages_count
            
            # Диалоги (где участник)
            conversations_count = Conversation.objects.filter(
                participants=user
            ).count()
            deleted_stats['conversations'] += conversations_count
            
            # Удаляем пользователя (CASCADE удалит связанные объекты)
            user.delete()
            deleted_stats['users'] += 1
            
            print(f"  [OK] Удален: {user.username}")
    
    # Очистка кеша
    from django.core.cache import cache
    cache.clear()
    print()
    print("[OK] Кеш очищен")
    
    # Итоги
    print()
    print("=" * 80)
    print("  ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО")
    print("=" * 80)
    print()
    print("[DELETED] Удалено:")
    print(f"  Пользователей:     {deleted_stats['users']}")
    print(f"  Объявлений:        {deleted_stats['listings']}")
    print(f"  Транзакций:        {deleted_stats['transactions']}")
    print(f"  Отзывов:           {deleted_stats['reviews']}")
    print(f"  Кошельков:         {deleted_stats['wallets']}")
    print(f"  Диалогов:          {deleted_stats['conversations']}")
    print(f"  Сообщений:         {deleted_stats['messages']}")
    print()
    
    print("[PROTECTED] Сохранены:")
    for user in protected_users:
        print(f"  [OK] {user.username} ({user.email})")
        print(f"       - Объявлений: {user.listings.count()}")
    print()
    
    print("=" * 80)
    print("[SUCCESS] База данных очищена!")
    print("Все тестовые данные удалены.")
    print("Владелец и реальные пользователи сохранены.")
    print("=" * 80)
    
except Exception as e:
    print()
    print("=" * 80)
    print("[ERROR] ОШИБКА ПРИ ОЧИСТКЕ!")
    print("=" * 80)
    print(f"Ошибка: {e}")
    print()
    print("Транзакция откачена. Данные НЕ изменены.")
    import traceback
    traceback.print_exc()
    sys.exit(1)

